"""
Phase 4 뉴스 분석 엔진 테스트
- ChatGPT API 연동 확인
- 다국어 요약 및 감성 분석 검증
"""

import sys
import logging
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.news_analyzer import NewsAnalyzer
from app.utils.config import Config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)


def test_analyzer():
    """뉴스 분석 엔진 테스트"""
    print("=" * 60)
    print("Phase 4 뉴스 분석 엔진 테스트")
    print("=" * 60)
    
    # API 키 확인
    if not Config.OPENAI_API_KEY:
        print("\n❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 추가해주세요.")
        return False
    
    print(f"\n✓ OpenAI API 키 설정 확인")
    print(f"  모델: {Config.OPENAI_MODEL}")
    
    # NewsAnalyzer 초기화
    analyzer = NewsAnalyzer()
    
    if not analyzer.client:
        print("\n❌ OpenAI 클라이언트 초기화 실패")
        return False
    
    print("✓ NewsAnalyzer 초기화 성공")
    
    # 테스트 뉴스 데이터
    test_news = {
        'title': 'Tesla Announces Record Q4 Deliveries, Stock Surges 5%',
        'content': '''Tesla Inc. reported record-breaking vehicle deliveries 
        for Q4 2024, exceeding analyst expectations by 12%. The electric 
        vehicle maker delivered 500,000 vehicles globally, driven by strong 
        demand in China and Europe. CEO Elon Musk stated that the company 
        is on track to meet its annual production targets. Following the 
        announcement, Tesla stock surged 5% in after-hours trading.''',
        'ticker': 'TSLA',
        'company_name': 'Tesla Inc.'
    }
    
    print("\n[1] 단일 뉴스 분석 테스트...")
    print(f"   제목: {test_news['title']}")
    
    try:
        result = analyzer.analyze_news(
            title=test_news['title'],
            content=test_news['content'],
            ticker=test_news['ticker'],
            company_name=test_news['company_name']
        )
        
        if not result:
            print("   ❌ 분석 실패")
            return False
        
        print("\n✓ 분석 성공!")
        
        # 요약 확인
        print("\n[2] 다국어 요약 확인:")
        for lang, text in result['summary'].items():
            print(f"   {lang}: {text[:80]}...")
        
        # 감성 분석 확인
        print("\n[3] 감성 분석 결과:")
        sentiment = result['sentiment']
        print(f"   분류: {sentiment['classification']}")
        print(f"   점수: {sentiment['score']} (-10 ~ +10)")
        
        # 검증
        print("\n[4] 결과 검증:")
        
        # 필수 언어 확인
        required_langs = ['ko', 'en', 'es', 'ja']
        missing_langs = [
            lang for lang in required_langs 
            if not result['summary'].get(lang)
        ]
        
        if missing_langs:
            print(f"   ❌ 누락된 언어: {missing_langs}")
            return False
        
        print("   ✓ 모든 언어 요약 존재")
        
        # 분류 확인
        valid_classifications = ['Positive', 'Negative', 'Neutral']
        if sentiment['classification'] not in valid_classifications:
            print(f"   ❌ 잘못된 분류: {sentiment['classification']}")
            return False
        
        print(f"   ✓ 분류 검증 통과: {sentiment['classification']}")
        
        # 점수 범위 확인
        if not -10 <= sentiment['score'] <= 10:
            print(f"   ❌ 점수 범위 초과: {sentiment['score']}")
            return False
        
        print(f"   ✓ 점수 범위 검증 통과: {sentiment['score']}")
        
        # 배치 분석 테스트
        print("\n[5] 배치 분석 테스트...")
        
        batch_items = [
            {
                'title': 'Apple Reports Strong iPhone 15 Sales',
                'content': 'Apple Inc. announced strong sales of iPhone 15...',
                'ticker': 'AAPL',
                'company_name': 'Apple Inc.'
            },
            {
                'title': 'Microsoft Cloud Revenue Grows 30%',
                'content': 'Microsoft Azure cloud services saw 30% growth...',
                'ticker': 'MSFT',
                'company_name': 'Microsoft Corporation'
            }
        ]
        
        batch_results = analyzer.batch_analyze(batch_items)
        
        print(f"   분석 완료: {len(batch_results)}/{len(batch_items)}건")
        
        if len(batch_results) == len(batch_items):
            print("   ✓ 배치 분석 성공")
        else:
            print("   ⚠️  일부 항목 분석 실패")
        
        print("\n" + "=" * 60)
        print("✅ Phase 4 뉴스 분석 엔진 테스트 통과")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}", exc_info=True)
        print(f"\n❌ 테스트 실패: {e}")
        return False


if __name__ == '__main__':
    try:
        success = test_analyzer()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        logger.error(f"치명적 오류: {e}", exc_info=True)
        sys.exit(1)
