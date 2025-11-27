"""
뉴스 크롤러 서비스
- Investing.com 전용 Selenium 크롤러
- 3시간마다 실행, 최근 3시간 뉴스 수집
- URL 기반 중복 제거
"""

import logging
import time
import re
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dateutil import parser as date_parser
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException
)

from app.utils.config import Config

logger = logging.getLogger(__name__)


# User-Agent 로테이션을 위한 리스트 (봇 차단 우회)
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
]

# 프록시 서버 리스트 (IP 분산용) - None이면 프록시 사용 안 함
# 무료 프록시 서비스 또는 유료 프록시 추가 가능
# 형식: 'http://ip:port' 또는 'socks5://ip:port'
PROXY_LIST = [
    None,  # 프록시 없음 (기본 IP)
    # 예시 (실제 사용 시 유효한 프록시로 교체):
    # 'http://proxy1.example.com:8080',
    # 'http://proxy2.example.com:8080',
    # 'socks5://proxy3.example.com:1080',
]

# 프록시 로테이션을 위한 락
proxy_lock = threading.Lock()
proxy_index = 0


# Investing.com 티커 매핑 (티커 심볼 -> investing.com URL 슬러그)
TICKER_TO_INVESTING_SLUG = {
    'TSLA': 'tesla-motors',
    'AAPL': 'apple-computer-inc',
    'GOOGL': 'google-inc',
    'GOOG': 'google-inc-c',
    'MSFT': 'microsoft-corp',
    'AMZN': 'amazon-com-inc',
    'META': 'meta-platforms',
    'NVDA': 'nvidia-corp',
    'AMD': 'advanced-micro-device',
    'NFLX': 'netflix-inc',
    'INTC': 'intel-corp',
    'CRM': 'salesforce-com',
    'ORCL': 'oracle-corp',
    'IBM': 'ibm',
    'CSCO': 'cisco-systems-inc',
    'ADBE': 'adobe-sys-inc',
    'PYPL': 'paypal-holdings-inc',
    'SQ': 'square-inc',
    'SHOP': 'shopify-inc',
    'UBER': 'uber-technologies-inc',
    'LYFT': 'lyft-inc',
    'SNAP': 'snap-inc',
    'TWTR': 'twitter-inc',
    'PINS': 'pinterest',
    'ZM': 'zoom-video-communications-inc',
    'DOCU': 'docusign-inc',
    'ROKU': 'roku-inc',
    'SPOT': 'spotify-technology',
    'ABNB': 'airbnb-inc',
    'COIN': 'coinbase-global-inc',
    'RBLX': 'roblox-corp',
    'PLTR': 'palantir-technologies-inc',
    'SNOW': 'snowflake-inc',
    'DDOG': 'datadog-inc',
    'NET': 'cloudflare-inc',
    'CRWD': 'crowdstrike-holdings-inc',
    'OKTA': 'okta-inc',
    'MDB': 'mongodb-inc',
    'ZS': 'zscaler-inc',
    'JPM': 'jp-morgan-chase',
    'BAC': 'bank-of-america',
    'WFC': 'wells-fargo',
    'GS': 'goldman-sachs-group',
    'MS': 'morgan-stanley',
    'C': 'citigroup',
    'V': 'visa-inc',
    'MA': 'mastercard-inc',
    'DIS': 'disney',
    'WMT': 'wal-mart-stores',
    'TGT': 'target-corp',
    'COST': 'costco-wholesale',
    'HD': 'home-depot',
    'NKE': 'nike',
    'SBUX': 'starbucks-corp',
    'MCD': 'mcdonalds-corp',
    'KO': 'coca-cola-co',
    'PEP': 'pepsico',
    'JNJ': 'johnson-johnson',
    'PFE': 'pfizer-inc',
    'MRK': 'merck-co-inc',
    'ABBV': 'abbvie-inc',
    'UNH': 'unitedhealth-group',
    'CVS': 'cvs-health-corp',
    'BA': 'boeing-co',
    'CAT': 'caterpillar-inc',
    'GE': 'general-electric',
    'MMM': '3m-co',
    'XOM': 'exxon-mobil',
    'CVX': 'chevron',
    'COP': 'conocophillips',
    'OXY': 'occidental-petroleum',
}

