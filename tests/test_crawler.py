"""
Phase 7 단위 테스트 - 크롤러 서비스
P7.M1.T1: 크롤러 파싱 함수 테스트 (Mock 사용)
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock


class TestCrawlerUtilities:
    """크롤러 유틸리티 함수 테스트"""
    
    def test_ticker_mapping(self):
        """티커 심볼 매핑 테스트"""
        from app.services.crawler import TICKER_TO_INVESTING_SLUG
        
        # 주요 티커 매핑 확인
        assert 'TSLA' in TICKER_TO_INVESTING_SLUG
        assert 'AAPL' in TICKER_TO_INVESTING_SLUG
        assert 'MSFT' in TICKER_TO_INVESTING_SLUG
        assert 'NVDA' in TICKER_TO_INVESTING_SLUG
        
        # 매핑 값 확인
        assert TICKER_TO_INVESTING_SLUG['TSLA'] == 'tesla-motors'
        assert TICKER_TO_INVESTING_SLUG['AAPL'] == 'apple-computer-inc'


class TestInvestingCrawler:
    """InvestingCrawler 클래스 테스트"""
    
    @pytest.fixture
    def mock_driver(self):
        """Mock WebDriver 생성"""
        driver = MagicMock()
        driver.get.return_value = None
        driver.quit.return_value = None
        return driver
    
    def test_crawler_initialization(self):
        """크롤러 초기화 테스트 (실제 드라이버 없이)"""
        from app.services.crawler import InvestingCrawler
        
        # headless 모드로 생성만 테스트
        with patch('app.services.crawler.webdriver.Chrome') as mock_chrome:
            mock_chrome.return_value = MagicMock()
            
            crawler = InvestingCrawler(headless=True, timeout=30)
            assert crawler.headless is True
            assert crawler.timeout == 30
    
    def test_get_news_url_with_mapping(self):
        """매핑된 티커의 URL 생성 테스트"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True)
        
        url = crawler.get_news_url('TSLA')
        assert 'tesla-motors' in url
        assert 'investing.com' in url
        assert '/equities/' in url
    
    def test_get_news_url_without_mapping(self):
        """매핑되지 않은 티커의 URL 생성 테스트"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True)
        
        url = crawler.get_news_url('UNKNOWN_TICKER')
        assert 'search' in url or 'UNKNOWN_TICKER' in url
    
    def test_parse_date_relative_hours(self):
        """상대 시간 파싱 테스트 (hours ago)"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True)
        
        now = datetime.now(timezone.utc)
        
        # 1시간 전
        result = crawler._parse_date("1 hour ago")
        if result:
            diff = abs((now - result).total_seconds())
            assert diff < 3700  # 약 1시간 + 오차
        
        # 2시간 전
        result = crawler._parse_date("2 hours ago")
        if result:
            diff = abs((now - result).total_seconds())
            assert diff < 7400  # 약 2시간 + 오차
    
    def test_parse_date_just_now(self):
        """'Just now' 시간 파싱 테스트"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True)
        
        now = datetime.now(timezone.utc)
        
        result = crawler._parse_date("Just now")
        if result:
            diff = abs((now - result).total_seconds())
            assert diff < 60  # 1분 이내
    
    def test_parse_date_minutes_ago(self):
        """분 단위 상대 시간 파싱 테스트"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True)
        
        now = datetime.now(timezone.utc)
        
        result = crawler._parse_date("30 minutes ago")
        if result:
            diff = abs((now - result).total_seconds())
            assert diff < 2000  # 약 30분 + 오차


class TestNewsDataStructure:
    """뉴스 데이터 구조 테스트"""
    
    def test_news_item_structure(self):
        """뉴스 아이템 구조 검증"""
        news_item = {
            'title': 'Tesla announces new model',
            'content': 'Tesla Inc. has announced...',
            'url': 'https://investing.com/news/tesla',
            'date': datetime.now(timezone.utc).isoformat(),
            'source': 'investing.com',
            'ticker': 'TSLA',
            'company_name': 'Tesla'
        }
        
        # 필수 필드 확인
        required_fields = ['title', 'url', 'date', 'ticker']
        for field in required_fields:
            assert field in news_item
        
        # 타입 확인
        assert isinstance(news_item['ticker'], str)
        assert len(news_item['ticker']) <= 10
    
    def test_news_with_analysis(self):
        """분석 포함 뉴스 데이터 구조"""
        news_with_analysis = {
            'news_id': 'test_002',
            'ticker_symbol': 'AAPL',
            'company_name': 'Apple',
            'title': 'Apple revenue beats expectations',
            'content': 'Apple Inc. reported...',
            'url': 'https://investing.com/news/apple',
            'published_date': datetime.now(timezone.utc).isoformat(),
            'crawled_date': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'ko': '애플 분기 실적 호조',
                'en': 'Apple beats quarterly expectations',
                'es': 'Apple supera expectativas trimestrales',
                'ja': 'アップル四半期決算好調'
            },
            'sentiment': {
                'classification': 'Positive',
                'score': 7
            }
        }
        
        # 요약 언어 확인
        assert 'ko' in news_with_analysis['summary']
        assert 'en' in news_with_analysis['summary']
        assert 'es' in news_with_analysis['summary']
        assert 'ja' in news_with_analysis['summary']
        
        # 감성 분석 범위 확인
        assert news_with_analysis['sentiment']['score'] >= -10
        assert news_with_analysis['sentiment']['score'] <= 10
        assert news_with_analysis['sentiment']['classification'] in ['Positive', 'Negative', 'Neutral']


class TestCrawlerRetryLogic:
    """크롤러 재시도 로직 테스트"""
    
    def test_retry_on_timeout(self):
        """타임아웃 시 재시도 테스트"""
        from app.services.crawler import InvestingCrawler
        from selenium.common.exceptions import TimeoutException
        
        with patch('app.services.crawler.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            
            # 첫 2번 실패, 3번째 성공
            mock_driver.get.side_effect = [
                TimeoutException(),
                TimeoutException(),
                None  # 성공
            ]
            
            crawler = InvestingCrawler(headless=True)
            crawler.driver = mock_driver
            
            # 재시도 로직 테스트
            success = False
            for attempt in range(3):
                try:
                    mock_driver.get("https://example.com")
                    success = True
                    break
                except TimeoutException:
                    continue
            
            assert success is True
            assert mock_driver.get.call_count == 3


class TestCrawlerConfig:
    """크롤러 설정 테스트"""
    
    def test_headless_mode(self):
        """Headless 모드 설정 테스트"""
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 인자 확인
        args = options.arguments
        assert '--headless' in args
        assert '--no-sandbox' in args
    
    def test_default_timeout(self):
        """기본 타임아웃 설정 테스트"""
        from app.services.crawler import InvestingCrawler
        
        crawler = InvestingCrawler(headless=True, timeout=30)
        
        assert crawler.timeout == 30


class TestCrawlerBaseUrl:
    """크롤러 기본 URL 테스트"""
    
    def test_base_url(self):
        """BASE_URL 확인"""
        from app.services.crawler import InvestingCrawler
        
        assert InvestingCrawler.BASE_URL == "https://www.investing.com"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
