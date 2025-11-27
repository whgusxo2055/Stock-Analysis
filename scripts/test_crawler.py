"""
개선된 크롤러 테스트 스크립트
RSS 피드 기반 크롤링 테스트
"""

import sys
sys.path.insert(0, '/Users/jht/Desktop/Projects/stockAnalysis')

from app.services.crawler import NewsCrawler
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_rss_crawler():
    """RSS 피드 크롤러 테스트"""
    print("=" * 60)
    print("RSS 피드 크롤러 테스트")
    print("=" * 60)
    
    ticker = "TSLA"
    hours_ago = 24  # 최근 24시간
    
    crawler = NewsCrawler(headless=True)
    
    try:
        print(f"\n테스트 1: RSS 피드로 {ticker} 뉴스 수집...")
        news_items = crawler.fetch_rss_news(ticker, hours_ago)
        
        print(f"\n✓ 수집된 뉴스 개수: {len(news_items)}")
        
        if news_items:
            print("\n첫 번째 뉴스 샘플:")
            print("-" * 60)
            item = news_items[0]
            print(f"제목: {item.get('title', 'N/A')[:100]}")
            print(f"URL: {item.get('url', 'N/A')}")
            print(f"날짜: {item.get('date', 'N/A')}")
            print(f"출처: {item.get('source', 'N/A')}")
            print(f"내용: {item.get('content', 'N/A')[:200]}...")
        else:
            print("⚠ 뉴스를 찾을 수 없습니다.")
        
        print("\n" + "=" * 60)
        print("테스트 2: crawl_with_retry 메서드 테스트...")
        
        with NewsCrawler(headless=True) as crawler2:
            news_list, error = crawler2.crawl_with_retry(
                ticker=ticker,
                company_name="Tesla Inc.",
                hours_ago=hours_ago,
                max_retries=2
            )
            
            print(f"\n✓ 수집된 뉴스: {len(news_list)}개")
            if error:
                print(f"⚠ 에러: {error}")
            else:
                print("✓ 성공!")
        
        print("\n" + "=" * 60)
        print("모든 테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_rss_crawler()
