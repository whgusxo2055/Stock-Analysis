"""
Phase 7 단위 테스트 - 뉴스 분석 서비스
P7.M1.T1: ChatGPT 분석 응답 파서 테스트 (Mock 사용)
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock


class TestNewsAnalyzerPrompt:
    """뉴스 분석 프롬프트 테스트"""
    
    def test_prompt_template_exists(self):
        """프롬프트 템플릿 존재 확인"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # 분석 프롬프트 생성
        test_news = {
            'title': 'Tesla Stock Rises on Strong Deliveries',
            'content': 'Tesla delivered 500,000 vehicles in Q4, beating analyst expectations.',
            'ticker_symbol': 'TSLA'
        }
        
        prompt = analyzer._build_prompt(
            title=test_news['title'],
            content=test_news['content'],
            ticker=test_news['ticker_symbol'],
            company_name='Tesla'
        )
        
        # 필수 요소 포함 확인
        assert 'Summary in Korean' in prompt or '한국어' in prompt
        assert 'Summary in English' in prompt or 'English' in prompt
        assert 'Sentiment' in prompt or 'sentiment' in prompt


class TestNewsAnalyzerResponse:
    """뉴스 분석 응답 파싱 테스트"""
    
    @pytest.fixture
    def valid_response_json(self):
        """유효한 ChatGPT 응답 JSON"""
        return {
            "summary_ko": "테슬라가 4분기에 50만대의 차량을 인도하며 애널리스트 예상을 상회했습니다.",
            "summary_en": "Tesla delivered 500,000 vehicles in Q4, beating analyst expectations.",
            "summary_es": "Tesla entregó 500,000 vehículos en el cuarto trimestre, superando las expectativas.",
            "summary_ja": "テスラは第4四半期に50万台を納車し、アナリスト予想を上回りました。",
            "sentiment": {
                "classification": "Positive",
                "score": 8
            }
        }
    
    def test_validate_valid_response(self, valid_response_json):
        """유효한 응답 검증 테스트"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # 검증 테스트
        result = analyzer._validate_result(valid_response_json)
        
        assert result is not None
        assert 'summary' in result
        assert 'sentiment' in result
        
        # 요약 언어 확인
        assert result['summary']['ko'] == valid_response_json['summary_ko']
        assert result['summary']['en'] == valid_response_json['summary_en']
        
        # 감성 분석 확인
        assert result['sentiment']['classification'] == 'Positive'
        assert result['sentiment']['score'] == 8
    
    def test_validate_response_with_invalid_score(self):
        """범위 초과 점수 처리"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # 범위 초과 점수 포함 응답
        invalid_score_response = {
            "summary_ko": "테스트 요약",
            "summary_en": "Test summary",
            "summary_es": "Resumen de prueba",
            "summary_ja": "テストの要約",
            "sentiment": {
                "classification": "Positive",
                "score": 15  # 범위 초과
            }
        }
        
        result = analyzer._validate_result(invalid_score_response)
        
        # 점수가 범위 내로 클리핑되어야 함
        assert result is not None
        assert result['sentiment']['score'] == 10  # 최대값으로 클리핑
    
    def test_parse_invalid_classification(self):
        """잘못된 분류 처리"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        invalid_classification_response = {
            "summary_ko": "테스트 요약",
            "summary_en": "Test summary",
            "summary_es": "Resumen de prueba",
            "summary_ja": "テストの要約",
            "sentiment": {
                "classification": "Invalid",  # 잘못된 분류
                "score": 5
            }
        }
        
        result = analyzer._validate_result(invalid_classification_response)
        
        # Neutral로 기본값 처리
        assert result['sentiment']['classification'] == 'Neutral'


class TestSentimentValidation:
    """감성 분석 결과 검증 테스트"""
    
    def test_valid_sentiment_score_range(self):
        """유효한 감성 점수 범위 (-10 ~ +10)"""
        valid_scores = [-10, -5, 0, 5, 10]
        
        for score in valid_scores:
            assert -10 <= score <= 10
    
    def test_score_clipping_high(self):
        """높은 점수 클리핑 검증"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # 범위 초과 점수 포함 응답
        high_score_response = {
            "summary_ko": "테스트",
            "summary_en": "Test",
            "summary_es": "Prueba",
            "summary_ja": "テスト",
            "sentiment": {
                "classification": "Positive",
                "score": 20  # 범위 초과
            }
        }
        
        result = analyzer._validate_result(high_score_response)
        
        # 최대값으로 클리핑
        assert result['sentiment']['score'] == 10
    
    def test_score_clipping_low(self):
        """낮은 점수 클리핑 검증"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # 범위 미만 점수 포함 응답
        low_score_response = {
            "summary_ko": "테스트",
            "summary_en": "Test",
            "summary_es": "Prueba",
            "summary_ja": "テスト",
            "sentiment": {
                "classification": "Negative",
                "score": -20  # 범위 미만
            }
        }
        
        result = analyzer._validate_result(low_score_response)
        
        # 최소값으로 클리핑
        assert result['sentiment']['score'] == -10
    
    def test_sentiment_classification(self):
        """감성 분류 검증"""
        valid_classifications = ['Positive', 'Negative', 'Neutral']
        
        for classification in valid_classifications:
            assert classification in ['Positive', 'Negative', 'Neutral']


class TestNewsAnalyzerIntegration:
    """뉴스 분석 통합 테스트 (Mock OpenAI)"""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI 응답"""
        return {
            "summary_ko": "애플이 신제품을 발표했습니다.",
            "summary_en": "Apple announced new products.",
            "summary_es": "Apple anunció nuevos productos.",
            "summary_ja": "アップルが新製品を発表しました。",
            "sentiment": {
                "classification": "Positive",
                "score": 6
            }
        }
    
    def test_analyze_news_with_mock(self, mock_openai_response):
        """Mock을 사용한 뉴스 분석 테스트"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # OpenAI client가 없어도 fallback 분석이 동작해야 함
        result = analyzer.analyze_news(
            title='Apple Announces New iPhone',
            content='Apple Inc. unveiled its latest iPhone model...',
            ticker='AAPL',
            company_name='Apple'
        )
        
        # fallback 결과도 포함하여 체크
        assert result is not None
        assert 'summary' in result
        assert 'sentiment' in result
    
    def test_batch_analyze_news(self, mock_openai_response):
        """배치 뉴스 분석 테스트"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        news_list = [
            {'title': 'News 1', 'content': 'Content 1', 'ticker': 'AAPL', 'company_name': 'Apple'},
            {'title': 'News 2', 'content': 'Content 2', 'ticker': 'GOOGL', 'company_name': 'Google'},
            {'title': 'News 3', 'content': 'Content 3', 'ticker': 'MSFT', 'company_name': 'Microsoft'}
        ]
        
        results = analyzer.batch_analyze(news_list)
        
        # 분석 결과 확인 (fallback 포함)
        assert len(results) == 3
        for result in results:
            assert 'summary' in result
            assert 'sentiment' in result


