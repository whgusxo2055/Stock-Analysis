"""
ElasticSearch 인덱스 매핑 검증 테스트
Phase 2 - Task 1
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from app.utils.elasticsearch_client import get_es_client
from app.utils.config import Config


class TestElasticsearchIndexMapping:
    """ElasticSearch 인덱스 매핑 테스트"""
    
    @pytest.fixture
    def es_client(self):
        """ES 클라이언트 픽스처"""
        return get_es_client()
    
    def test_es_connection(self, es_client):
        """ElasticSearch 연결 테스트"""
        assert es_client.is_connected(), "ElasticSearch 연결 실패"
        print("✓ ElasticSearch 연결 성공")
    
    def test_index_creation(self, es_client):
        """인덱스 생성 테스트"""
        # 기존 인덱스 삭제 (테스트용)
        if es_client.client.indices.exists(index=Config.ELASTICSEARCH_INDEX):
            es_client.client.indices.delete(index=Config.ELASTICSEARCH_INDEX)
        
        # 인덱스 생성
        result = es_client.create_index()
        assert result, "인덱스 생성 실패"
        
        # 인덱스 존재 확인
        exists = es_client.client.indices.exists(index=Config.ELASTICSEARCH_INDEX)
        assert exists, f"인덱스 '{Config.ELASTICSEARCH_INDEX}'가 생성되지 않음"
        print(f"✓ 인덱스 '{Config.ELASTICSEARCH_INDEX}' 생성 성공")
    
    def test_index_settings(self, es_client):
        """인덱스 설정 검증 (SRS 7.2.1)"""
        index_name = Config.ELASTICSEARCH_INDEX
        
        # 설정 조회
        settings = es_client.client.indices.get_settings(index=index_name)
        index_settings = settings[index_name]['settings']['index']
        
        # Shards 확인
        assert 'number_of_shards' in index_settings
        print(f"✓ Shards: {index_settings['number_of_shards']}")
        
        # Replicas 확인
        assert 'number_of_replicas' in index_settings
        print(f"✓ Replicas: {index_settings['number_of_replicas']}")
        
        # Max result window 확인
        assert index_settings.get('max_result_window') == '10000'
        print(f"✓ Max result window: {index_settings['max_result_window']}")
    
    def test_index_mappings(self, es_client):
        """인덱스 매핑 검증 (SRS 7.2.1)"""
        index_name = Config.ELASTICSEARCH_INDEX
        
        # 매핑 조회
        mappings = es_client.client.indices.get_mapping(index=index_name)
        properties = mappings[index_name]['mappings']['properties']
        
        # 필수 필드 검증
        required_fields = [
            'news_id',
            'ticker_symbol',
            'company_name',
            'title',
            'content',
            'url',
            'published_date',
            'crawled_date',
            'summary',
            'sentiment'
        ]
        
        for field in required_fields:
            assert field in properties, f"필수 필드 '{field}' 누락"
            print(f"✓ 필드 '{field}' 존재")
        
        # news_id, ticker_symbol은 keyword 타입
        assert properties['news_id']['type'] == 'keyword'
        assert properties['ticker_symbol']['type'] == 'keyword'
        print("✓ ID 필드들이 keyword 타입으로 설정됨")
        
        # title, content는 text 타입 + standard analyzer
        assert properties['title']['type'] == 'text'
        assert properties['title']['analyzer'] == 'standard'
        assert properties['content']['type'] == 'text'
        assert properties['content']['analyzer'] == 'standard'
        print("✓ 텍스트 필드들이 standard analyzer로 설정됨")
        
        # published_date, crawled_date는 date 타입
        assert properties['published_date']['type'] == 'date'
        assert properties['crawled_date']['type'] == 'date'
        print("✓ 날짜 필드들이 date 타입으로 설정됨")
    
    def test_summary_mapping(self, es_client):
        """다국어 요약 매핑 검증"""
        index_name = Config.ELASTICSEARCH_INDEX
        
        mappings = es_client.client.indices.get_mapping(index=index_name)
        summary = mappings[index_name]['mappings']['properties']['summary']
        
        # summary는 object 타입 (properties 포함)
        assert 'properties' in summary
        summary_props = summary['properties']
        
        # 다국어 필드 검증 (ko, en, es, ja)
        languages = ['ko', 'en', 'es', 'ja']
        for lang in languages:
            assert lang in summary_props, f"언어 '{lang}' 필드 누락"
            assert summary_props[lang]['type'] == 'text'
            assert summary_props[lang]['analyzer'] == 'standard'
            print(f"✓ summary.{lang} 필드 설정 완료 (standard analyzer)")
    
    def test_sentiment_mapping(self, es_client):
        """감정 분석 매핑 검증"""
        index_name = Config.ELASTICSEARCH_INDEX
        
        mappings = es_client.client.indices.get_mapping(index=index_name)
        sentiment = mappings[index_name]['mappings']['properties']['sentiment']
        
        # sentiment는 object 타입
        assert 'properties' in sentiment
        sentiment_props = sentiment['properties']
        
        # classification은 keyword, score는 integer
        assert sentiment_props['classification']['type'] == 'keyword'
        assert sentiment_props['score']['type'] == 'integer'
        print("✓ sentiment.classification: keyword")
        print("✓ sentiment.score: integer")
    
    def test_sample_document_indexing(self, es_client):
        """샘플 문서 색인 테스트"""
        from datetime import datetime
        
        sample_doc = {
            "news_id": "test_news_001",
            "ticker_symbol": "005930",
            "company_name": "삼성전자",
            "title": "Samsung Electronics Q4 earnings surpass expectations",
            "content": "Samsung Electronics announced strong Q4 2024 results...",
            "url": "https://example.com/news/001",
            "published_date": "2024-01-15T10:00:00",
            "crawled_date": datetime.now().isoformat(),
            "summary": {
                "ko": "삼성전자 4분기 실적 발표",
                "en": "Samsung Q4 earnings announcement",
                "es": "Anuncio de ganancias de Samsung Q4",
                "ja": "サムスンQ4決算発表"
            },
            "sentiment": {
                "classification": "positive",
                "score": 85
            }
        }
        
        # 문서 색인
        result = es_client.index_news(sample_doc)
        assert result, "문서 색인 실패"
        
        # 잠시 대기 (refresh)
        es_client.client.indices.refresh(index=Config.ELASTICSEARCH_INDEX)
        
        # 문서 조회
        doc = es_client.client.get(
            index=Config.ELASTICSEARCH_INDEX,
            id="test_news_001"
        )
        
        assert doc['found'], "색인된 문서를 찾을 수 없음"
        assert doc['_source']['ticker_symbol'] == "005930"
        assert doc['_source']['sentiment']['score'] == 85
        print("✓ 샘플 문서 색인 및 조회 성공")
        
        # 테스트 문서 삭제
        es_client.client.delete(
            index=Config.ELASTICSEARCH_INDEX,
            id="test_news_001"
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
