"""
메인 페이지 라우트
- 대시보드
"""

from flask import Blueprint, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import logging

from app.routes.auth import login_required
from app.models.models import User, UserStock, StockMaster
from app.services.news_storage import NewsStorageAdapter
from app.extensions import db

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """메인 페이지 (로그인 시 대시보드, 미로그인 시 로그인 페이지)"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """대시보드"""
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    
    # 사용자 관심 종목 조회
    user_stocks = db.session.query(UserStock, StockMaster)\
        .join(StockMaster, UserStock.ticker_symbol == StockMaster.ticker_symbol)\
        .filter(UserStock.user_id == user_id)\
        .all()
    
    # ElasticSearch에서 최신 뉴스 조회
    storage = NewsStorageAdapter()
    recent_news = []
    stats = {
        'total': 0,
        'positive': 0,
        'negative': 0,
        'neutral': 0
    }
    
    try:
        # 최근 24시간 뉴스
        from_date = datetime.now() - timedelta(days=1)
        
        for user_stock, stock_info in user_stocks:
            ticker = user_stock.ticker_symbol
            
            # 종목별 최신 뉴스 5개
            result = storage.search_news(
                ticker_symbol=ticker,
                from_date=from_date.isoformat(),
                size=5
            )
            
            # search_news는 Dict를 반환 (hits 키에 뉴스 리스트)
            news_items = result.get('hits', []) if isinstance(result, dict) else []
            
            for item in news_items:
                stats['total'] += 1
                sentiment_data = item.get('sentiment', {})
                sentiment_label = sentiment_data.get('label', 'neutral').lower()
                
                if sentiment_label in ['positive', 'negative', 'neutral']:
                    stats[sentiment_label] = stats.get(sentiment_label, 0) + 1
                else:
                    stats['neutral'] = stats.get('neutral', 0) + 1
                
                recent_news.append({
                    'ticker': ticker,
                    'company_name': stock_info.company_name,
                    'title': item.get('title', 'N/A'),
                    'summary': item.get('summary_ko', item.get('summary', {}).get('ko', '')),
                    'url': item.get('url', '#'),
                    'published_date': item.get('published_at') or item.get('published_date'),
                    'sentiment_score': sentiment_data.get('score', 0),
                    'sentiment_label': sentiment_label,
                    'news_id': item.get('news_id', item.get('_id'))
                })
        
        # 날짜순 정렬 (None 값 처리)
        recent_news.sort(key=lambda x: x.get('published_date') or '0', reverse=True)
        
    except Exception as e:
        logger.error(f"Failed to load dashboard data: {e}", exc_info=True)
    
    return render_template(
        'main/dashboard.html',
        user=user,
        stocks=user_stocks,
        news=recent_news[:20],  # 최대 20개
        stats=stats
    )
