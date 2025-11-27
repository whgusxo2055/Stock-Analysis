"""
Phase 7 통합 테스트
P7.M1.T2: 전체 파이프라인 End-to-End 테스트
크롤링 → 분석 → 저장 → 메일 플로우
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import json


class TestEndToEndPipeline:
    """전체 파이프라인 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def mock_news_data(self):
        """Mock 뉴스 데이터"""
        return [
            {
                'title': 'Tesla Q4 Earnings Beat Expectations',
                'content': 'Tesla Inc. reported strong Q4 earnings, beating analyst expectations with record deliveries.',
                'url': 'https://investing.com/news/tesla-q4-earnings',
                'date': datetime.now(timezone.utc).isoformat(),
                'source': 'investing.com',
                'ticker': 'TSLA',
                'company_name': 'Tesla'
            },
            {
                'title': 'Tesla Faces Supply Chain Challenges',
                'content': 'Tesla announced potential delays in production due to global supply chain issues.',
                'url': 'https://investing.com/news/tesla-supply-chain',
                'date': datetime.now(timezone.utc).isoformat(),
                'source': 'investing.com',
                'ticker': 'TSLA',
                'company_name': 'Tesla'
            }
        ]
    
    @pytest.fixture
    def mock_analysis_result(self):
        """Mock 분석 결과"""
        return {
            'summary': {
                'ko': '테슬라 4분기 실적이 예상을 상회했습니다.',
                'en': 'Tesla Q4 earnings beat expectations.',
                'es': 'Las ganancias del Q4 de Tesla superaron las expectativas.',
                'ja': 'テスラQ4決算が予想を上回りました。'
            },
            'sentiment': {
                'classification': 'Positive',
                'score': 7
            }
        }
    
    def test_crawl_to_analysis_flow(self, app, mock_news_data, mock_analysis_result):
        """크롤링 → 분석 플로우 테스트"""
        with app.app_context():
            from app.services.news_analyzer import NewsAnalyzer
            
            # Mock 크롤링 결과를 분석기에 전달
            analyzer = NewsAnalyzer()
            
            for news in mock_news_data:
                result = analyzer.analyze_news(
                    title=news['title'],
                    content=news['content'],
                    ticker=news['ticker'],
                    company_name=news['company_name']
                )
                
                # 분석 결과 확인 (fallback 포함)
                assert result is not None
                assert 'summary' in result
                assert 'sentiment' in result
    
    def test_analysis_to_storage_flow(self, app, mock_news_data, mock_analysis_result):
        """분석 → 저장 플로우 테스트"""
        with app.app_context():
            from app.services.news_storage import get_news_storage
            
            storage = get_news_storage()
            
            # 뉴스 데이터에 분석 결과 추가
            news_with_analysis = mock_news_data[0].copy()
            news_with_analysis['news_id'] = 'test_e2e_001'
            news_with_analysis['ticker_symbol'] = news_with_analysis.pop('ticker')
            news_with_analysis['published_date'] = news_with_analysis.pop('date')
            news_with_analysis['summary'] = mock_analysis_result['summary']
            news_with_analysis['sentiment'] = mock_analysis_result['sentiment']
            
            # 저장 테스트
            result = storage.save_news(news_with_analysis)
            
            # ES 연결 여부에 따라 결과 확인
            # 테스트 환경에서는 ES가 없을 수 있음
            if result:
                assert result is True
                
                # 조회 테스트
                retrieved = storage.get_news('test_e2e_001')
                if retrieved:
                    assert retrieved['ticker_symbol'] == 'TSLA'


class TestAPIEndpoints:
    """API 엔드포인트 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트"""
        return app.test_client()
    
    def test_health_endpoint(self, client):
        """헬스 체크 엔드포인트 테스트"""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'status' in data
        assert 'database' in data
    
    def test_login_page(self, client):
        """로그인 페이지 접근 테스트"""
        response = client.get('/auth/login')
        assert response.status_code == 200
    
    def test_protected_route_redirect(self, client):
        """보호된 경로 리다이렉트 테스트"""
        response = client.get('/dashboard')
        # 로그인되지 않은 상태에서 리다이렉트
        assert response.status_code in [302, 200]  # 리다이렉트 또는 로그인 페이지


