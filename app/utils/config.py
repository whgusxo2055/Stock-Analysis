"""
환경 변수 및 설정 관리 유틸리티
"""
import os
from typing import Any
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class Config:
    """기본 설정 클래스"""
    
    # Flask 설정
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 데이터베이스 설정
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/app.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # ElasticSearch 설정
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
    ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'news_analysis')
    
    # OpenAI 설정
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')
    
    # Gmail 설정
    GMAIL_USERNAME = os.getenv('GMAIL_USERNAME', '')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', '')
    GMAIL_SMTP_SERVER = os.getenv('GMAIL_SMTP_SERVER', 'smtp.gmail.com')
    GMAIL_SMTP_PORT = int(os.getenv('GMAIL_SMTP_PORT', '587'))
    
    # 크롤러 설정
    CRAWLER_TYPE = os.getenv('CRAWLER_TYPE', 'selenium')
    HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
    CRAWL_TIMEOUT = int(os.getenv('CRAWL_TIMEOUT', '45'))
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
    
    # 스케줄러 설정
    CRAWL_INTERVAL_HOURS = int(os.getenv('CRAWL_INTERVAL_HOURS', '3'))
    CRAWL_LOOKBACK_HOURS = int(os.getenv('CRAWL_LOOKBACK_HOURS', '96'))
    NEWS_RETENTION_DAYS = int(os.getenv('NEWS_RETENTION_DAYS', '730'))  # 2년
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        환경 변수 값을 가져옴
        
        Args:
            key (str): 환경 변수 키
            default (Any): 기본값
        
        Returns:
            Any: 환경 변수 값 또는 기본값
        """
        return os.getenv(key, default)
    
    @staticmethod
    def validate_config() -> bool:
        """
        필수 설정 값이 존재하는지 검증
        
        Returns:
            bool: 검증 성공 여부
        """
        required_keys = [
            'SECRET_KEY',
            'OPENAI_API_KEY',
            'GMAIL_USERNAME',
            'GMAIL_APP_PASSWORD'
        ]
        
        missing_keys = []
        for key in required_keys:
            value = getattr(Config, key, None) or os.getenv(key)
            if not value or value == '':
                missing_keys.append(key)
        
        if missing_keys:
            print(f"⚠️  경고: 다음 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_keys)}")
            return False
        
        return True


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """운영 환경 설정"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """테스트 환경 설정"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False


# 설정 딕셔너리
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str = None) -> Config:
    """
    설정 객체를 반환
    
    Args:
        config_name (str): 설정 환경 이름
    
    Returns:
        Config: 설정 객체
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
