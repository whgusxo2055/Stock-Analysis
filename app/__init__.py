"""
Flask 애플리케이션 팩토리
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
import os

# 전역 확장 인스턴스
db = SQLAlchemy()
session = Session()


def create_app(config_name='development'):
    """
    Flask 애플리케이션 팩토리 함수
    
    Args:
        config_name (str): 설정 환경 ('development', 'production', 'testing')
    
    Returns:
        Flask: 설정된 Flask 애플리케이션 인스턴스
    """
    app = Flask(__name__)
    
    # 설정 로드
    from app.utils.config import get_config
    config = get_config(config_name)
    app.config.from_object(config)
    
    # 로깅 설정
    from app.utils.logger import setup_logging
    setup_logging(app, log_dir=config.LOG_DIR, log_level=config.LOG_LEVEL)
    
    # 확장 초기화
    db.init_app(app)
    session.init_app(app)
    
    # Blueprint 등록 (추후 구현)
    # from app.routes import auth, user, stocks, news, admin
    # app.register_blueprint(auth.bp)
    # app.register_blueprint(user.bp)
    # app.register_blueprint(stocks.bp)
    # app.register_blueprint(news.bp)
    # app.register_blueprint(admin.bp)
    
    # 기본 라우트
    @app.route('/')
    def index():
        return {
            'status': 'ok',
            'message': 'Stock Analysis Service API',
            'version': '1.0.0'
        }
    
    @app.route('/health')
    def health():
        """헬스 체크 엔드포인트"""
        return {
            'status': 'healthy',
            'database': 'connected'
        }
    
    # 데이터베이스 초기화
    with app.app_context():
        # 테이블 생성 (모델이 정의된 후)
        db.create_all()
    
    return app
