"""
Investing.com 크롤러 테스트 스크립트
"""

import sys
sys.path.insert(0, '/Users/jht/Desktop/Projects/stockAnalysis')

from app.services.crawler import InvestingCrawler
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_investing_crawler():
    """Investing.com 크롤러 테스트"""
    print("=" * 60)
    print("Investing.com 크롤러 테스트")
    print("=" * 60)
    
    ticker = "TSLA"
    company_name = "Tesla Inc."
    hours_ago = 24  # 최근 24시간
    
    print(f"\n테스트: {ticker} ({company_name}) 뉴스 수집")
    print(f"기간: 최근 {hours_ago}시간")
    print("-" * 60)
    
    try:
        with InvestingCrawler(headless=True) as crawler:
            news_items, error = crawler.crawl_with_retry(
                ticker=ticker,
                company_name=company_name,
                hours_ago=hours_ago,
                max_retries=2
            )
            
            print(f"\n✓ 수집된 뉴스 개수: {len(news_items)}")
            
            if error:
                print(f"⚠ 에러: {error}")
            
            if news_items:
                print("\n수집된 뉴스 샘플:")
                print("-" * 60)
                
                for i, item in enumerate(news_items[:5], 1):
                    print(f"\n[{i}] {item.get('title', 'N/A')[:80]}")
                    print(f"    URL: {item.get('url', 'N/A')[:60]}...")
                    print(f"    날짜: {item.get('date', 'N/A')}")
                    print(f"    출처: {item.get('source', 'N/A')}")
                    content = item.get('content', '')
                    if content:
                        print(f"    내용: {content[:100]}...")
            else:
                print("\n⚠ 수집된 뉴스가 없습니다.")
        
        print("\n" + "=" * 60)
        print("테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_investing_crawler()
