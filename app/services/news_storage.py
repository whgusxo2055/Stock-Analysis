"""
뉴스 저장 어댑터
Phase 2.3 - News Storage Adapter

ElasticSearch를 사용한 뉴스 데이터 저장 및 조회 서비스
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

from app.utils.elasticsearch_client import get_es_client

logger = logging.getLogger(__name__)


class NewsStorageAdapter:
    """
    뉴스 데이터 저장/조회 어댑터
    
    Phase 3 크롤러와 통합될 서비스 레이어
    """
    
    def __init__(self):
        """어댑터 초기화"""
        self.es_client = get_es_client()
        # 테스트용 별칭 추가
        self.es = self.es_client
        self.news_index = self.es_client.index_name
        self._validate_connection()
    
    def _validate_connection(self):
        """ES 연결 검증"""
        if not self.es_client.is_connected():
            raise ConnectionError("ElasticSearch 연결 실패")
        logger.info("NewsStorageAdapter initialized successfully")
    
    def save_news(self, news_data: Dict) -> bool:
        """
        단일 뉴스 저장
        
        Args:
            news_data (Dict): 뉴스 데이터
                Required fields:
                - news_id: 뉴스 고유 ID
                - ticker_symbol: 종목 코드
                - title: 제목
                - content: 내용
                - published_date: 발행일
                Optional fields:
                - company_name: 회사명
                - url: 뉴스 URL
                - summary: {ko, en, es, ja} 다국어 요약
                - sentiment: {classification, score} 감정 분석
        
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 필수 필드 검증
            required_fields = ['news_id', 'ticker_symbol', 'title', 'content', 'published_date']
            for field in required_fields:
                if field not in news_data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            # 크롤링 시간 자동 추가
            if 'crawled_date' not in news_data:
                news_data['crawled_date'] = datetime.now().isoformat()
            
            # 저장
            result = self.es_client.index_news(news_data)
            
            if result:
                logger.info(f"News saved successfully: {news_data['news_id']}")
            else:
                logger.error(f"Failed to save news: {news_data['news_id']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error saving news: {e}")
            return False
    
    def bulk_save_news(self, news_list: List[Dict]) -> Dict:
        """
        뉴스 벌크 저장 (Phase 3 크롤러 통합용)
        
        Args:
            news_list (List[Dict]): 뉴스 데이터 리스트
        
        Returns:
            Dict: 저장 결과
                - success: 성공한 문서 수
                - failed: 실패한 문서 수
                - errors: 에러 목록
        """
        try:
            if not news_list:
                logger.warning("Empty news list provided")
                return {"success": 0, "failed": 0, "total": 0, "errors": []}
            
            # 크롤링 시간 자동 추가
            crawled_time = datetime.now().isoformat()
            for news in news_list:
                if 'crawled_date' not in news:
                    news['crawled_date'] = crawled_time
            
            # 벌크 저장
            success_count = self.es_client.bulk_index_news(news_list)
            failed_count = len(news_list) - success_count
            
            logger.info(f"Bulk save completed: {success_count} success, {failed_count} failed")
            
            return {
                "success": success_count,
                "failed": failed_count,
                "total": len(news_list),
                "errors": []
            }
            
        except Exception as e:
            logger.error(f"Error in bulk save: {e}")
            return {
                "success": 0,
                "failed": len(news_list) if news_list else 0,
                "total": len(news_list) if news_list else 0,
                "errors": [str(e)]
            }
    
    def get_news(self, news_id: str) -> Optional[Dict]:
        """
        뉴스 ID로 단일 뉴스 조회
        
        Args:
            news_id (str): 뉴스 ID
        
        Returns:
            Optional[Dict]: 뉴스 데이터 (없으면 None)
        """
        try:
            result = self.es_client.client.get(
                index=self.es_client.index_name,
                id=news_id
            )
            
            if result['found']:
                logger.info(f"News retrieved: {news_id}")
                return result['_source']
            else:
                logger.warning(f"News not found: {news_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving news {news_id}: {e}")
            return None
    
    def search_news(
        self,
        ticker_symbol: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sentiment: Optional[str] = None,
        keyword: Optional[str] = None,
        size: int = 20,
        page: int = 1
    ) -> Dict:
        """
        뉴스 검색
        
        Args:
            ticker_symbol (str, optional): 종목 코드
            from_date (str, optional): 시작 날짜 (ISO format)
            to_date (str, optional): 종료 날짜 (ISO format)
            sentiment (str, optional): 감정 분류 (positive/negative/neutral)
            keyword (str, optional): 검색 키워드 (제목+내용)
            size (int): 페이지당 결과 수
            page (int): 페이지 번호 (1부터 시작)
        
        Returns:
            Dict: 검색 결과
                - total: 전체 결과 수
                - hits: 뉴스 리스트
                - page: 현재 페이지
                - size: 페이지 크기
        """
        try:
            # 페이지 계산 (1-based to 0-based)
            from_ = (page - 1) * size
            
            # 키워드 검색 추가
            if keyword:
                # 기본 검색에 키워드 검색 추가
                response = self._search_with_keyword(
                    keyword=keyword,
                    ticker_symbol=ticker_symbol,
                    from_date=from_date,
                    to_date=to_date,
                    sentiment=sentiment,
                    size=size,
                    from_=from_
                )
            else:
                response = self.es_client.search_news(
                    ticker_symbol=ticker_symbol,
                    from_date=from_date,
                    to_date=to_date,
                    sentiment=sentiment,
                    size=size,
                    from_=from_
                )
            
            total = response['hits']['total']['value']
            hits = [hit['_source'] for hit in response['hits']['hits']]
            
            logger.info(f"Search completed: {total} results found")
            
            return {
                "total": total,
                "hits": hits,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size  # 전체 페이지 수
            }
            
        except Exception as e:
            logger.error(f"Error searching news: {e}")
            return {
                "total": 0,
                "hits": [],
                "page": page,
                "size": size,
                "pages": 0
            }
    
    def _search_with_keyword(
        self,
        keyword: str,
        ticker_symbol: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sentiment: Optional[str] = None,
        size: int = 20,
        from_: int = 0
    ) -> Dict:
        """키워드 포함 검색 (내부 메서드)"""
        query = {"bool": {"must": []}}
        
        # 키워드 검색 (제목 + 내용)
        query["bool"]["must"].append({
            "multi_match": {
                "query": keyword,
                "fields": ["title^2", "content"],  # 제목에 가중치 2배
                "type": "best_fields"
            }
        })
        
        # 추가 필터
        if ticker_symbol:
            query["bool"]["must"].append({"term": {"ticker_symbol": ticker_symbol}})
        
        if sentiment:
            query["bool"]["must"].append({"term": {"sentiment.classification": sentiment}})
        
        if from_date or to_date:
            date_range = {}
            if from_date:
                date_range["gte"] = from_date
            if to_date:
                date_range["lte"] = to_date
            query["bool"]["must"].append({"range": {"published_date": date_range}})
        
        response = self.es_client.client.search(
            index=self.es_client.index_name,
            query=query,
            sort=[{"published_date": {"order": "desc"}}],
            size=size,
            from_=from_
        )
        
        return response
    
    def get_statistics(self, ticker_symbol: str, days: int = 7) -> Dict:
        """
        종목별 뉴스 통계
        
        Args:
            ticker_symbol (str): 종목 코드
            days (int): 기간 (일)
        
        Returns:
            Dict: 통계 데이터
                - total: 총 뉴스 수
                - sentiment_distribution: 감정 분포
                - avg_score: 평균 감정 점수
        """
        try:
            stats = self.es_client.get_statistics(ticker_symbol, days)
            logger.info(f"Statistics retrieved for {ticker_symbol}: {stats['total']} news")
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total": 0,
                "sentiment_distribution": [],
                "avg_score": 0
            }
    
    def delete_news(self, news_id: str) -> bool:
        """
        뉴스 삭제
        
        Args:
            news_id (str): 뉴스 ID
        
        Returns:
            bool: 삭제 성공 여부
        """
        try:
            self.es_client.client.delete(
                index=self.es_client.index_name,
                id=news_id
            )
            logger.info(f"News deleted: {news_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting news {news_id}: {e}")
            return False
    
    def get_latest_news(self, ticker_symbol: str, limit: int = 10) -> List[Dict]:
        """
        특정 종목의 최신 뉴스 조회
        
        Args:
            ticker_symbol (str): 종목 코드
            limit (int): 조회 개수
        
        Returns:
            List[Dict]: 최신 뉴스 리스트
        """
        result = self.search_news(
            ticker_symbol=ticker_symbol,
            size=limit,
            page=1
        )
        return result['hits']

    def check_duplicates(self, urls: List[str], ticker_symbol: Optional[str] = None) -> set:
        """
        URL 목록에서 중복된 뉴스 URL 확인
        
        Args:
            urls (List[str]): 확인할 URL 리스트
            ticker_symbol (str, optional): 종목 코드. 지정하면 해당 종목 내에서만 중복을 확인.
        
        Returns:
            set: 이미 저장된 URL 집합
        """
        if not urls:
            return set()
        
        try:
            # source_url 필드로 검색 (SRS v1.1)
            should_clause = [{"term": {"source_url": url}} for url in urls]
            query_bool = {
                "should": should_clause,
                "minimum_should_match": 1
            }
            if ticker_symbol:
                query_bool["must"] = [{"term": {"ticker_symbol": ticker_symbol}}]

            query = {"bool": query_bool}
            
            response = self.es_client.client.search(
                index=self.es_client.index_name,
                query=query,
                size=len(urls),
                _source=["source_url"]
            )
            
            existing_urls = {
                hit['_source'].get('source_url') or hit['_source'].get('url', '')
                for hit in response['hits']['hits']
            }
            
            logger.debug(f"Found {len(existing_urls)} existing URLs out of {len(urls)}")
            
            return existing_urls
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return set()
    
    def get_news_by_id(self, news_id: str) -> Optional[Dict]:
        """
        뉴스 ID로 단일 뉴스 조회
        
        Args:
            news_id: 뉴스 ID
        
        Returns:
            Dict: 뉴스 데이터 또는 None
        """
        try:
            result = self.es_client.get_document(news_id)
            return result
        except Exception as e:
            logger.error(f"Failed to get news by ID {news_id}: {e}")
            return None
    
    def get_ticker_statistics(self, ticker: str, from_date: str) -> Optional[Dict]:
        """
        종목별 통계 조회 (Sprint 9.2)
        
        Args:
            ticker: 종목 심볼
            from_date: 시작 날짜 (YYYY-MM-DD)
        
        Returns:
            Dict: {
                "ticker": "TSLA",
                "company_name": "Tesla Inc",
                "total": 100,
                "positive": 45,
                "negative": 30,
                "neutral": 25,
                "sentiment_avg": 0.35
            }
        """
        try:
            # ES 집계 쿼리
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"term": {"ticker_symbol": ticker}},
                            {"range": {"published_date": {"gte": from_date}}}
                        ]
                    }
                },
                "aggs": {
                    "positive_count": {
                        "filter": {"term": {"sentiment.classification": "positive"}}
                    },
                    "negative_count": {
                        "filter": {"term": {"sentiment.classification": "negative"}}
                    },
                    "neutral_count": {
                        "filter": {"term": {"sentiment.classification": "neutral"}}
                    },
                    "avg_sentiment": {
                        "avg": {"field": "sentiment.score"}
                    },
                    "company_name": {
                        "terms": {"field": "company_name.keyword", "size": 1}
                    }
                }
            }
            
            response = self.es.client.search(
                index=self.news_index,
                query=query['query'],
                aggs=query['aggs'],
                size=0
            )
            
            total = response['hits']['total']['value']
            if total == 0:
                return None
            
            aggs = response['aggregations']
            company_buckets = aggs['company_name']['buckets']
            company_name = company_buckets[0]['key'] if company_buckets else ticker
            
            return {
                'ticker': ticker,
                'company_name': company_name,
                'total': total,
                'positive': aggs['positive_count']['doc_count'],
                'negative': aggs['negative_count']['doc_count'],
                'neutral': aggs['neutral_count']['doc_count'],
                'sentiment_avg': round(aggs['avg_sentiment']['value'] or 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get ticker statistics for {ticker}: {e}")
            return None
    
    def get_date_statistics(self, tickers: List[str], from_date: str) -> List[Dict]:
        """
        일별 통계 조회 (Sprint 9.2)
        
        Args:
            tickers: 종목 심볼 리스트
            from_date: 시작 날짜 (YYYY-MM-DD)
        
        Returns:
            List[Dict]: [
                {"date": "2025-11-27", "count": 15},
                {"date": "2025-11-26", "count": 20}
            ]
        """
        try:
            query = {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {"terms": {"ticker_symbol": tickers}},
                            {"range": {"published_date": {"gte": from_date}}}
                        ]
                    }
                },
                "aggs": {
                    "by_date": {
                        "date_histogram": {
                            "field": "published_date",
                            "calendar_interval": "day",
                            "format": "yyyy-MM-dd",
                            "order": {"_key": "desc"}
                        }
                    }
                }
            }
            
            response = self.es.client.search(
                index=self.news_index,
                query=query['query'],
                aggs=query['aggs'],
                size=0
            )
            
            buckets = response['aggregations']['by_date']['buckets']
            
            return [
                {
                    'date': bucket['key_as_string'],
                    'count': bucket['doc_count']
                }
                for bucket in buckets
            ]
            
        except Exception as e:
            logger.error(f"Failed to get date statistics: {e}")
            return []
    
    def count_news(
        self,
        ticker_symbols: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sentiment: Optional[str] = None
    ) -> int:
        """
        조건에 맞는 뉴스 개수 반환
        
        Args:
            ticker_symbols: 종목 코드 리스트
            from_date: 시작 날짜
            to_date: 종료 날짜
            sentiment: 감성 분류
        
        Returns:
            int: 뉴스 개수
        """
        try:
            # 검색 조건 구성
            must = []
            
            if ticker_symbols:
                must.append({"terms": {"ticker_symbol": ticker_symbols}})
            
            if from_date or to_date:
                date_range = {}
                if from_date:
                    date_range["gte"] = from_date
                if to_date:
                    date_range["lte"] = to_date
                must.append({"range": {"published_date": date_range}})
            
            if sentiment:
                must.append({"term": {"sentiment.classification": sentiment}})
            
            query = {"bool": {"must": must}} if must else {"match_all": {}}
            
            # Count API 사용
            result = self.es.count(index=self.news_index, body={"query": query})
            return result.get('count', 0)
            
        except Exception as e:
            logger.error(f"Failed to count news: {e}")
            return 0


    def get_recent_news(
        self,
        ticker_symbol: str,
        hours: int = 3
    ) -> List[Dict]:
        """
        최근 N시간 이내의 뉴스 조회 (FR-035)
        
        Args:
            ticker_symbol: 종목 코드
            hours: 시간 범위 (기본 3시간)
        
        Returns:
            List[Dict]: 뉴스 리스트
        """
        try:
            from datetime import timezone
            # UTC 기준으로 시간 계산 (ES에 저장된 published_date가 UTC임)
            from_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            
            query = {
                "bool": {
                    "must": [
                        {"term": {"ticker_symbol": ticker_symbol}},
                        {"range": {"published_date": {"gte": from_date}}}
                    ]
                }
            }
            
            response = self.es_client.client.search(
                index=self.news_index,
                query=query,
                sort=[{"published_date": {"order": "desc"}}],
                size=100
            )
            
            hits = [hit['_source'] for hit in response['hits']['hits']]
            logger.info(f"Found {len(hits)} recent news for {ticker_symbol} in last {hours} hours")
            return hits
            
        except Exception as e:
            logger.error(f"Error getting recent news for {ticker_symbol}: {e}")
            return []

    def delete_old_news(self, cutoff_date: datetime) -> int:
        """
        오래된 뉴스 삭제 (FR-028)
        
        Args:
            cutoff_date: 기준 날짜 (이전 데이터 삭제)
        
        Returns:
            int: 삭제된 문서 수
        """
        try:
            query = {
                "range": {
                    "published_date": {
                        "lt": cutoff_date.isoformat()
                    }
                }
            }
            
            response = self.es_client.client.delete_by_query(
                index=self.news_index,
                body={"query": query}
            )
            
            deleted_count = response.get('deleted', 0)
            logger.info(f"Deleted {deleted_count} old news items before {cutoff_date}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old news: {e}")
            return 0


