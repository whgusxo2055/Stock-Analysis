"""
Phase 2 통합 테스트
End-to-End 검증: 저장 → 조회 → 통계 → 삭제 플로우
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta
from app.services.news_storage import get_news_storage
from app.utils.elasticsearch_client import get_es_client


class TestPhase2Integration:
    """Phase 2 통합 테스트"""
    
    @pytest.fixture
    def storage(self):
        """저장 어댑터 픽스처"""
        return get_news_storage()
    
    @pytest.fixture
    def es_client(self):
        """ES 클라이언트 픽스처"""
        return get_es_client()
    
    @pytest.fixture(autouse=True)
    def cleanup(self, storage):
        """각 테스트 후 정리"""
        yield
        # 테스트 데이터 정리 (test_로 시작하는 ID)
        try:
            storage.es_client.client.delete_by_query(
                index=storage.es_client.index_name,
                query={
                    "prefix": {
                        "news_id": "test_integration_"
                    }
                }
            )
        except:
            pass
    
    def test_complete_news_lifecycle(self, storage):
        """
        완전한 뉴스 라이프사이클 테스트
        1. 저장 → 2. 조회 → 3. 검색 → 4. 통계 → 5. 삭제
        """
        print("\n=== 뉴스 라이프사이클 통합 테스트 ===")
        
        # 1. 저장
        print("\n[1단계] 뉴스 저장")
        news_data = {
            "news_id": "test_integration_001",
            "ticker_symbol": "005930",
            "company_name": "삼성전자",
            "title": "Samsung announces breakthrough in AI chip technology",
            "content": "Samsung Electronics has developed a revolutionary AI processing chip that promises 50% better performance...",
            "url": "https://example.com/news/ai-chip",
            "published_date": datetime.now().isoformat(),
            "summary": {
                "ko": "삼성전자, AI 칩 기술 혁신 발표",
                "en": "Samsung announces AI chip breakthrough",
                "es": "Samsung anuncia avance en tecnología de chips de IA",
                "ja": "サムスン、AIチップ技術の革新を発表"
            },
            "sentiment": {
                "classification": "positive",
                "score": 88
            }
        }
        
        result = storage.save_news(news_data)
        assert result is True, "뉴스 저장 실패"
        print("✓ 뉴스 저장 완료")
        
        # ES refresh (실시간 검색)
        storage.es_client.client.indices.refresh(
            index=storage.es_client.index_name
        )
        
        # 2. 조회
        print("\n[2단계] 뉴스 조회")
        retrieved = storage.get_news("test_integration_001")
        assert retrieved is not None, "저장된 뉴스를 찾을 수 없음"
        assert retrieved['ticker_symbol'] == "005930"
        assert retrieved['sentiment']['score'] == 88
        print(f"✓ 뉴스 조회 성공: {retrieved['title']}")
        
        # 3. 검색
        print("\n[3단계] 검색 기능 테스트")
        
        # 3-1. 종목별 검색
        search_result = storage.search_news(ticker_symbol="005930")
        assert search_result['total'] >= 1
        print(f"✓ 종목별 검색: {search_result['total']}건")
        
        # 3-2. 키워드 검색
        keyword_result = storage.search_news(keyword="AI chip")
        assert keyword_result['total'] >= 1
        print(f"✓ 키워드 검색: {keyword_result['total']}건")
        
        # 3-3. 감정 필터 검색
        sentiment_result = storage.search_news(
            ticker_symbol="005930",
            sentiment="positive"
        )
        assert sentiment_result['total'] >= 1
        print(f"✓ 감정 필터 검색: {sentiment_result['total']}건")
        
        # 4. 통계
        print("\n[4단계] 통계 조회")
        stats = storage.get_statistics("005930", days=7)
        assert stats['total'] >= 1
        assert stats['avg_score'] > 0
        print(f"✓ 통계 조회 완료:")
        print(f"  - 총 뉴스: {stats['total']}")
        print(f"  - 평균 점수: {stats['avg_score']:.2f}")
        
        # 5. 삭제
        print("\n[5단계] 뉴스 삭제")
        delete_result = storage.delete_news("test_integration_001")
        assert delete_result is True
        print("✓ 뉴스 삭제 완료")
        
        # 삭제 확인
        deleted_news = storage.get_news("test_integration_001")
        assert deleted_news is None
        print("✓ 삭제 확인 완료")
        
        print("\n=== 라이프사이클 테스트 완료 ===")
    
    def test_bulk_operations_workflow(self, storage):
        """
        벌크 작업 워크플로우 테스트 (Phase 3 크롤러 시뮬레이션)
        """
        print("\n=== 벌크 작업 워크플로우 테스트 ===")
        
        # 1. 크롤러가 수집한 뉴스 시뮬레이션
        print("\n[1단계] 크롤러 뉴스 수집 시뮬레이션")
        crawled_news = []
        
        companies = [
            ("005930", "삼성전자"),
            ("035420", "NAVER"),
            ("000660", "SK하이닉스")
        ]
        
        for i, (ticker, company) in enumerate(companies):
            for j in range(3):  # 각 종목당 3개 뉴스
                crawled_news.append({
                    "news_id": f"test_integration_bulk_{i}_{j}",
                    "ticker_symbol": ticker,
                    "company_name": company,
                    "title": f"{company} news {j+1}",
                    "content": f"Latest news about {company}...",
                    "published_date": (datetime.now() - timedelta(hours=j)).isoformat(),
                    "sentiment": {
                        "classification": ["positive", "neutral", "negative"][j % 3],
                        "score": [80, 50, 30][j % 3]
                    }
                })
        
        print(f"✓ 총 {len(crawled_news)}개 뉴스 수집 완료")
        
        # 2. 벌크 저장
        print("\n[2단계] 벌크 저장")
        bulk_result = storage.bulk_save_news(crawled_news)
        assert bulk_result['success'] == 9
        assert bulk_result['failed'] == 0
        print(f"✓ 벌크 저장 완료: {bulk_result['success']}/{bulk_result['total']}")
        
        # ES refresh
        storage.es_client.client.indices.refresh(
            index=storage.es_client.index_name
        )
        
        # 3. 종목별 분석
        print("\n[3단계] 종목별 뉴스 분석")
        for ticker, company in companies:
            # 최신 뉴스 조회
            latest = storage.get_latest_news(ticker, limit=3)
            assert len(latest) == 3
            print(f"✓ {company} 최신 뉴스: {len(latest)}건")
            
            # 통계 조회
            stats = storage.get_statistics(ticker, days=1)
            assert stats['total'] >= 3
            print(f"  - 통계: {stats['total']}건, 평균 점수: {stats['avg_score']:.1f}")
        
        # 4. 전체 검색
        print("\n[4단계] 전체 검색 및 페이지네이션")
        
        # 페이지 1
        page1 = storage.search_news(size=5, page=1)
        assert len(page1['hits']) == 5
        print(f"✓ 페이지 1: {len(page1['hits'])}건")
        
        # 페이지 2
        page2 = storage.search_news(size=5, page=2)
        assert len(page2['hits']) == 4  # 나머지 4건
        print(f"✓ 페이지 2: {len(page2['hits'])}건")
        
        # 5. 정리
        print("\n[5단계] 데이터 정리")
        for news in crawled_news:
            storage.delete_news(news['news_id'])
        print("✓ 모든 테스트 데이터 삭제 완료")
        
        print("\n=== 벌크 워크플로우 테스트 완료 ===")
    
    def test_elasticsearch_index_and_ilm(self, es_client):
        """
        ElasticSearch 인덱스 및 ILM 정책 통합 테스트
        """
        print("\n=== ES 인덱스 & ILM 통합 테스트 ===")
        
        # 1. 인덱스 존재 확인
        print("\n[1단계] 인덱스 확인")
        index_name = es_client.index_name
        exists = es_client.client.indices.exists(index=index_name)
        assert exists, f"인덱스 '{index_name}'가 존재하지 않음"
        print(f"✓ 인덱스 '{index_name}' 존재 확인")
        
        # 2. 매핑 확인
        print("\n[2단계] 매핑 구조 확인")
        mappings = es_client.client.indices.get_mapping(index=index_name)
        properties = mappings[index_name]['mappings']['properties']
        
        required_fields = [
            'news_id', 'ticker_symbol', 'title', 'content',
            'published_date', 'summary', 'sentiment'
        ]
        
        for field in required_fields:
            assert field in properties, f"필수 필드 '{field}' 누락"
        print(f"✓ 모든 필수 필드 존재 확인 ({len(required_fields)}개)")
        
        # 3. ILM 정책 확인
        print("\n[3단계] ILM 정책 확인")
        policy_name = "news_retention_policy"
        policies = es_client.client.ilm.get_lifecycle()
        
        assert policy_name in policies, f"ILM 정책 '{policy_name}' 없음"
        print(f"✓ ILM 정책 '{policy_name}' 존재")
        
        # 4. 인덱스에 ILM 적용 확인
        print("\n[4단계] 인덱스 ILM 적용 상태")
        settings = es_client.client.indices.get_settings(index=index_name)
        lifecycle = settings[index_name]['settings']['index'].get('lifecycle', {})
        
        assert lifecycle.get('name') == policy_name, "ILM 정책이 인덱스에 적용되지 않음"
        print(f"✓ 인덱스에 ILM 정책 적용됨")
        print(f"  - Policy: {lifecycle['name']}")
        print(f"  - Rollover Alias: {lifecycle.get('rollover_alias', 'N/A')}")
        
        # 5. ILM 정책 내용 확인 (2년 보관)
        print("\n[5단계] ILM 정책 내용 검증")
        policy = policies[policy_name]['policy']
        phases = policy['phases']
        
        assert 'delete' in phases, "Delete 단계 없음"
        assert phases['delete']['min_age'] == '730d', "보관 기간이 2년(730d)이 아님"
        print(f"✓ 데이터 보관 정책: {phases['delete']['min_age']} (2년)")
        
        print("\n=== ES 인덱스 & ILM 통합 테스트 완료 ===")
    
    def test_date_range_search(self, storage):
        """날짜 범위 검색 테스트"""
        print("\n=== 날짜 범위 검색 테스트 ===")
        
        # 테스트 데이터 생성 (여러 날짜)
        test_dates = []
        for i in range(5):
            date = datetime.now() - timedelta(days=i)
            test_dates.append({
                "news_id": f"test_integration_date_{i}",
                "ticker_symbol": "005930",
                "company_name": "삼성전자",
                "title": f"News {i}",
                "content": f"Content {i}",
                "published_date": date.isoformat()
            })
        
        storage.bulk_save_news(test_dates)
        storage.es_client.client.indices.refresh(
            index=storage.es_client.index_name
        )
        
        # 최근 3일 검색 (days=2는 2일 전부터이므로 0,1,2 = 3개)
        from_date = (datetime.now() - timedelta(days=2, hours=1)).isoformat()
        to_date = (datetime.now() + timedelta(hours=1)).isoformat()  # 약간 미래로
        
        result = storage.search_news(
            ticker_symbol="005930",
            from_date=from_date,
            to_date=to_date
        )
        
        # 0일, 1일, 2일 = 3개
        assert result['total'] >= 3, f"Expected >= 3, got {result['total']}"
        print(f"✓ 날짜 범위 검색: {result['total']}건")
        
        # 정리
        for news in test_dates:
            storage.delete_news(news['news_id'])
        
        print("=== 날짜 범위 검색 테스트 완료 ===")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
