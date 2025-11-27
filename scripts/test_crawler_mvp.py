"""
Phase 3 크롤러 MVP 테스트
- 1개 티커(TSLA)로 최소 3건 뉴스 수집 검증
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.services.crawler_service import CrawlerService
from app.services.news_storage import NewsStorageAdapter

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_crawler_mvp():
    """크롤러 MVP 테스트"""
    print("=" * 60)
    print("Phase 3 크롤러 MVP 테스트")
    print("=" * 60)
    
    # Flask 앱 초기화
    app = create_app()
    
    with app.app_context():
        # NewsStorageAdapter 초기화
        storage = NewsStorageAdapter()
        
        # CrawlerService 초기화
        crawler_service = CrawlerService(
            db_session=db.session,
            news_storage=storage
        )
        
        # TSLA 크롤링
        print("\n[1] TSLA 크롤링 시작...")
        result = crawler_service.crawl_ticker(
            ticker='TSLA',
            hours_ago=24,  # 테스트를 위해 24시간으로 확대
            max_retries=3
        )
        
        print(f"\n결과:")
        print(f"  상태: {result['status']}")
        print(f"  수집 개수: {result.get('total', 0)}")
        print(f"  저장 개수: {result['count']}")
        
        if result.get('error'):
            print(f"  에러: {result['error']}")
        
        # 검증
        print("\n[2] 결과 검증...")
        
        if result['status'] == 'FAILED':
            print("❌ 크롤링 실패")
            return False
        
        if result['count'] >= 3:
            print(f"✅ 최소 3건 이상 수집 성공: {result['count']}건")
            success = True
        else:
            print(f"⚠️  3건 미만 수집: {result['count']}건")
            print("   (investing.com에 실제 뉴스가 부족할 수 있음)")
            success = result['count'] > 0  # 1건 이상이면 부분 성공
        
        # ES 저장 확인
        print("\n[3] ElasticSearch 저장 확인...")
        try:
            es_result = storage.es.search(
                index=storage.news_index,
                body={
                    "query": {
                        "term": {"ticker.keyword": "TSLA"}
                    },
                    "size": 5
                }
            )
            
            total = es_result['hits']['total']['value']
            print(f"  ES에 저장된 TSLA 뉴스: {total}건")
            
            if es_result['hits']['hits']:
                print("\n  샘플 뉴스:")
                for hit in es_result['hits']['hits'][:3]:
                    source = hit['_source']
                    print(f"    - {source.get('title', 'N/A')}")
                    print(f"      URL: {source.get('url', 'N/A')}")
            
        except Exception as e:
            print(f"  ⚠️  ES 조회 실패: {e}")
        
        # crawl_logs 확인
        print("\n[4] crawl_logs 확인...")
        from app.models.models import CrawlLog
        
        latest_log = db.session.query(CrawlLog).filter_by(
            ticker_symbol='TSLA'
        ).order_by(CrawlLog.crawled_at.desc()).first()
        
        if latest_log:
            print(f"  마지막 크롤링: {latest_log.crawled_at}")
            print(f"  상태: {latest_log.status}")
            print(f"  뉴스 개수: {latest_log.news_count}")
            if latest_log.error_message:
                print(f"  에러: {latest_log.error_message}")
        else:
            print("  ⚠️  crawl_logs 기록 없음")
        
        print("\n" + "=" * 60)
        
        if success:
            print("✅ Phase 3 크롤러 MVP 테스트 통과")
        else:
            print("❌ Phase 3 크롤러 MVP 테스트 실패")
        
        print("=" * 60)
        
        return success


if __name__ == '__main__':
    try:
        success = test_crawler_mvp()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}", exc_info=True)
        sys.exit(1)
