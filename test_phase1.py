"""
Phase 1 검증 스크립트
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def test_imports():
    """필수 모듈 import 테스트"""
    print("🧪 Testing imports...")
    try:
        from app import create_app, db
        from app.models.models import User, UserSetting, StockMaster, UserStock
        from app.utils.config import Config
        from app.utils.logger import setup_logging
        print("✓ All imports successful!")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_app_creation():
    """Flask 앱 생성 테스트"""
    print("\n🧪 Testing Flask app creation...")
    try:
        from app import create_app
        app = create_app('testing')
        
        with app.app_context():
            print(f"✓ App created successfully")
            print(f"  - App name: {app.name}")
            print(f"  - Debug: {app.debug}")
            print(f"  - Testing: {app.testing}")
        return True
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_models():
    """데이터베이스 모델 테스트"""
    print("\n🧪 Testing database models...")
    try:
        from app import create_app, db
        from app.models.models import User, StockMaster
        
        app = create_app('testing')
        
        with app.app_context():
            # 테이블 생성
            db.create_all()
            print("✓ Database tables created")
            
            # 사용자 생성 테스트
            test_user = User(
                username='testuser',
                email='test@example.com',
                is_admin=False
            )
            test_user.set_password('test123')
            db.session.add(test_user)
            db.session.commit()
            print("✓ Test user created")
            
            # 사용자 조회 테스트
            user = User.query.filter_by(username='testuser').first()
            assert user is not None
            assert user.check_password('test123')
            print("✓ User query and password check successful")
            
            # 종목 생성 테스트
            test_stock = StockMaster(
                ticker_symbol='TEST',
                company_name='Test Company',
                exchange='NASDAQ'
            )
            db.session.add(test_stock)
            db.session.commit()
            print("✓ Test stock created")
            
            # 정리
            db.session.delete(user)
            db.session.delete(test_stock)
            db.session.commit()
            print("✓ Test data cleaned up")
            
        return True
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config():
    """설정 로딩 테스트"""
    print("\n🧪 Testing configuration...")
    try:
        from app.utils.config import Config, get_config
        
        config = get_config('development')
        print(f"✓ Config loaded")
        print(f"  - Flask ENV: {config.FLASK_ENV}")
        print(f"  - Database URL: {config.DATABASE_URL}")
        print(f"  - ES URL: {config.ELASTICSEARCH_URL}")
        print(f"  - Crawler Type: {config.CRAWLER_TYPE}")
        
        return True
    except Exception as e:
        print(f"✗ Config test failed: {e}")
        return False


def test_logging():
    """로깅 시스템 테스트"""
    print("\n🧪 Testing logging system...")
    try:
        from app.utils.logger import setup_logging, get_logger
        
        # 로깅 설정
        setup_logging(log_dir='logs', log_level='INFO')
        
        # 로거 테스트
        logger = get_logger('test')
        logger.info("Test info message")
        logger.warning("Test warning message")
        
        print("✓ Logging system working")
        return True
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        return False


def test_api_endpoints():
    """API 엔드포인트 테스트"""
    print("\n🧪 Testing API endpoints...")
    try:
        from app import create_app
        
        app = create_app('testing')
        client = app.test_client()
        
        # 루트 엔드포인트 테스트
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        print("✓ Root endpoint (/) working")
        
        # 헬스 체크 엔드포인트 테스트
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        print("✓ Health endpoint (/health) working")
        
        return True
    except Exception as e:
        print(f"✗ API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("="*60)
    print("Phase 1 Validation Tests")
    print("="*60)
    
    tests = [
        test_imports,
        test_config,
        test_logging,
        test_app_creation,
        test_database_models,
        test_api_endpoints
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! Phase 1 is complete.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
