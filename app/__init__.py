"""
Flask 애플리케이션 팩토리
"""
from flask import Flask
import os

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
    
    # Flask 세션용 secret key 설정
    if not app.config.get('SECRET_KEY'):
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            if config_name == 'production':
                raise ValueError("SECRET_KEY must be set in production environment")
            else:
                import secrets
                secret_key = secrets.token_hex(32)
                app.logger.warning("Using randomly generated SECRET_KEY. Set SECRET_KEY environment variable for persistent sessions.")
        app.config['SECRET_KEY'] = secret_key
    
    # 로깅 설정
    from app.utils.logger import setup_logging
    setup_logging(app, log_dir=config.LOG_DIR, log_level=config.LOG_LEVEL)
    
    # 확장 초기화
    from app.extensions import db
    db.init_app(app)
    
    # Blueprint 등록
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.stocks import stocks_bp
    from app.routes.news import news_bp
    from app.routes.settings import settings_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(stocks_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(admin_bp)
    
    # 보안 헤더 추가
    @app.after_request
    def add_security_headers(response):
        """보안 헤더 추가"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if config_name == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        """404 에러 핸들러"""
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 에러 핸들러"""
        app.logger.error(f"Internal error: {error}")
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    # 헬스 체크
    @app.route('/health')
    def health():
        """헬스 체크 엔드포인트"""
        try:
            # DB 연결 확인
            db.session.execute(db.text('SELECT 1'))
            db_status = 'connected'
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            db_status = 'disconnected'
        
        return {
            'status': 'healthy' if db_status == 'connected' else 'unhealthy',
            'database': db_status
        }
    
    # 데이터베이스 초기화
    with app.app_context():
        # 테이블 생성
        db.create_all()
    
    # 스케줄러 초기화 (Gunicorn preload 또는 단일 프로세스에서만)
    # 환경변수로 스케줄러 활성화 여부 결정
    if os.environ.get('ENABLE_SCHEDULER', 'true').lower() == 'true':
        # Gunicorn 워커가 아닌 경우에만 스케줄러 시작
        # (Gunicorn은 --preload 옵션과 함께 사용하거나 별도 프로세스로 실행)
        is_gunicorn = 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '')
        is_main_process = os.environ.get('SCHEDULER_MAIN', 'false').lower() == 'true'
        
        if not is_gunicorn or is_main_process:
            try:
                from app.services.scheduler import SchedulerService
                scheduler_service = SchedulerService()
                scheduler_service.init_app(app)
                app.logger.info("✓ Scheduler initialized successfully")
            except Exception as e:
                app.logger.warning(f"Scheduler initialization skipped: {e}")
    
    return app
