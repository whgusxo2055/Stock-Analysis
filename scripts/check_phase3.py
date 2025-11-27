"""
Phase 3 사전 점검 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.models.models import StockMaster

print("="*60)
print("Phase 3 사전 점검")
print("="*60)

app = create_app('development')

with app.app_context():
    # 1. Stock Master 데이터 확인
    print("\n[1] Stock Master 데이터 확인")
    stocks = StockMaster.query.all()
    print(f"   총 {len(stocks)}개 종목 등록됨")
    
    if stocks:
        print("   샘플 데이터:")
        for stock in stocks[:5]:
            print(f"   - {stock.ticker_symbol}: {stock.company_name}")
    else:
        print("   ⚠️  종목 데이터가 없습니다!")
        print("   💡 python scripts/init_db.py init 실행 필요")

# 2. Selenium 확인
print("\n[2] Selenium 설치 확인")
try:
    import selenium
    print(f"   ✓ Selenium 버전: {selenium.__version__}")
except ImportError:
    print("   ❌ Selenium이 설치되지 않음")
    print("   💡 pip install selenium 실행 필요")

# 3. ChromeDriver 확인
print("\n[3] ChromeDriver 확인")
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    print(f"   ✓ ChromeDriver 정상 작동")
    driver.quit()
except Exception as e:
    print(f"   ❌ ChromeDriver 오류: {e}")
    print("   💡 해결 방법:")
    print("      - macOS: brew install chromedriver")
    print("      - 또는 webdriver-manager 사용")

# 4. 환경 변수 확인
print("\n[4] 환경 변수 확인")
from app.utils.config import Config

es_url = Config.ELASTICSEARCH_URL
print(f"   ElasticSearch URL: {es_url}")

# 5. Phase 2 완료 상태 확인
print("\n[5] Phase 2 완료 상태 확인")
from app.utils.elasticsearch_client import get_es_client
from app.services.news_storage import get_news_storage

try:
    es_client = get_es_client()
    if es_client.is_connected():
        print("   ✓ ElasticSearch 연결 성공")
        
        # 인덱스 존재 확인
        if es_client.client.indices.exists(index=es_client.index_name):
            print(f"   ✓ 인덱스 '{es_client.index_name}' 존재")
        else:
            print(f"   ⚠️  인덱스 '{es_client.index_name}' 없음")
    else:
        print("   ❌ ElasticSearch 연결 실패")
except Exception as e:
    print(f"   ❌ ElasticSearch 오류: {e}")

try:
    storage = get_news_storage()
    print("   ✓ NewsStorageAdapter 초기화 성공")
except Exception as e:
    print(f"   ❌ NewsStorageAdapter 오류: {e}")

print("\n" + "="*60)
print("사전 점검 완료")
print("="*60)