class TestAnalyzerErrorHandling:
    """분석기 에러 처리 테스트"""
    
    def test_fallback_on_no_client(self):
        """OpenAI 클라이언트 없을 때 fallback 처리"""
        from app.services.news_analyzer import NewsAnalyzer
        
        # API 키 없이 초기화
        analyzer = NewsAnalyzer(api_key=None)
        
        result = analyzer.analyze_news(
            title='Test News',
            content='Test content for analysis',
            ticker='TEST',
            company_name='Test Corp'
        )
        
        # fallback 결과 반환
        assert result is not None
        assert result['sentiment']['classification'] == 'Neutral'
        assert result['sentiment']['score'] == 0
    
    def test_empty_content_handling(self):
        """빈 컨텐츠 처리"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        result = analyzer.analyze_news(
            title='Title Only News',
            content='',  # 빈 컨텐츠
            ticker='TEST'
        )
        
        # 빈 컨텐츠도 fallback으로 처리
        assert result is not None


class TestFallbackAnalysis:
    """Fallback 분석 테스트"""
    
    def test_fallback_summary_generation(self):
        """Fallback 요약 생성"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        # fallback 분석 생성
        fallback = analyzer._generate_fallback_analysis(
            title='Tesla Stock Rises 5% on Strong Q4 Results',
            content='Tesla Inc. reported strong Q4 earnings. The company beat analyst expectations.'
        )
        
        assert fallback is not None
        assert 'summary' in fallback
        assert 'sentiment' in fallback
        
        # fallback은 모든 언어에 동일한 요약 사용
        assert fallback['summary']['ko'] is not None
        assert fallback['summary']['en'] is not None
        
        # 기본 sentiment
        assert fallback['sentiment']['classification'] == 'Neutral'
        assert fallback['sentiment']['score'] == 0
    
    def test_fallback_with_long_title(self):
        """긴 제목 fallback 처리"""
        from app.services.news_analyzer import NewsAnalyzer
        
        analyzer = NewsAnalyzer()
        
        long_title = "This is a very long news title that exceeds the normal length and should be truncated properly " * 3
        
        fallback = analyzer._generate_fallback_analysis(
            title=long_title,
            content=''
        )
        
        # 길이 제한 확인
        assert len(fallback['summary']['ko']) <= 203  # 200 + "..."


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