# 싱글톤 인스턴스
_storage_adapter: Optional[NewsStorageAdapter] = None


def get_news_storage() -> NewsStorageAdapter:
    """
    NewsStorageAdapter 싱글톤 인스턴스 반환
    
    Returns:
        NewsStorageAdapter: 저장 어댑터 인스턴스
    """
    global _storage_adapter
    
    if _storage_adapter is None:
        _storage_adapter = NewsStorageAdapter()
    
    return _storage_adapter


# 별칭 - 스케줄러에서 사용
class NewsStorageService:
    """
    NewsStorageAdapter의 래퍼 클래스
    스케줄러 및 이메일 서비스에서 사용
    """
    
    def __init__(self):
        """초기화"""
        self._adapter = None
    
    def _get_adapter(self) -> NewsStorageAdapter:
        """지연 초기화"""
        if self._adapter is None:
            try:
                self._adapter = get_news_storage()
            except Exception as e:
                logger.error(f"Failed to initialize storage adapter: {e}")
                raise
        return self._adapter
    
    def get_recent_news(self, ticker: str, hours: int = 3) -> List[Dict]:
        """최근 N시간 뉴스 조회"""
        return self._get_adapter().get_recent_news(ticker, hours)
    
    def delete_old_news(self, cutoff_date: datetime) -> int:
        """오래된 뉴스 삭제"""
        return self._get_adapter().delete_old_news(cutoff_date)
    
    def store_news_batch(self, news_list: List[Dict]) -> int:
        """뉴스 배치 저장"""
        result = self._get_adapter().bulk_save_news(news_list)
        return result.get('success', 0)
    
    def search_news(self, **kwargs) -> Dict:
        """뉴스 검색"""
        return self._get_adapter().search_news(**kwargs)
    
    def get_statistics(self, ticker: str, days: int = 7) -> Dict:
        """통계 조회"""
        return self._get_adapter().get_statistics(ticker, days)
    
    def get_ticker_statistics(self, ticker: str, from_date: str) -> Optional[Dict]:
        """종목별 통계 조회 (Sprint 9.2)"""
        return self._get_adapter().get_ticker_statistics(ticker, from_date)
    
    def get_date_statistics(self, tickers: List[str], from_date: str) -> List[Dict]:
        """일별 통계 조회 (Sprint 9.2)"""
        return self._get_adapter().get_date_statistics(tickers, from_date)
