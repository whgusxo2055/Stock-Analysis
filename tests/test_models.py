"""
Phase 7 단위 테스트 - 데이터베이스 모델
P7.M1.T1: 모델 CRUD 테스트
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, time
from app import create_app
from app.extensions import db
from app.models.models import User, UserSetting, StockMaster, UserStock, EmailLog, CrawlLog


class TestUserModel:
    """User 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app):
        """테스트 클라이언트"""
        return app.test_client()
    
    def test_create_user(self, app):
        """사용자 생성 테스트"""
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()
            
            # 조회
            found = User.query.filter_by(username='testuser').first()
            assert found is not None
            assert found.email == 'test@example.com'
            assert found.is_active is True
            assert found.is_admin is False
    
    def test_password_hashing(self, app):
        """비밀번호 해싱 테스트"""
        with app.app_context():
            user = User(username='hashtest', email='hash@test.com')
            user.set_password('mypassword')
            
            # 해시 저장 확인
            assert user.password_hash != 'mypassword'
            assert user.check_password('mypassword') is True
            assert user.check_password('wrongpassword') is False
    
    def test_user_to_dict(self, app):
        """User to_dict 메서드 테스트"""
        with app.app_context():
            user = User(
                username='dictuser',
                email='dict@test.com'
            )
            user.set_password('test')
            db.session.add(user)
            db.session.commit()
            
            user_dict = user.to_dict()
            assert 'id' in user_dict
            assert user_dict['username'] == 'dictuser'
            assert user_dict['email'] == 'dict@test.com'
            assert 'password_hash' not in user_dict  # 비밀번호는 제외
    
    def test_unique_username(self, app):
        """username 유니크 제약 테스트"""
        with app.app_context():
            user1 = User(username='unique', email='user1@test.com')
            user1.set_password('pass')
            db.session.add(user1)
            db.session.commit()
            
            user2 = User(username='unique', email='user2@test.com')
            user2.set_password('pass')
            db.session.add(user2)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()


class TestUserSettingModel:
    """UserSetting 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_create_user_setting(self, app):
        """사용자 설정 생성 테스트"""
        with app.app_context():
            # 사용자 먼저 생성
            user = User(username='settingtest', email='setting@test.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            
            # 설정 생성
            setting = UserSetting(
                user_id=user.id,
                language='ko',
                notification_time=time(9, 0, 0),
                is_notification_enabled=True
            )
            db.session.add(setting)
            db.session.commit()
            
            # 조회
            found = UserSetting.query.filter_by(user_id=user.id).first()
            assert found is not None
            assert found.language == 'ko'
            assert found.notification_time == time(9, 0, 0)
            assert found.is_notification_enabled is True
    
    def test_user_setting_relationship(self, app):
        """User-UserSetting 관계 테스트"""
        with app.app_context():
            user = User(username='reltest', email='rel@test.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            
            setting = UserSetting(
                user_id=user.id,
                language='en',
                notification_time=time(18, 0, 0)
            )
            db.session.add(setting)
            db.session.commit()
            
            # 관계를 통한 접근
            assert user.settings is not None
            assert user.settings.language == 'en'
            assert setting.user.username == 'reltest'


class TestStockMasterModel:
    """StockMaster 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_create_stock_master(self, app):
        """종목 마스터 생성 테스트"""
        with app.app_context():
            stock = StockMaster(
                ticker_symbol='TSLA',
                company_name='Tesla, Inc.',
                exchange='NASDAQ',
                sector='Automotive'
            )
            db.session.add(stock)
            db.session.commit()
            
            found = StockMaster.query.get('TSLA')
            assert found is not None
            assert found.company_name == 'Tesla, Inc.'
            assert found.exchange == 'NASDAQ'
    
    def test_stock_master_to_dict(self, app):
        """StockMaster to_dict 메서드 테스트"""
        with app.app_context():
            stock = StockMaster(
                ticker_symbol='AAPL',
                company_name='Apple Inc.',
                exchange='NASDAQ',
                sector='Technology'
            )
            db.session.add(stock)
            db.session.commit()
            
            stock_dict = stock.to_dict()
            assert stock_dict['ticker_symbol'] == 'AAPL'
            assert stock_dict['company_name'] == 'Apple Inc.'


