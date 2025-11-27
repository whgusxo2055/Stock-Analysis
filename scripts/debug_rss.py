"""
Yahoo Finance RSS 피드 디버깅
"""

import requests
import feedparser

def test_yahoo_rss():
    ticker = "TSLA"
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    
    print(f"테스트 URL: {rss_url}\n")
    
    try:
        # 1. requests로 직접 가져오기
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(rss_url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Length: {len(response.content)}")
        print(f"\n처음 500자:")
        print(response.text[:500])
        print("\n" + "="*60 + "\n")
        
        # 2. feedparser로 파싱
        feed = feedparser.parse(response.content)
        print(f"Feed Title: {feed.feed.get('title', 'N/A')}")
        print(f"Entries Count: {len(feed.entries)}")
        
        if feed.entries:
            print("\n첫 번째 엔트리:")
            entry = feed.entries[0]
            print(f"  Title: {entry.get('title', 'N/A')}")
            print(f"  Link: {entry.get('link', 'N/A')}")
            print(f"  Published: {entry.get('published', 'N/A')}")
        else:
            print("\n⚠ 엔트리가 비어있습니다!")
            print("\nFeed 구조:")
            print(feed)
            
    except Exception as e:
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_yahoo_rss()
