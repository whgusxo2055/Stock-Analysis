"""OpenAI API 디버그 테스트"""
import sys
import logging
sys.path.insert(0, '.')

# 로깅 레벨을 DEBUG로 설정
logging.basicConfig(level=logging.DEBUG)

from app import create_app
from app.services.news_analyzer import get_news_analyzer

print('\n=== OpenAI API 디버그 테스트 ===\n')

app = create_app()
with app.app_context():
    analyzer = get_news_analyzer()
    
    result = analyzer.analyze_news(
        title='Apple announces breakthrough in AI chip technology',
        content='Apple Inc. unveiled a revolutionary AI chip today, promising 10x performance improvements for machine learning tasks.',
        ticker='AAPL',
        company_name='Apple Inc.'
    )
    
    if result:
        print('\n✅ 분석 완료')
        print(f'한국어 요약: {result["summary"]["ko"][:100]}...')
        print(f'감성: {result["sentiment"]["classification"]} ({result["sentiment"]["score"]})')
