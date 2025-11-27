"""
뉴스 크롤러 서비스
- Investing.com 전용 Selenium 크롤러
- 3시간마다 실행, 최근 3시간 뉴스 수집
- URL 기반 중복 제거
"""

import logging
import time
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from dateutil import parser as date_parser

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


class InvestingCrawler:
    """Investing.com 전용 Selenium 크롤러"""

    BASE_URL = "https://www.investing.com"
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30,
        user_agent: Optional[str] = None
    ):
        """
        크롤러 초기화
        
        Args:
            headless: Headless 모드 활성화 여부
            timeout: 페이지 로딩 타임아웃 (초)
            user_agent: User-Agent 문자열
        """
        self.headless = headless if Config.HEADLESS is None else Config.HEADLESS
        self.timeout = timeout if Config.CRAWL_TIMEOUT is None else Config.CRAWL_TIMEOUT
        self.user_agent = user_agent or Config.USER_AGENT or \
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        self.driver: Optional[webdriver.Chrome] = None
        
        logger.info(
            f"InvestingCrawler initialized - "
            f"headless={self.headless}, timeout={self.timeout}s"
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
        slug = TICKER_TO_INVESTING_SLUG.get(ticker.upper())
        
        if slug:
            url = f"{self.BASE_URL}/equities/{slug}-news"
        else:
            # 매핑이 없는 경우 검색 URL 사용
            url = f"{self.BASE_URL}/search/?q={ticker}&tab=news"
        
        logger.debug(f"News URL for {ticker}: {url}")
        return url

    def fetch_news(
        self,
        ticker: str,
        company_name: str,
        hours_ago: int = 3
    ) -> List[Dict[str, str]]:
        """
        Investing.com에서 뉴스 수집
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            hours_ago: 최근 N시간
        
        Returns:
            뉴스 리스트 [{'title': ..., 'content': ..., 'url': ..., 'date': ...}, ...]
        """
        if not self.driver:
            raise RuntimeError("WebDriver not initialized. Use context manager.")
        
        url = self.get_news_url(ticker)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        
        try:
            logger.info(f"Fetching news for {ticker} from {url}")
            self.driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 동적 컨텐츠 로딩 대기
            time.sleep(3)
            
            # 쿠키 동의 팝업 처리
            self._handle_cookie_popup()
            
            # 뉴스 아이템 파싱
            news_items = self._parse_news_articles(ticker, company_name, cutoff_time)
            
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
        cutoff_time: datetime
    ) -> List[Dict[str, str]]:
        """
        Investing.com 뉴스 기사 파싱
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            cutoff_time: 필터링 기준 시간
        
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
            
            for article in articles[:20]:  # 최대 20개
                try:
                    news_data = self._extract_article_data(article, ticker, company_name, cutoff_time)
                    if news_data:
                        news_items.append(news_data)
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
                'url': url,
                'date': article_date.isoformat() if article_date else datetime.now(timezone.utc).isoformat(),
                'source': 'investing.com',
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
        max_retries: int = 3,
        retry_delay: int = 5
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        재시도 로직을 포함한 크롤링
        
        Args:
            ticker: 티커 심볼
            company_name: 회사명
            hours_ago: 최근 N시간
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
                
                news_items = self.fetch_news(ticker, company_name, hours_ago)
                
                if news_items:
                    logger.info(f"Successfully fetched {len(news_items)} items for {ticker}")
                    return news_items, None
                
                # 빈 결과
                logger.info(f"No news found for {ticker} (attempt {attempt})")
                
                if attempt < max_retries:
                    logger.debug(f"Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Attempt {attempt}/{max_retries} failed for {ticker}: {e}"
                )
                
                if attempt < max_retries:
                    time.sleep(retry_delay)
        
        # 모든 재시도 실패
        error_msg = last_error or "No news found after all retries"
        logger.error(f"All crawl attempts failed for {ticker}: {error_msg}")
        
        return [], error_msg


# 하위 호환성을 위한 별칭
NewsCrawler = InvestingCrawler
SeleniumCrawler = InvestingCrawler