# ETF 티커 매핑 (investing.com 구조가 다름)
TICKER_TO_ETF_SLUG = {
    'SPY': 'spdr-s-p-500',
    'QQQ': 'invesco-qqq-trust',
    'IWM': 'ishares-russell-2000-etf',
    'DIA': 'spdr-djia-trust',
    'VOO': 'vanguard-s-p-500-etf',
    'VTI': 'vanguard-total-stock-market-etf',
    'EEM': 'ishares-msci-emerging-markets',
    'GLD': 'spdr-gold-trust',
    'XLF': 'financial-select-sector-spdr',
    'XLE': 'energy-select-sector-spdr',
}


class InvestingCrawler:
    """Investing.com 전용 Selenium 크롤러"""

    BASE_URL = "https://www.investing.com"
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None
    ):
        """
        크롤러 초기화
        
        Args:
            headless: Headless 모드 활성화 여부
            timeout: 페이지 로딩 타임아웃 (초)
            user_agent: User-Agent 문자열
            proxy: 프록시 서버 (None이면 사용 안 함)
        """
        self.headless = headless if Config.HEADLESS is None else Config.HEADLESS
        self.timeout = timeout if Config.CRAWL_TIMEOUT is None else Config.CRAWL_TIMEOUT
        # User-Agent 로테이션 (매번 랜덤 선택)
        self.user_agent = user_agent or Config.USER_AGENT or random.choice(USER_AGENTS)
        self.proxy = proxy
        self.driver: Optional[webdriver.Chrome] = None
        self.request_count = 0  # 요청 카운터 (딜레이 조절용)
        
        proxy_info = f", proxy={proxy}" if proxy else ""
        logger.info(
            f"InvestingCrawler initialized - "
            f"headless={self.headless}, timeout={self.timeout}s{proxy_info}"
        )

    def _init_driver(self) -> None:
        """Chrome WebDriver 초기화 (investing.com 최적화)"""
        try:
            options = Options()
            
            if self.headless:
                options.add_argument('--headless=new')
            
            # 기본 옵션
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            
            # User-Agent 설정
            options.add_argument(f'user-agent={self.user_agent}')
            
            # 로깅 최소화
            options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--log-level=3')
            
            # 언어 설정 (영문)
            options.add_argument('--lang=en-US')
            prefs = {
                'intl.accept_languages': 'en-US,en',
                'profile.managed_default_content_settings.images': 2  # 이미지 비활성화 (속도 향상)
            }
            options.add_experimental_option('prefs', prefs)
            
            # 프록시 설정 (있는 경우)
            if self.proxy:
                options.add_argument(f'--proxy-server={self.proxy}')
                logger.info(f"Using proxy: {self.proxy}")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(self.timeout)
            
            # JavaScript webdriver 플래그 제거
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                '''
            })
            
            logger.debug("Chrome WebDriver initialized for investing.com")
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def _close_driver(self) -> None:
        """Chrome WebDriver 종료"""
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("Chrome WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Context manager 진입"""
        self._init_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self._close_driver()

    def get_news_url(self, ticker: str) -> str:
        """
        티커에 해당하는 investing.com 뉴스 URL 생성
        
        Args:
            ticker: 티커 심볼 (예: TSLA)
        
        Returns:
            investing.com 뉴스 URL
        """
        ticker_upper = ticker.upper()
        
        # 주식 매핑 확인
        slug = TICKER_TO_INVESTING_SLUG.get(ticker_upper)
        if slug:
            url = f"{self.BASE_URL}/equities/{slug}-news"
            logger.debug(f"News URL for {ticker}: {url}")
            return url
        
        # ETF 매핑 확인
        etf_slug = TICKER_TO_ETF_SLUG.get(ticker_upper)
        if etf_slug:
            url = f"{self.BASE_URL}/etfs/{etf_slug}-news"
            logger.debug(f"ETF News URL for {ticker}: {url}")
            return url
        
        # 매핑이 없는 경우 검색 URL 사용
        url = f"{self.BASE_URL}/search/?q={ticker}&tab=news"
        
        logger.debug(f"News URL for {ticker}: {url}")
        return url

    def fetch_news(
        self,
        ticker: str,
        company_name: str,
        hours_ago: int = 3,
        max_articles: int = 10,
        add_delay: bool = True
    ) -> List[Dict[str, str]]:
        """
        Investing.com에서 뉴스 수집
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            hours_ago: 최근 N시간 (기본: 3시간, 0이면 시간 필터 무시)
            max_articles: 최대 수집 기사 수 (기본: 10개)
            add_delay: 봇 차단 방지를 위한 딜레이 추가 여부 (기본: True)
        
        Returns:
            뉴스 리스트 [{'title': ..., 'content': ..., 'url': ..., 'date': ...}, ...]
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized. Use context manager.")
        
        # 요청 전 랜덤 딜레이 (봇 차단 방지)
        if add_delay and self.request_count > 0:
            delay = random.uniform(10, 15)  # 10-15초 랜덤 딜레이
            logger.info(f"Waiting {delay:.1f}s before next request (anti-bot)...")
            time.sleep(delay)
        
        self.request_count += 1
        
        url = self.get_news_url(ticker)
        # hours_ago가 0이면 시간 필터 무시 (아주 오래 전 시간으로 설정)
        if hours_ago <= 0:
            cutoff_time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        else:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        
        try:
            logger.info(f"Fetching news for {ticker} from {url}")
            
            # 페이지 로딩
            try:
                self.driver.get(url)
            except Exception as e:
                logger.warning(f"Page load error for {ticker}: {e}")
                return []
            
            # 페이지 로딩 대기 (더 긴 시간)
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for body element: {ticker}")
                return []
            
            # 동적 컨텐츠 로딩 대기 (더 긴 시간)
            time.sleep(5)
            
            # 쿠키 동의 팝업 처리
            self._handle_cookie_popup()
            
            # 추가 대기 (봇 감지 방지)
            time.sleep(2)
            
            # 뉴스 아이템 파싱
            news_items = self._parse_news_articles(ticker, company_name, cutoff_time, max_articles)
            
            logger.info(f"Collected {len(news_items)} news items for {ticker} from investing.com")
            
            return news_items
            
        except TimeoutException:
            logger.error(f"Timeout loading page: {url}")
            return []
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}", exc_info=True)
            return []

    def _handle_cookie_popup(self) -> None:
        """쿠키 동의 팝업 처리"""
        try:
            # 다양한 쿠키 동의 버튼 셀렉터 시도
            cookie_selectors = [
                'button[id*="accept"]',
                'button[class*="accept"]',
                '[data-test="consent-accept"]',
                '#onetrust-accept-btn-handler',
                '.js-accept-cookies',
            ]
            
            for selector in cookie_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        btn.click()
                        logger.debug(f"Cookie popup handled with: {selector}")
                        time.sleep(1)
                        return
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            logger.debug(f"No cookie popup or already handled: {e}")

    def _parse_news_articles(
        self,
        ticker: str,
        company_name: str,
        cutoff_time: datetime,
        max_articles: int = 10
    ) -> List[Dict[str, str]]:
        """
        Investing.com 뉴스 기사 파싱
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            cutoff_time: 필터링 기준 시간
            max_articles: 최대 수집 기사 수
        
        Returns:
            뉴스 리스트
        """
        news_items = []
        
        try:
            # investing.com의 뉴스 아티클 셀렉터
            # data-test="article-item" 속성을 가진 article 태그
            article_selectors = [
                'article[data-test="article-item"]',
                'article.js-article-item',
                'article[class*="article"]',
                '.articleItem',
                'div[data-test="news-item"]',
                # ETF 페이지용 셀렉터
                'div.largeTitle article',
                'div.mediumTitle1 article',
                '[class*="news"] article',
            ]
            
            articles = []
            for selector in article_selectors:
                try:
                    articles = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if articles:
                        logger.debug(f"Found {len(articles)} articles with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not articles:
                logger.warning(f"No news articles found for {ticker}")
                return []
            
            # 최대 기사 수만큼 수집
            for article in articles[:max_articles * 2]:  # 시간 필터링 고려하여 2배로 탐색
                try:
                    news_data = self._extract_article_data(article, ticker, company_name, cutoff_time)
                    if news_data:
                        news_items.append(news_data)
                        if len(news_items) >= max_articles:
                            break
                except StaleElementReferenceException:
                    logger.debug("Stale element, skipping...")
                    continue
                except Exception as e:
                    logger.debug(f"Failed to extract article: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing news articles: {e}", exc_info=True)
        
        return news_items

    def _extract_article_data(
        self,
        article,
        ticker: str,
        company_name: str,
        cutoff_time: datetime
    ) -> Optional[Dict[str, str]]:
        """
        단일 기사에서 데이터 추출
        
        Args:
            article: Selenium WebElement
            ticker: 티커 심볼
            company_name: 회사명
            cutoff_time: 필터링 기준 시간
        
        Returns:
            뉴스 데이터 딕셔너리 또는 None
        """
        try:
            # 제목과 링크 추출
            title_elem = None
            url = None
            
            # 제목 링크 찾기 (여러 셀렉터 시도)
            title_selectors = [
                'a[data-test="article-title-link"]',
                'a.title',
                'h3 a',
                'h2 a',
                'a[href*="/news/"]',
                'a[href*="/analysis/"]',
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = article.find_element(By.CSS_SELECTOR, selector)
                    if title_elem:
                        break
                except NoSuchElementException:
                    continue
            
            if not title_elem:
                return None
            
            title = title_elem.text.strip()
            url = title_elem.get_attribute('href')
            
            if not title or not url:
                return None
            
            # 전체 URL로 변환
            if url.startswith('/'):
                url = f"{self.BASE_URL}{url}"
            
            # 날짜 추출
            article_date = self._extract_date(article)
            
            # 시간 필터링
            if article_date and article_date < cutoff_time:
                logger.debug(f"Skipping old article: {title[:50]}... ({article_date})")
                return None
            
            # 요약/설명 추출
            content = ""
            content_selectors = [
                'p[data-test="article-description"]',
                '.articleDescription',
                'p.description',
                'p',
            ]
            
            for selector in content_selectors:
                try:
                    content_elem = article.find_element(By.CSS_SELECTOR, selector)
                    content = content_elem.text.strip()
                    if content:
                        break
                except NoSuchElementException:
                    continue
            
            return {
                'title': title,
                'content': content,
                'source_url': url,  # SRS v1.1: 실제 기사 URL
                'source_name': 'Investing.com',  # SRS v1.1: 뉴스 출처명
                'date': article_date.isoformat() if article_date else datetime.now(timezone.utc).isoformat(),
                'ticker': ticker,
                'company_name': company_name
            }
            
        except Exception as e:
            logger.debug(f"Error extracting article data: {e}")
            return None

    def _extract_date(self, article) -> Optional[datetime]:
        """
        기사에서 날짜 추출
        
        Args:
            article: Selenium WebElement
        
        Returns:
            datetime 객체 또는 None
        """
        date_selectors = [
            'time[data-test="article-publish-date"]',
            'time',
            'span[data-test="article-publish-date"]',
            '.date',
            '.articleDetails span',
            '[datetime]',
        ]
        
        for selector in date_selectors:
            try:
                date_elem = article.find_element(By.CSS_SELECTOR, selector)
                
                # datetime 속성 우선
                date_str = date_elem.get_attribute('datetime')
                if not date_str:
                    date_str = date_elem.text.strip()
                
                if date_str:
                    return self._parse_date(date_str)
                    
            except NoSuchElementException:
                continue
            except Exception:
                continue
        
        return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        날짜 문자열 파싱
        
        Args:
            date_str: 날짜 문자열
        
        Returns:
            datetime 객체 또는 None
        """
        if not date_str:
            return None
        
        # dateutil.parser 사용
        try:
            parsed = date_parser.parse(date_str)
            # timezone-naive인 경우 UTC로 가정
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            pass
        
        # 상대 시간 파싱 ("2 hours ago", "1 day ago", "Just now")
        date_str_lower = date_str.lower()
        
        if 'just now' in date_str_lower or 'moments ago' in date_str_lower:
            return datetime.now(timezone.utc)
        
        if 'ago' in date_str_lower:
            try:
                # 숫자 추출
                numbers = re.findall(r'\d+', date_str)
                if not numbers:
                    return datetime.now(timezone.utc)
                
                value = int(numbers[0])
                
                if 'second' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(seconds=value)
                elif 'minute' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(minutes=value)
                elif 'hour' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(hours=value)
                elif 'day' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(days=value)
                elif 'week' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(weeks=value)
                elif 'month' in date_str_lower:
                    return datetime.now(timezone.utc) - timedelta(days=value * 30)
                    
            except (ValueError, AttributeError):
                pass
        
        logger.debug(f"Could not parse date: {date_str}")
        return None

    def crawl_with_retry(
        self,
        ticker: str,
        company_name: str,
        hours_ago: int = 3,
        max_articles: int = 10,
        max_retries: int = 2,
        retry_delay: int = 10
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        재시도 로직을 포함한 크롤링
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            hours_ago: 최근 N시간
            max_articles: 최대 수집 기사 수
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
        
        Returns:
            (뉴스 리스트, 에러 메시지)
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Crawling investing.com attempt {attempt}/{max_retries} for {ticker}"
                )
                
                news_items = self.fetch_news(ticker, company_name, hours_ago, max_articles)
                
                if news_items:
                    logger.info(f"Successfully fetched {len(news_items)} items for {ticker}")
                    return news_items, None
                
                # 빈 결과
                logger.info(f"No news found for {ticker} (attempt {attempt})")
                
                if attempt < max_retries:
                    retry_wait = retry_delay + random.uniform(0, 5)  # 랜덤 추가 딜레이
                    logger.debug(f"Waiting {retry_wait:.1f}s before retry...")
                    time.sleep(retry_wait)
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed for {ticker}: {e}"
                )
                
                if attempt < max_retries:
                    retry_wait = retry_delay + random.uniform(0, 5)
                    time.sleep(retry_wait)
        
        # 모든 재시도 실패
        error_msg = last_error or "No news found after all retries"
        logger.error(f"All crawl attempts failed for {ticker}: {error_msg}")
        
        return [], error_msg


def get_next_proxy() -> Optional[str]:
    """
    프록시 로테이션 (스레드 안전)
    
    Returns:
        다음 프록시 주소 또는 None
    """
    global proxy_index
    
    if not PROXY_LIST:
        return None
    
    with proxy_lock:
        proxy = PROXY_LIST[proxy_index % len(PROXY_LIST)]
        proxy_index += 1
        return proxy


def crawl_single_stock(
    ticker: str,
    company_name: str,
    hours_ago: int = 0,
    max_articles: int = 10,
    use_proxy: bool = True
) -> Tuple[str, List[Dict[str, str]], Optional[str]]:
    """
    단일 종목 크롤링 (멀티스레드용)
    
    Args:
        ticker: 티커 심볼
        company_name: 회사명
        hours_ago: 최근 N시간 (0이면 제한 없음)
        max_articles: 최대 수집 기사 수
        use_proxy: 프록시 사용 여부
    
    Returns:
        (티커, 뉴스 리스트, 에러 메시지)
    """
    proxy = get_next_proxy() if use_proxy else None
    
    try:
        with InvestingCrawler(proxy=proxy) as crawler:
            articles = crawler.fetch_news(
                ticker, 
                company_name, 
                hours_ago=hours_ago, 
                max_articles=max_articles,
                add_delay=False  # 멀티스레드에서는 딜레이 불필요
            )
            
            # 메타데이터 추가
            for article in articles:
                article['symbol'] = ticker
                article['ticker'] = ticker
                article['company_name'] = company_name
            
            logger.info(f"[{ticker}] Successfully crawled {len(articles)} articles")
            return ticker, articles, None
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"[{ticker}] Crawling failed: {error_msg}")
        return ticker, [], error_msg


def batch_crawl_parallel(
    stocks: List[Tuple[str, str]],
    hours_ago: int = 0,
    max_articles: int = 10,
    max_workers: int = 5,
    use_proxy: bool = True
) -> Dict[str, List[Dict[str, str]]]:
    """
    멀티스레드 배치 크롤링
    
    Args:
        stocks: [(ticker, company_name), ...] 리스트
        hours_ago: 최근 N시간 (0이면 제한 없음)
        max_articles: 종목당 최대 수집 기사 수
        max_workers: 최대 스레드 수
        use_proxy: 프록시 사용 여부
    
    Returns:
        {ticker: [articles], ...} 딕셔너리
    """
    results = {}
    
    logger.info(
        f"Starting parallel crawl for {len(stocks)} stocks "
        f"(workers={max_workers}, proxy={use_proxy})"
    )
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 종목에 대해 크롤링 태스크 제출
        future_to_ticker = {
            executor.submit(
                crawl_single_stock,
                ticker,
                company_name,
                hours_ago,
                max_articles,
                use_proxy
            ): ticker
            for ticker, company_name in stocks
        }
        
        # 완료된 태스크 수집
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker_result, articles, error = future.result()
                results[ticker_result] = articles
                
                if error:
                    logger.warning(f"[{ticker_result}] Error: {error}")
                else:
                    logger.info(f"[{ticker_result}] Collected {len(articles)} articles")
                    
            except Exception as e:
                logger.error(f"[{ticker}] Unexpected error: {e}", exc_info=True)
                results[ticker] = []
    
    total_articles = sum(len(articles) for articles in results.values())
    logger.info(
        f"Parallel crawl completed: {total_articles} total articles "
        f"from {len([r for r in results.values() if r])} successful stocks"
    )
    
    return results


# 하위 호환성을 위한 별칭
NewsCrawler = InvestingCrawler
SeleniumCrawler = InvestingCrawler
