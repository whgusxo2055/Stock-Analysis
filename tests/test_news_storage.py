"""
뉴스 저장 어댑터 단위 테스트
Phase 2.4 - Unit Tests
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta
from app.services.news_storage import NewsStorageAdapter, get_news_storage
from app.utils.elasticsearch_client import get_es_client


class TestNewsStorageAdapter:
    """NewsStorageAdapter 단위 테스트"""
    
    @pytest.fixture
    def adapter(self):
        """어댑터 픽스처"""
        return get_news_storage()
    
    @pytest.fixture
    def sample_news(self):
        """샘플 뉴스 데이터"""
        return {
            "news_id": "test_unit_001",
            "ticker_symbol": "005930",
            "company_name": "삼성전자",
            "title": "Samsung unveils new AI chip",
            "content": "Samsung Electronics announced the development of a new AI processing chip...",
            "url": "https://example.com/news/001",
            "published_date": datetime.now().isoformat(),
            "summary": {
                "ko": "삼성전자 신규 AI 칩 공개",
                "en": "Samsung unveils new AI chip",
                "es": "Samsung presenta nuevo chip de IA",
                "ja": "サムスン、新しいAIチップを発表"
            },
            "sentiment": {
                "classification": "positive",
                "score": 85
            }
        }
    
    def test_adapter_initialization(self, adapter):
        """어댑터 초기화 테스트"""
        assert adapter is not None
        assert adapter.es_client is not None
        assert adapter.es_client.is_connected()
        print("✓ NewsStorageAdapter 초기화 성공")
    
    def test_singleton_pattern(self):
        """싱글톤 패턴 테스트"""
        adapter1 = get_news_storage()
        adapter2 = get_news_storage()
        assert adapter1 is adapter2
        print("✓ 싱글톤 패턴 동작 확인")
    
    def test_save_news_success(self, adapter, sample_news):
        """단일 뉴스 저장 성공 테스트"""
        result = adapter.save_news(sample_news)
        assert result is True
        print(f"✓ 뉴스 저장 성공: {sample_news['news_id']}")
        
        # 저장된 뉴스 조회
        saved = adapter.get_news(sample_news['news_id'])
        assert saved is not None
        assert saved['ticker_symbol'] == "005930"
        assert saved['sentiment']['score'] == 85
        print("✓ 저장된 뉴스 조회 성공")
        
        # 테스트 데이터 정리
        adapter.delete_news(sample_news['news_id'])
    
    def test_save_news_missing_fields(self, adapter):
        """필수 필드 누락 테스트"""
        incomplete_news = {
            "news_id": "test_incomplete",
            "title": "Incomplete news"
            # ticker_symbol, content, published_date 누락
        }
        
        result = adapter.save_news(incomplete_news)
        assert result is False
        print("✓ 필수 필드 누락 시 저장 실패 확인")
    
    def test_bulk_save_news(self, adapter):
        """벌크 저장 테스트"""
        news_list = []
        for i in range(5):
            news_list.append({
                "news_id": f"test_bulk_{i:03d}",
                "ticker_symbol": "035420",
                "company_name": "NAVER",
                "title": f"Test news {i}",
                "content": f"Test content {i}",
                "published_date": datetime.now().isoformat()
            })
        
        result = adapter.bulk_save_news(news_list)
        assert result['success'] == 5
        assert result['failed'] == 0
        assert result['total'] == 5
        print(f"✓ 벌크 저장 성공: {result['success']}/{result['total']}")
        
        # 저장된 뉴스 확인
        for i in range(5):
            news = adapter.get_news(f"test_bulk_{i:03d}")
            assert news is not None
            assert news['ticker_symbol'] == "035420"
        print("✓ 벌크 저장된 모든 뉴스 조회 성공")
        
        # 테스트 데이터 정리
        for i in range(5):
            adapter.delete_news(f"test_bulk_{i:03d}")
    
    def test_bulk_save_empty_list(self, adapter):
        """빈 리스트 벌크 저장 테스트"""
        result = adapter.bulk_save_news([])
        assert result['success'] == 0
        assert result['failed'] == 0
        assert result['total'] == 0
        print("✓ 빈 리스트 처리 확인")
    
    def test_get_news_not_found(self, adapter):
        """존재하지 않는 뉴스 조회 테스트"""
        news = adapter.get_news("nonexistent_news_id")
        assert news is None
        print("✓ 없는 뉴스 조회 시 None 반환 확인")
    
    def test_search_news_by_ticker(self, adapter):
        """종목별 뉴스 검색 테스트"""
        # 테스트 데이터 생성
        test_news = []
        for i in range(3):
            test_news.append({
                "news_id": f"test_search_{i:03d}",
                "ticker_symbol": "000660",
                "company_name": "SK하이닉스",
                "title": f"SK Hynix news {i}",
                "content": f"Test content {i}",
                "published_date": datetime.now().isoformat()
            })
        
        adapter.bulk_save_news(test_news)
        
        # ES refresh (실시간 검색을 위해)
        adapter.es_client.client.indices.refresh(
            index=adapter.es_client.index_name
        )
        
        # 검색
        result = adapter.search_news(ticker_symbol="000660", size=10)
        assert result['total'] >= 3  # 최소 3개 이상
        assert len(result['hits']) >= 3
        print(f"✓ 종목별 검색 성공: {result['total']} 건")
        
        # 테스트 데이터 정리
        for i in range(3):
            adapter.delete_news(f"test_search_{i:03d}")
    
    def test_search_news_with_keyword(self, adapter):
        """키워드 검색 테스트"""
        # 테스트 데이터 생성
        test_news = {
            "news_id": "test_keyword_001",
            "ticker_symbol": "005930",
            "company_name": "삼성전자",
            "title": "Artificial Intelligence breakthrough",
            "content": "Samsung achieves major AI advancement in semiconductor technology",
            "published_date": datetime.now().isoformat()
        }
        
        adapter.save_news(test_news)
        adapter.es_client.client.indices.refresh(
            index=adapter.es_client.index_name
        )
        
        # 키워드로 검색
        result = adapter.search_news(keyword="Artificial Intelligence", size=10)
        assert result['total'] >= 1
        print(f"✓ 키워드 검색 성공: '{test_news['title']}'")
        
        # 정리
        adapter.delete_news("test_keyword_001")
    
    def test_search_news_with_pagination(self, adapter):
        """페이지네이션 테스트"""
        # 테스트 데이터 생성 (10개)
        test_news_list = []
        for i in range(10):
            test_news_list.append({
                "news_id": f"test_page_{i:03d}",
                "ticker_symbol": "035720",
                "company_name": "카카오",
                "title": f"Kakao news {i}",
                "content": f"Test content {i}",
                "published_date": (datetime.now() - timedelta(days=i)).isoformat()
            })
        
        adapter.bulk_save_news(test_news_list)
        adapter.es_client.client.indices.refresh(
            index=adapter.es_client.index_name
        )
        
        # 페이지 1 (5개)
        result_page1 = adapter.search_news(ticker_symbol="035720", size=5, page=1)
        assert len(result_page1['hits']) == 5
        assert result_page1['page'] == 1
        print(f"✓ 페이지 1: {len(result_page1['hits'])} 건")
        
        # 페이지 2 (5개)
        result_page2 = adapter.search_news(ticker_symbol="035720", size=5, page=2)
        assert len(result_page2['hits']) == 5
        assert result_page2['page'] == 2
        print(f"✓ 페이지 2: {len(result_page2['hits'])} 건")
        
        # 페이지 1과 2의 뉴스가 다름
        page1_ids = [news['news_id'] for news in result_page1['hits']]
        page2_ids = [news['news_id'] for news in result_page2['hits']]
        assert set(page1_ids).isdisjoint(set(page2_ids))
        print("✓ 페이지별 데이터 중복 없음")
        
        # 정리
        for i in range(10):
            adapter.delete_news(f"test_page_{i:03d}")
    
    def test_get_statistics(self, adapter):
        """통계 조회 테스트"""
        # 테스트 데이터 생성
        test_news_list = []
        sentiments = ["positive", "positive", "negative", "neutral"]
        scores = [80, 90, 30, 50]
        
        for i in range(4):
            test_news_list.append({
                "news_id": f"test_stats_{i:03d}",
                "ticker_symbol": "051910",
                "company_name": "LG화학",
                "title": f"LG Chem news {i}",
                "content": f"Test content {i}",
                "published_date": datetime.now().isoformat(),
                "sentiment": {
                    "classification": sentiments[i],
                    "score": scores[i]
                }
            })
        
        adapter.bulk_save_news(test_news_list)
        adapter.es_client.client.indices.refresh(
            index=adapter.es_client.index_name
        )
        
        # 통계 조회
        stats = adapter.get_statistics("051910", days=7)
        assert stats['total'] >= 4
        assert stats['avg_score'] > 0
        print(f"✓ 통계 조회 성공:")
        print(f"  - 총 뉴스: {stats['total']}")
        print(f"  - 평균 점수: {stats['avg_score']:.2f}")
        print(f"  - 감정 분포: {stats['sentiment_distribution']}")
        
        # 정리
        for i in range(4):
            adapter.delete_news(f"test_stats_{i:03d}")
    
    def test_get_latest_news(self, adapter):
        """최신 뉴스 조회 테스트"""
        # 테스트 데이터 생성 (시간 순)
        test_news_list = []
        for i in range(5):
            test_news_list.append({
                "news_id": f"test_latest_{i:03d}",
                "ticker_symbol": "068270",
                "company_name": "셀트리온",
                "title": f"Celltrion news {i}",
                "content": f"Test content {i}",
                "published_date": (datetime.now() - timedelta(hours=i)).isoformat()
            })
        
        adapter.bulk_save_news(test_news_list)
        adapter.es_client.client.indices.refresh(
            index=adapter.es_client.index_name
        )
        
        # 최신 3개 조회
        latest = adapter.get_latest_news("068270", limit=3)
        assert len(latest) == 3
        
        # 최신순 정렬 확인
        for i in range(len(latest) - 1):
            date1 = datetime.fromisoformat(latest[i]['published_date'])
            date2 = datetime.fromisoformat(latest[i+1]['published_date'])
            assert date1 >= date2, "최신순으로 정렬되지 않음"
        
        print(f"✓ 최신 뉴스 {len(latest)}건 조회 성공 (최신순 정렬 확인)")
        
        # 정리
        for i in range(5):
            adapter.delete_news(f"test_latest_{i:03d}")
    
    def test_delete_news(self, adapter):
        """뉴스 삭제 테스트"""
        # 테스트 데이터 생성
        test_news = {
            "news_id": "test_delete_001",
            "ticker_symbol": "005930",
            "company_name": "삼성전자",
            "title": "Test for deletion",
            "content": "This will be deleted",
            "published_date": datetime.now().isoformat()
        }
        
        # 저장
        adapter.save_news(test_news)
        
        # 조회 확인
        news = adapter.get_news("test_delete_001")
        assert news is not None
        
        # 삭제
        result = adapter.delete_news("test_delete_001")
        assert result is True
        print("✓ 뉴스 삭제 성공")
        
        # 삭제 확인
        news = adapter.get_news("test_delete_001")
        assert news is None
        print("✓ 삭제된 뉴스 조회 시 None 반환 확인")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
