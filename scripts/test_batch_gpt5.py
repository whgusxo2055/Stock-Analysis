"""GPT-5.1 배치 분석 테스트"""
import sys
sys.path.insert(0, '.')

from app import create_app
from app.services.news_analyzer import get_news_analyzer

print('\n=== GPT-5.1 배치 분석 테스트 ===\n')

app = create_app()
with app.app_context():
    analyzer = get_news_analyzer()
    
    news_items = [
        {
            'title': 'Apple announces breakthrough AI chip',
            'content': 'Apple unveiled revolutionary AI chip with 10x performance boost',
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.'
        },
        {
            'title': 'Microsoft Azure revenue drops 15%',
            'content': 'Microsoft reported disappointing Azure results, missing analyst targets',
            'ticker': 'MSFT',
            'company_name': 'Microsoft Corporation'
        },
        {
            'title': 'Amazon maintains steady growth',
            'content': 'Amazon Q4 results meet expectations with stable revenue growth',
            'ticker': 'AMZN',
            'company_name': 'Amazon.com Inc.'
        }
    ]
    
    print('뉴스 분석 시작...\n')
    results = analyzer.batch_analyze(news_items)
    
    print(f'✅ {len(results)}/{len(news_items)}건 분석 완료\n')
    print('=' * 70)
    
    for i, result in enumerate(results, 1):
        print(f'\n[{i}] {result["title"]}')
        print(f'📊 감성: {result["sentiment"]["classification"]} ({result["sentiment"]["score"]}/10)')
        print(f'🇰🇷 {result["summary"]["ko"]}')
        print('-' * 70)
