"""
investing.com HTML 구조 분석 스크립트
실제 페이지 구조를 확인하여 적절한 CSS 셀렉터 찾기
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def analyze_investing_structure():
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("🔍 Analyzing investing.com structure...\n")
        
        # TSLA 뉴스 검색 페이지
        url = 'https://www.investing.com/search/?q=TSLA&tab=news'
        driver.get(url)
        time.sleep(5)  # 페이지 로딩 대기
        
        print(f"✓ Page Title: {driver.title}\n")
        
        # 다양한 셀렉터 시도
        selectors_to_test = [
            ('article', 'Generic article tag'),
            ('.js-article-item', 'JS article item class'),
            ('[data-test="article"]', 'Data test attribute'),
            ('.article-item', 'Article item class'),
            ('.search-result', 'Search result class'),
            ('.searchResults article', 'Article in search results'),
            ('div[class*="article"]', 'Divs with article in class'),
            ('li[class*="article"]', 'List items with article'),
            ('.searchRes', 'Search results container'),
            ('#fullColumn article', 'Articles in main column'),
            ('.js-news-item', 'JS news item'),
            ('[data-id]', 'Elements with data-id'),
        ]
        
        print("=" * 60)
        print("SELECTOR TEST RESULTS")
        print("=" * 60)
        
        for selector, description in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"✓ [{len(elements):2d} found] {selector:30s} - {description}")
                    
                    # 첫 번째 요소의 구조 샘플 출력
                    if len(elements) > 0:
                        elem = elements[0]
                        print(f"   Sample HTML (first 200 chars):")
                        html = elem.get_attribute('outerHTML')[:200]
                        print(f"   {html}...")
                        print()
                else:
                    print(f"✗ [0 found]  {selector:30s} - {description}")
            except Exception as e:
                print(f"✗ [ERROR]    {selector:30s} - {str(e)[:50]}")
        
        print("\n" + "=" * 60)
        print("PAGE BODY SAMPLE (first 3000 chars)")
        print("=" * 60)
        
        try:
            body = driver.find_element(By.TAG_NAME, 'body')
            html_sample = body.get_attribute('innerHTML')[:3000]
            print(html_sample)
        except Exception as e:
            print(f"Error getting body: {e}")
        
    finally:
        driver.quit()
        print("\n✓ Analysis complete")

if __name__ == '__main__':
    analyze_investing_structure()
