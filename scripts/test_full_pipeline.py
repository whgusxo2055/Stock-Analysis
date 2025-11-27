"""
전체 파이프라인 통합 테스트
- 크롤링 → 분석 → 저장 전체 플로우 검증
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.services.crawler_service import CrawlerService
from app.services.news_storage import NewsStorageAdapter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_full_pipeline():
    """전체 파이프라인 통합 테스트"""
    print("=" * 60)
    print("전체 파이프라인 통합 테스트")
    print("크롤링 → 중복 체크 → 분석 → ES 저장")
    print("=" * 60)
    
    # Flask 앱 초기화
    app = create_app()
    
    with app.app_context():
        # 서비스 초기화
        storage = NewsStorageAdapter()
        
        # DB 세션 없이 테스트용으로 간단히 초기화
        # 실제로는 CrawlerService 없이 직접 analyzer 사용
        from app.services.news_analyzer import get_news_analyzer
        analyzer = get_news_analyzer()
        
        print("\n[1] 서비스 초기화 확인")
        print(f"   ✓ NewsStorageAdapter: {type(storage).__name__}")
        print(f"   ✓ NewsAnalyzer: {type(analyzer).__name__}")
        
        # 테스트용 가짜 뉴스 데이터
        test_news = [
            {
                'title': 'Apple Unveils New AI-Powered MacBook Pro',
                'content': 'Apple Inc. today announced a revolutionary MacBook Pro featuring advanced AI capabilities...',
                'url': 'https://example.com/apple-macbook-ai-2024',
                'published_date': '2024-01-15',
                'source': 'Tech News'
            },
            {
                'title': 'Tesla Expands Supercharger Network in Europe',
                'content': 'Tesla continues its expansion with 500 new Supercharger stations across Europe...',
                'url': 'https://example.com/tesla-supercharger-europe',
                'published_date': '2024-01-15',
                'source': 'Auto World'
            }
        ]
        
        print("\n[2] 테스트 데이터 준비")
        print(f"   뉴스 개수: {len(test_news)}건")
        
        # 중복 체크
        print("\n[3] URL 중복 체크")
        urls = [item['url'] for item in test_news]
        existing_urls = storage.check_duplicates(urls)
        
        if existing_urls:
            print(f"   ⚠️  중복 URL 발견: {len(existing_urls)}건")
            for url in existing_urls:
                print(f"      - {url}")
        else:
            print("   ✓ 중복 없음")
        
        # 중복 제거
        unique_news = [
            item for item in test_news 
            if item['url'] not in existing_urls
        ]
        
        if not unique_news:
            print("\n   모든 뉴스가 이미 저장되어 있습니다.")
            print("   ES에서 기존 데이터 확인...")
            
            # ES에서 검색
            for url in urls:
                results = storage.search_news(
                    query={'match': {'url': url}},
                    size=1
                )
                if results:
                    news = results[0]
                    print(f"\n   저장된 뉴스:")
                    print(f"      제목: {news.get('title')}")
                    print(f"      요약(한): {news.get('summary', {}).get('ko', 'N/A')[:60]}...")
                    print(f"      감성: {news.get('sentiment', {}).get('classification')} "
                          f"({news.get('sentiment', {}).get('score')})")
            return True
        
        print(f"\n[4] 신규 뉴스: {len(unique_news)}건")
        
        # 메타데이터 추가
        for item in unique_news:
            item['ticker'] = 'AAPL' if 'Apple' in item['title'] else 'TSLA'
            item['company_name'] = 'Apple Inc.' if item['ticker'] == 'AAPL' else 'Tesla Inc.'
        
        # 뉴스 분석
        print("\n[5] 뉴스 분석 실행")
        analyzed_items = analyzer.batch_analyze(unique_news)
        
        print(f"   분석 완료: {len(analyzed_items)}/{len(unique_news)}건")
        
        if not analyzed_items:
            print("   ❌ 분석 실패")
            return False
        
        # 분석 결과 확인
        for i, item in enumerate(analyzed_items, 1):
            print(f"\n   [{i}] {item['title'][:50]}...")
            print(f"      요약(한): {item['summary']['ko'][:60]}...")
            print(f"      감성: {item['sentiment']['classification']} "
                  f"({item['sentiment']['score']})")
        
        # ES 저장
        print("\n[6] ElasticSearch 저장")
        result = storage.bulk_save_news(analyzed_items)
        
        print(f"   성공: {result['success']}건")
        print(f"   실패: {result['failed']}건")
        
        if result['failed'] > 0:
            print("   실패 상세:")
            for error in result['errors'][:3]:  # 최대 3개만 표시
                print(f"      - {error}")
        
        # ES 검색 확인
        print("\n[7] 저장된 데이터 검증")
        for item in analyzed_items[:2]:  # 최대 2개만 검증
            results = storage.search_news(
                query={'match': {'url': item['url']}},
                size=1
            )
            
            if results:
                saved = results[0]
                print(f"\n   ✓ 검증 성공: {saved['title'][:40]}...")
                print(f"      ID: {saved.get('_id', 'N/A')}")
                print(f"      종목: {saved.get('ticker')}")
                print(f"      요약: {len(saved.get('summary', {}))}개 언어")
                print(f"      감성: {saved.get('sentiment', {}).get('classification')}")
            else:
                print(f"\n   ❌ 검증 실패: {item['url']}")
        
        print("\n" + "=" * 60)
        print("✅ 전체 파이프라인 통합 테스트 완료")
        print("=" * 60)
        
        return True


if __name__ == '__main__':
    try:
        success = test_full_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"테스트 실패: {e}", exc_info=True)
        sys.exit(1)
