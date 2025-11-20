"""
비즈니스 로직 서비스 모듈
"""
from .news_storage import NewsStorageAdapter, get_news_storage

__all__ = ['NewsStorageAdapter', 'get_news_storage']
