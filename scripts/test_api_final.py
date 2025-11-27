"""OpenAI API 최종 연동 테스트"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.services.news_analyzer import get_news_analyzer

print('\n=== OpenAI API 연동 최종 테스트 ===\n')

app = create_app()
with app.app_context():
    analyzer = get_news_analyzer()
    
    result = analyzer.analyze_news(
        title='Tesla breaks delivery records with strong Q4 performance',
        content='Tesla Inc. announced record-breaking vehicle deliveries in Q4, exceeding analyst expectations. The company delivered 500,000 vehicles globally, marking a significant milestone. Stock price surged 8% following the announcement.',
        ticker='TSLA',
        company_name='Tesla Inc.'
    )
    
    if result:
        print('✅ API 연동 성공!\n')
        print(f'🇰🇷 한국어: {result["summary"]["ko"]}')
        print(f'\n🇺🇸 English: {result["summary"]["en"]}')
        print(f'\n🇪🇸 Español: {result["summary"]["es"]}')
        print(f'\n🇯🇵 日本語: {result["summary"]["ja"]}')
        print(f'\n📊 감성 분석:')
        print(f'   분류: {result["sentiment"]["classification"]}')
        print(f'   점수: {result["sentiment"]["score"]}/10')
    else:
        print('❌ 분석 실패')
