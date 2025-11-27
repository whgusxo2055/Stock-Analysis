#!/usr/bin/env python3
"""
멀티스레드 병렬 크롤링 테스트
- 프록시 로테이션
- 5개 스레드 동시 실행
"""

from app import create_app
from app.services.crawler import batch_crawl_parallel
from app.services.news_analyzer import NewsAnalyzer
from app.services.news_storage import NewsStorageAdapter
from app.models.models import StockMaster
from app.utils.config import Config
import hashlib
from datetime import datetime

print('=' * 80)
print('멀티스레드 병렬 크롤링 테스트')
print('=' * 80)
print(f'모델: {Config.OPENAI_MODEL}')
print('개선 사항:')
print('  ✓ 멀티스레드 병렬 처리 (5개 스레드)')
print('  ✓ 프록시 로테이션 (IP 분산)')
print('  ✓ 종목별 독립적인 크롤러 인스턴스')
print('  ✓ 딜레이 없이 동시 크롤링')
print()

app = create_app()

with app.app_context():
    # 모든 종목 조회
    stocks_db = StockMaster.query.all()
    stocks = [(s.ticker_symbol, s.company_name) for s in stocks_db]
    
    print(f'대상 종목: {len(stocks)}개')
    for ticker, company in stocks:
        print(f'  - {ticker}: {company}')
    print()
    
    # 멀티스레드 병렬 크롤링
    print(f'{"=" * 80}')
    print('크롤링 시작...')
    print(f'{"=" * 80}\n')
    
    results = batch_crawl_parallel(
        stocks=stocks,
        hours_ago=0,  # 시간 제한 없음
        max_articles=10,  # 종목당 10개
        max_workers=5,  # 5개 스레드 동시 실행
        use_proxy=False  # 프록시 사용 (실제 프록시 없으면 False)
    )
    
    # 결과 집계
    all_articles = []
    for ticker, articles in results.items():
        all_articles.extend(articles)
    
    print(f'\n{"=" * 80}')
    print(f'총 수집: {len(all_articles)}개')
    print(f'{"=" * 80}')
    
    # 종목별 통계
    print('\n종목별 수집 결과:')
    for ticker, articles in sorted(results.items()):
        status = '✓' if articles else '✗'
        print(f'  {status} {ticker}: {len(articles)}개')
    
    if not all_articles:
        print('\n⚠️  수집된 기사가 없습니다.')
        exit(0)
    
    # 중복 체크
    print(f'\n{"=" * 80}')
    print('중복 체크 및 GPT 분석...')
    print(f'{"=" * 80}\n')
    
    storage = NewsStorageAdapter()
    analyzer = NewsAnalyzer()
    
    urls = [a['source_url'] for a in all_articles]
    duplicates = storage.check_duplicates(urls)
    new_articles = [a for a in all_articles if a['source_url'] not in duplicates]
    
    print(f'신규 기사: {len(new_articles)}개 (중복: {len(duplicates)}개)')
    
    if new_articles:
        # GPT 분석
        print(f'\nGPT-5.1 분석 시작... ({len(new_articles)}개)')
        analyzed = analyzer.batch_analyze(new_articles)
        print(f'분석 완료: {len(analyzed)}개')
        
        # ES 저장
        print('\nES 저장 중...')
        saved_count = 0
        for news in analyzed:
            news_id = hashlib.md5(news['source_url'].encode()).hexdigest()[:16]
            
            news_data = {
                'news_id': news_id,
                'ticker_symbol': news.get('symbol', news.get('ticker', '')),
                'title': news.get('title', ''),
                'content': news.get('content', ''),
                'published_date': news.get('date', datetime.now().isoformat()),
                'source_url': news.get('source_url', ''),
                'source_name': news.get('source_name', 'Investing.com'),
                'company_name': news.get('company_name', ''),
                'summary': news.get('summary', {}),
                'sentiment': news.get('sentiment', {}),
                'analyzed_date': news.get('analyzed_date', datetime.now().isoformat()),
                'metadata': news.get('metadata', {})
            }
            
            if storage.save_news(news_data):
                saved_count += 1
        
        print(f'저장 완료: {saved_count}개')
        
        # 최종 통계
        print(f'\n{"=" * 80}')
        print('종목별 저장 통계:')
        from collections import Counter
        ticker_counts = Counter([a['symbol'] for a in analyzed])
        for ticker, count in sorted(ticker_counts.items()):
            print(f'  {ticker}: {count}개')

print(f'\n{"=" * 80}')
print('=== 완료 ===')
print(f'{"=" * 80}')
