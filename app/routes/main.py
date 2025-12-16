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
        # 최근 30일 뉴스, 관심 종목 전체 조회
        from datetime import timezone
        from_date = datetime.now(timezone.utc) - timedelta(days=30)
        ticker_list = [us.ticker_symbol for us, _ in user_stocks]
        ticker_company = {us.ticker_symbol: stock.company_name for us, stock in user_stocks}

        if ticker_list:
            result = storage.search_news(
                ticker_symbols=ticker_list,
                from_date=from_date.isoformat(),
                size=100
            )
            news_items = result.get('hits', []) if isinstance(result, dict) else []

            for item in news_items:
                published = item.get('published_date') or item.get('date') or item.get('crawled_date')
                stats['total'] += 1
                sentiment_data = item.get('sentiment', {})
                sentiment_label = sentiment_data.get('classification', sentiment_data.get('label', 'neutral'))
                if sentiment_label:
                    sentiment_label = sentiment_label.lower()
                if sentiment_label in ['positive', 'negative', 'neutral']:
                    stats[sentiment_label] = stats.get(sentiment_label, 0) + 1
                else:
                    stats['neutral'] = stats.get('neutral', 0) + 1

                ticker = item.get('ticker_symbol') or item.get('ticker')
                recent_news.append({
                    'ticker': ticker,
                    'company_name': ticker_company.get(ticker, ''),
                    'title': item.get('title', 'N/A'),
                    'summary': item.get('summary_ko', item.get('summary', {}).get('ko', '')) or item.get('content', ''),
                    'url': item.get('source_url') or item.get('url', '#'),
                    'published_date': published,
                    'sentiment_score': sentiment_data.get('score', 0),
                    'sentiment_label': sentiment_label,
                    'news_id': item.get('news_id', item.get('_id'))
                })

            recent_news.sort(key=lambda x: x.get('published_date') or '0', reverse=True)
        else:
            logger.info("No watchlist tickers for dashboard")

    except Exception as e:
        logger.error(f"Failed to load dashboard data: {e}", exc_info=True)
    
    return render_template(
        'main/dashboard.html',
        user=user,
        stocks=user_stocks,
        news=recent_news[:20],  # 최대 20개
        stats=stats
    )