class TestUserStockModel:
    """UserStock 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_add_user_stock(self, app):
        """관심 종목 추가 테스트"""
        with app.app_context():
            # 사용자 생성
            user = User(username='stockuser', email='stock@test.com')
            user.set_password('pass')
            db.session.add(user)
            
            # 종목 마스터 생성
            stock = StockMaster(ticker_symbol='NVDA', company_name='NVIDIA Corporation')
            db.session.add(stock)
            db.session.commit()
            
            # 관심 종목 추가
            user_stock = UserStock(user_id=user.id, ticker_symbol='NVDA')
            db.session.add(user_stock)
            db.session.commit()
            
            # 조회
            found = UserStock.query.filter_by(user_id=user.id, ticker_symbol='NVDA').first()
            assert found is not None
            assert found.stock.company_name == 'NVIDIA Corporation'
    
    def test_unique_user_stock(self, app):
        """중복 관심 종목 방지 테스트"""
        with app.app_context():
            user = User(username='dupuser', email='dup@test.com')
            user.set_password('pass')
            db.session.add(user)
            
            stock = StockMaster(ticker_symbol='MSFT', company_name='Microsoft Corporation')
            db.session.add(stock)
            db.session.commit()
            
            # 첫 번째 추가
            us1 = UserStock(user_id=user.id, ticker_symbol='MSFT')
            db.session.add(us1)
            db.session.commit()
            
            # 중복 추가 시도
            us2 = UserStock(user_id=user.id, ticker_symbol='MSFT')
            db.session.add(us2)
            
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()
    
    def test_cascade_delete(self, app):
        """CASCADE 삭제 테스트 - 사용자 삭제 시 관심 종목도 삭제"""
        with app.app_context():
            user = User(username='cascadeuser', email='cascade@test.com')
            user.set_password('pass')
            db.session.add(user)
            
            stock = StockMaster(ticker_symbol='AMZN', company_name='Amazon.com, Inc.')
            db.session.add(stock)
            db.session.commit()
            
            us = UserStock(user_id=user.id, ticker_symbol='AMZN')
            db.session.add(us)
            db.session.commit()
            
            user_id = user.id
            
            # 사용자 삭제
            db.session.delete(user)
            db.session.commit()
            
            # 관심 종목도 삭제되었는지 확인
            assert UserStock.query.filter_by(user_id=user_id).first() is None


class TestEmailLogModel:
    """EmailLog 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_create_email_log(self, app):
        """이메일 로그 생성 테스트"""
        with app.app_context():
            user = User(username='emailloguser', email='emaillog@test.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            
            log = EmailLog(
                user_id=user.id,
                status='success',
                news_count=5
            )
            db.session.add(log)
            db.session.commit()
            
            found = EmailLog.query.filter_by(user_id=user.id).first()
            assert found is not None
            assert found.status == 'success'
            assert found.news_count == 5
    
    def test_email_log_failed(self, app):
        """실패 이메일 로그 테스트"""
        with app.app_context():
            user = User(username='failloguser', email='faillog@test.com')
            user.set_password('pass')
            db.session.add(user)
            db.session.commit()
            
            log = EmailLog(
                user_id=user.id,
                status='failed',
                error_message='SMTP connection timeout',
                news_count=0
            )
            db.session.add(log)
            db.session.commit()
            
            found = EmailLog.query.filter_by(user_id=user.id, status='failed').first()
            assert found is not None
            assert 'SMTP' in found.error_message


class TestCrawlLogModel:
    """CrawlLog 모델 테스트"""
    
    @pytest.fixture
    def app(self):
        """테스트용 Flask 앱"""
        app = create_app('testing')
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_create_crawl_log(self, app):
        """크롤링 로그 생성 테스트"""
        with app.app_context():
            log = CrawlLog(
                ticker_symbol='GOOGL',
                status='success',
                news_count=10
            )
            db.session.add(log)
            db.session.commit()
            
            found = CrawlLog.query.filter_by(ticker_symbol='GOOGL').first()
            assert found is not None
            assert found.status == 'success'
            assert found.news_count == 10
    
    def test_crawl_log_to_dict(self, app):
        """CrawlLog to_dict 메서드 테스트"""
        with app.app_context():
            log = CrawlLog(
                ticker_symbol='META',
                status='success',
                news_count=7
            )
            db.session.add(log)
            db.session.commit()
            
            log_dict = log.to_dict()
            assert log_dict['ticker_symbol'] == 'META'
            assert log_dict['status'] == 'success'
            assert log_dict['news_count'] == 7


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
