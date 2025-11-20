"""
로깅 시스템 설정
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logging(app=None, log_dir='logs', log_level='INFO'):
    """
    애플리케이션 로깅 설정
    
    Args:
        app: Flask 애플리케이션 인스턴스 (선택)
        log_dir (str): 로그 디렉토리
        log_level (str): 로그 레벨
    """
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 레벨 설정
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 로그 포맷 정의
    log_format = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)
    
    # 전체 애플리케이션 로그 파일 핸들러
    app_log_file = os.path.join(log_dir, 'app.log')
    app_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    app_handler.setLevel(level)
    app_handler.setFormatter(log_format)
    root_logger.addHandler(app_handler)
    
    # 에러 전용 로그 파일 핸들러
    error_log_file = os.path.join(log_dir, 'error.log')
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)
    
    # 크롤러 전용 로그
    crawler_logger = logging.getLogger('crawler')
    crawler_log_file = os.path.join(log_dir, 'crawler.log')
    crawler_handler = RotatingFileHandler(
        crawler_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    crawler_handler.setLevel(level)
    crawler_handler.setFormatter(log_format)
    crawler_logger.addHandler(crawler_handler)
    
    # 이메일 전용 로그
    email_logger = logging.getLogger('email')
    email_log_file = os.path.join(log_dir, 'email.log')
    email_handler = RotatingFileHandler(
        email_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    email_handler.setLevel(level)
    email_handler.setFormatter(log_format)
    email_logger.addHandler(email_handler)
    
    # Flask 애플리케이션 로거 설정
    if app:
        app.logger.setLevel(level)
        app.logger.info("Logging system initialized")
    
    logging.info(f"✓ Logging configured - Level: {log_level}, Directory: {log_dir}")


def get_logger(name: str) -> logging.Logger:
    """
    특정 모듈의 로거 반환
    
    Args:
        name (str): 로거 이름
    
    Returns:
        logging.Logger: 로거 인스턴스
    """
    return logging.getLogger(name)


# 편의 함수들
def log_info(message: str, logger_name: str = None):
    """INFO 레벨 로그"""
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.info(message)


def log_warning(message: str, logger_name: str = None):
    """WARNING 레벨 로그"""
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.warning(message)


def log_error(message: str, logger_name: str = None, exc_info: bool = False):
    """ERROR 레벨 로그"""
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.error(message, exc_info=exc_info)


def log_critical(message: str, logger_name: str = None, exc_info: bool = False):
    """CRITICAL 레벨 로그"""
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.critical(message, exc_info=exc_info)


def log_debug(message: str, logger_name: str = None):
    """DEBUG 레벨 로그"""
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    logger.debug(message)
