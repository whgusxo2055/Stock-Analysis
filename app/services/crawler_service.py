"""
크롤링 오케스트레이션 서비스
- 크롤러 실행 조율
- 중복 체크 및 ES 저장
- crawl_logs 기록
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.models.models import CrawlLog, StockMaster
from app.services.crawler import InvestingCrawler
from app.services.news_storage import NewsStorageAdapter
from app.services.news_analyzer import NewsAnalyzer

logger = logging.getLogger(__name__)


class CrawlerService:
    """크롤링 오케스트레이션 서비스"""

    def __init__(
        self,
        db_session: Session,
        news_storage: NewsStorageAdapter,
        news_analyzer: Optional[NewsAnalyzer] = None
    ):
        """
        초기화
        
        Args:
            db_session: SQLAlchemy 세션
            news_storage: NewsStorageAdapter 인스턴스
            news_analyzer: NewsAnalyzer 인스턴스 (옵션)
        """
        self.db = db_session
        self.storage = news_storage
        self.analyzer = news_analyzer or NewsAnalyzer()
        logger.info("CrawlerService initialized with analyzer")

    def crawl_ticker(
        self,
        ticker: str,
        hours_ago: int = 6,
        max_retries: int = 3
    ) -> Dict[str, any]:
        """
        단일 티커에 대한 크롤링 실행
        
        Args:
            ticker: 티커 심볼 (예: TSLA)
            hours_ago: 최근 N시간
            max_retries: 최대 재시도 횟수
        
        Returns:
            결과 딕셔너리 {'status': ..., 'count': ..., 'error': ...}
        """
        # stock_master에서 회사명 조회
        stock = self.db.query(StockMaster).filter_by(
            ticker_symbol=ticker
        ).first()
        
        if not stock:
            error_msg = f"Ticker {ticker} not found in stock_master"
            logger.error(error_msg)
            self._save_crawl_log(ticker, 'FAILED', 0, error_msg)
            return {'status': 'FAILED', 'count': 0, 'error': error_msg}
        
        company_name = stock.company_name
        logger.info(f"Starting crawl for {ticker} ({company_name})")
        
        try:
            # Investing.com에서 뉴스 수집
            with InvestingCrawler() as crawler:
                news_items, error = crawler.crawl_with_retry(
                    ticker=ticker,
                    company_name=company_name,
                    hours_ago=hours_ago,
                    max_retries=max_retries
                )
            
            if error:
                logger.warning(
                    f"Crawl completed with errors for {ticker}: {error}"
                )
                self._save_crawl_log(ticker, 'PARTIAL', len(news_items), error)
                return {
                    'status': 'PARTIAL',
                    'count': len(news_items),
                    'error': error
                }
            
            # 빈 결과
            if not news_items:
                logger.info(f"No news found for {ticker}")
                self._save_crawl_log(ticker, 'SUCCESS', 0, None)
                return {'status': 'SUCCESS', 'count': 0, 'error': None}
            
            # 중복 제거 및 저장
            saved_count = self._save_news_items(ticker, news_items, company_name)
            
            logger.info(
                f"Crawl completed for {ticker}: "
                f"{len(news_items)} collected, {saved_count} saved"
            )
            
            self._save_crawl_log(ticker, 'SUCCESS', saved_count, None)
            
            return {
                'status': 'SUCCESS',
                'count': saved_count,
                'total': len(news_items),
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(
                f"Failed to crawl {ticker}: {error_msg}",
                exc_info=True
            )
            self._save_crawl_log(ticker, 'FAILED', 0, error_msg)
            return {'status': 'FAILED', 'count': 0, 'error': error_msg}

    def crawl_all_tickers(
        self,
        hours_ago: int = 6,
        max_retries: int = 3
    ) -> List[Dict[str, any]]:
        """
        모든 등록된 티커에 대한 크롤링 실행
        
        Args:
            hours_ago: 최근 N시간
            max_retries: 최대 재시도 횟수
        
        Returns:
            각 티커별 결과 리스트
        """
        stocks = self.db.query(StockMaster).all()
        
        if not stocks:
            logger.warning("No stocks found in stock_master")
            return []
        
        results = []
        logger.info(f"Starting crawl for {len(stocks)} tickers")
        
        for stock in stocks:
            ticker = stock.ticker_symbol
            result = self.crawl_ticker(
                ticker=ticker,
                hours_ago=hours_ago,
                max_retries=max_retries
            )
            results.append({
                'ticker': ticker,
                **result
            })
        
        # 요약 로그
        total_count = sum(r['count'] for r in results)
        success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
        
        logger.info(
            f"Crawl completed for all tickers: "
            f"{success_count}/{len(stocks)} successful, "
            f"{total_count} news items saved"
        )
        
        return results

    def _save_news_items(
        self,
        ticker: str,
        news_items: List[Dict[str, str]],
        company_name: Optional[str] = None
    ) -> int:
        """
        뉴스 아이템을 ES에 저장 (중복 체크 + 분석 포함)
        
        Args:
            ticker: 티커 심볼
            news_items: 크롤링된 뉴스 리스트
            company_name: 회사명
        
        Returns:
            저장된 개수
        """
        if not news_items:
            return 0
        
        # URL 중복 체크
        unique_items = []
        urls = []
        for item in news_items:
            src = item.get('source_url') or item.get('url')
            if src:
                urls.append(src)
        
        if urls:
            existing_urls = self.storage.check_duplicates(urls, ticker)
            logger.debug(
                f"Found {len(existing_urls)} existing URLs out of {len(urls)}"
            )
        else:
            existing_urls = set()
        
        # 중복 제거
        for item in news_items:
            url = item.get('source_url') or item.get('url')
            if url and url not in existing_urls:
                # ticker와 company_name 추가
                item['ticker'] = ticker
                # ES 호환을 위해 url 필드도 채워둠
                item.setdefault('url', url)
                if company_name:
                    item['company_name'] = company_name
                unique_items.append(item)
        
        if not unique_items:
            logger.info(f"All news items for {ticker} are duplicates")
            return 0
        
        # Phase 4: 뉴스 분석 (다국어 요약 + 감성 분석)
        logger.info(f"Analyzing {len(unique_items)} news items for {ticker}")
        analyzed_items = self.analyzer.batch_analyze(unique_items)
        
        if not analyzed_items:
            logger.warning(f"No items analyzed successfully for {ticker}")
            return 0
        
        # bulk 저장
        result = self.storage.bulk_save_news(analyzed_items)
        saved_count = result.get('success', 0)
        
        logger.info(
            f"Saved {saved_count}/{len(news_items)} news items for {ticker} "
            f"({len(news_items) - saved_count} duplicates or failed analysis)"
        )
        
        return saved_count

    def _save_crawl_log(
        self,
        ticker: str,
        status: str,
        news_count: int,
        error_message: Optional[str]
    ) -> None:
        """
        크롤링 로그를 crawl_logs 테이블에 저장
        
        Args:
            ticker: 티커 심볼
            status: SUCCESS / PARTIAL / FAILED
            news_count: 수집된 뉴스 개수
            error_message: 에러 메시지 (있을 경우)
        """
        try:
            from app.models.models import KST
            log = CrawlLog(
                ticker_symbol=ticker,
                crawled_at=datetime.now(KST),
                status=status,
                news_count=news_count,
                error_message=error_message
            )
            self.db.add(log)
            self.db.commit()
            
            logger.debug(
                f"Crawl log saved: {ticker} - {status} - {news_count} items"
            )
            
        except Exception as e:
            logger.error(f"Failed to save crawl log: {e}", exc_info=True)
            self.db.rollback()