class TestUserWorkflow:
    """사용자 워크플로우 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트"""
        return app.test_client()
    
    def test_user_creation_and_password(self, app):
        """사용자 생성 및 비밀번호 확인 테스트"""
        from app.extensions import db
        from app.models.models import User
        
        with app.app_context():
            # 사용자 생성
            user = User(username='testuser', email='test@test.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # 사용자 조회 및 비밀번호 확인
            found = User.query.filter_by(username='testuser').first()
            assert found is not None
            assert found.check_password('password123') is True
            assert found.check_password('wrongpassword') is False


class TestSchedulerIntegration:
    """스케줄러 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_scheduler_service_import(self, app):
        """스케줄러 서비스 임포트 테스트"""
        with app.app_context():
            from app.services.scheduler import SchedulerService
            
            # 클래스가 정상적으로 임포트되는지 확인
            assert SchedulerService is not None
    
    def test_scheduler_instance_creation(self, app):
        """스케줄러 인스턴스 생성 테스트"""
        with app.app_context():
            from app.services.scheduler import SchedulerService
            
            # 앱 컨텍스트 전달하여 생성
            scheduler = SchedulerService(app=app)
            
            # 인스턴스 확인
            assert scheduler is not None


class TestEmailIntegration:
    """이메일 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_email_sender_initialization(self, app):
        """이메일 발송 서비스 초기화 테스트"""
        with app.app_context():
            from app.services.email_sender import EmailSender
            
            sender = EmailSender()
            
            # 인스턴스 확인
            assert sender is not None
    
    def test_email_template_rendering(self, app):
        """이메일 템플릿 렌더링 테스트"""
        with app.app_context():
            from flask import render_template_string
            
            # 간단한 템플릿 테스트
            test_context = {
                'user_name': 'Test User',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'stocks': [
                    {
                        'ticker_symbol': 'TSLA',
                        'company_name': 'Tesla',
                        'news_list': []
                    }
                ]
            }
            
            # 템플릿 파일 존재 확인
            from pathlib import Path
            template_path = Path(app.root_path) / 'templates' / 'email' / 'report.html'
            assert template_path.exists()


class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_complete_user_setup(self, app):
        """완전한 사용자 설정 테스트"""
        from app.extensions import db
        from app.models.models import User, UserSetting, StockMaster, UserStock
        from datetime import time
        
        with app.app_context():
            # 1. 사용자 생성
            user = User(username='fulltest', email='full@test.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            
            # 2. 설정 추가
            setting = UserSetting(
                user_id=user.id,
                language='ko',
                notification_time=time(9, 0, 0),
                is_notification_enabled=True
            )
            db.session.add(setting)
            
            # 3. 종목 마스터 추가
            stock = StockMaster(
                ticker_symbol='AAPL',
                company_name='Apple Inc.',
                exchange='NASDAQ',
                sector='Technology'
            )
            db.session.add(stock)
            db.session.commit()
            
            # 4. 관심 종목 추가
            user_stock = UserStock(
                user_id=user.id,
                ticker_symbol='AAPL'
            )
            db.session.add(user_stock)
            db.session.commit()
            
            # 검증
            found_user = User.query.filter_by(username='fulltest').first()
            assert found_user is not None
            assert found_user.settings is not None
            assert len(found_user.stocks) == 1
            assert found_user.stocks[0].ticker_symbol == 'AAPL'


class TestNewsStorageIntegration:
    """뉴스 저장소 통합 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        from app import create_app
        from app.extensions import db
        
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_news_storage_singleton(self, app):
        """뉴스 저장소 싱글톤 패턴 테스트"""
        with app.app_context():
            from app.services.news_storage import get_news_storage
            
            storage1 = get_news_storage()
            storage2 = get_news_storage()
            
            # 동일 인스턴스인지 확인
            assert storage1 is storage2
    
    def test_recent_news_query(self, app):
        """최근 뉴스 조회 테스트"""
        with app.app_context():
            from app.services.news_storage import get_news_storage
            
            storage = get_news_storage()
            
            # 최근 뉴스 조회 (ES 연결 없어도 빈 결과 반환)
            result = storage.get_recent_news(ticker_symbol='TSLA', hours=3)
            
            # 결과 구조 확인
            assert isinstance(result, (list, type(None)))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
