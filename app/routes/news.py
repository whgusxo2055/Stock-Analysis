"""
뉴스 관련 라우트
- 뉴스 조회/히스토리/상세
"""

from flask import Blueprint, render_template, request, jsonify, session
from datetime import datetime, timedelta
import logging

from app.routes.auth import login_required
from app.models.models import UserStock, StockMaster
from app.services.news_storage import NewsStorageAdapter
from app.extensions import db

logger = logging.getLogger(__name__)

news_bp = Blueprint('news', __name__, url_prefix='/news')


@news_bp.route('/')
@login_required
def news_page():
    """뉴스 히스토리 페이지"""
    user_id = session['user_id']
    
    # 필터 파라미터 (검증 추가)
    ticker = request.args.get('ticker', '').strip().upper()
    from_date = request.args.get('from', '').strip()
    to_date = request.args.get('to', '').strip()
    sentiment = request.args.get('sentiment', '').strip().lower()
    
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    
    per_page = 20
    
    # sentiment 값 검증
    if sentiment and sentiment not in ['positive', 'negative', 'neutral']:
        sentiment = ''
    
    # 사용자 관심 종목 조회
    user_stocks = UserStock.query.filter_by(user_id=user_id).all()
    
    storage = NewsStorageAdapter()
    
    # 검색할 종목 결정
    if ticker:
        ticker_symbols = [ticker]
    else:
        ticker_symbols = [stock.ticker_symbol for stock in user_stocks]
    
    # 날짜 설정
    if not from_date:
        from_date = (datetime.now() - timedelta(days=30)).isoformat()
    if not to_date:
        to_date = datetime.now().isoformat()
    
    # 뉴스 검색
    news_list = []
    total = 0
    
    if ticker_symbols:
        try:
            # 단일 티커만 지원하는 경우 첫 번째 티커 사용
            search_ticker = ticker_symbols[0] if len(ticker_symbols) == 1 else None
            
            result = storage.search_news(
                ticker_symbol=search_ticker,
                from_date=from_date if from_date else None,
                to_date=to_date if to_date else None,
                sentiment=sentiment if sentiment else None,
                size=per_page,
                page=page
            )
            
            # search_news가 Dict를 반환 (total, hits 키 포함)
            if isinstance(result, dict):
                news_list = result.get('hits', [])
                total = result.get('total', 0)
            else:
                news_list = []
                total = 0
                
        except Exception as e:
            logger.error(f"뉴스 조회 중 오류: {e}", exc_info=True)
            news_list = []
            total = 0
    
    return render_template(
        'news/index.html',
        news_list=news_list,
        user_stocks=user_stocks,
        total=total,
        page=page,
        per_page=per_page
    )


@news_bp.route('/api/latest', methods=['GET'])
@login_required
def get_latest():
    """최신 뉴스 조회 API"""
    user_id = session['user_id']
    ticker = request.args.get('ticker', '').upper()
    limit = int(request.args.get('limit', 10))
    
    storage = NewsStorageAdapter()
    
    try:
        # 티커 지정 시 해당 종목만, 없으면 전체
        if ticker:
            # 사용자가 관심 종목으로 등록했는지 확인
            user_stock = UserStock.query.filter_by(
                user_id=user_id,
                ticker_symbol=ticker
            ).first()
            
            if not user_stock:
                return jsonify({'error': '관심 종목이 아닙니다.'}), 403
            
            from_date = (datetime.now() - timedelta(days=7)).isoformat()
            news = storage.search_news(
                ticker_symbol=ticker,
                from_date=from_date,
                size=limit
            )
        else:
            # 사용자 전체 관심 종목 뉴스
            user_stocks = UserStock.query.filter_by(user_id=user_id).all()
            tickers = [us.ticker_symbol for us in user_stocks]
            
            from_date = (datetime.now() - timedelta(days=3)).isoformat()
            news = storage.search_news(
                ticker_symbols=tickers,
                from_date=from_date,
                size=limit
            )
        
        # 응답 포맷
        results = [{
            'news_id': item.get('_id'),
            'ticker_symbol': item.get('ticker_symbol'),
            'company_name': item.get('company_name'),
            'title': item.get('title'),
            'summary': item.get('summary', {}),
            'url': item.get('url'),
            'published_date': item.get('published_date'),
            'sentiment': item.get('sentiment', {})
        } for item in news]
        
        return jsonify({'news': results})
        
    except Exception as e:
        logger.error(f"Failed to fetch news: {e}", exc_info=True)
        return jsonify({'error': '뉴스 조회에 실패했습니다.'}), 500


@news_bp.route('/api/history', methods=['GET'])
@login_required
def get_history():
    """뉴스 히스토리 조회 API (필터링 지원)"""
    user_id = session['user_id']
    
    # 파라미터
    ticker = request.args.get('ticker', '').upper()
    from_date = request.args.get('from', '')
    to_date = request.args.get('to', '')
    sentiment = request.args.get('sentiment', '')  # Positive/Negative/Neutral
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    
    storage = NewsStorageAdapter()
    
    try:
        # 사용자 관심 종목 확인
        user_stocks = UserStock.query.filter_by(user_id=user_id).all()
        user_tickers = [us.ticker_symbol for us in user_stocks]
        
        if ticker and ticker not in user_tickers:
            return jsonify({'error': '관심 종목이 아닙니다.'}), 403
        
        # 검색 조건 구성
        tickers = [ticker] if ticker else user_tickers
        
        if not from_date:
            from_date = (datetime.now() - timedelta(days=30)).isoformat()
        if not to_date:
            to_date = datetime.now().isoformat()
        
        # ElasticSearch 검색
        news = storage.search_news(
            ticker_symbols=tickers,
            from_date=from_date,
            to_date=to_date,
            sentiment=sentiment or None,
            size=per_page,
            from_=(page - 1) * per_page
        )
        
        # 전체 개수 (간이 방식)
        total_news = storage.count_news(
            ticker_symbols=tickers,
            from_date=from_date,
            to_date=to_date,
            sentiment=sentiment or None
        )
        
        results = [{
            'news_id': item.get('_id'),
            'ticker_symbol': item.get('ticker_symbol'),
            'company_name': item.get('company_name'),
            'title': item.get('title'),
            'summary': item.get('summary', {}),
            'url': item.get('url'),
            'published_date': item.get('published_date'),
            'sentiment': item.get('sentiment', {})
        } for item in news]
        
        return jsonify({
            'news': results,
            'total': total_news,
            'page': page,
            'per_page': per_page
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch news history: {e}", exc_info=True)
        return jsonify({'error': '뉴스 히스토리 조회에 실패했습니다.'}), 500


@news_bp.route('/<news_id>')
@login_required
def detail(news_id):
    """뉴스 상세 페이지"""
    storage = NewsStorageAdapter()
    
    try:
        news_data = storage.get_news_by_id(news_id)
        
        if not news_data:
            return render_template('errors/404.html'), 404
        
        # 템플릿 필드명 통일
        sentiment_data = news_data.get('sentiment', {})
        if sentiment_data:
            news_data['sentiment_label'] = sentiment_data.get('label', 'neutral').lower()
            news_data['sentiment_score'] = sentiment_data.get('score', 0.0)
        
        # 다국어 요약
        summary_data = news_data.get('summary', {})
        if summary_data:
            news_data['summary_ko'] = summary_data.get('ko', '')
            news_data['summary_en'] = summary_data.get('en', '')
            news_data['summary_ja'] = summary_data.get('ja', '')
            news_data['summary_zh'] = summary_data.get('zh', '')
        
        return render_template('news/detail.html', news=news_data)
        
    except Exception as e:
        logger.error(f"Failed to fetch news detail: {e}", exc_info=True)
        return render_template('errors/500.html'), 500


@news_bp.route('/api/<news_id>', methods=['GET'])
@login_required
def get_detail(news_id):
    """뉴스 상세 조회 API"""
    storage = NewsStorageAdapter()
    
    try:
        news = storage.get_news_by_id(news_id)
        
        if not news:
            return jsonify({'error': '뉴스를 찾을 수 없습니다.'}), 404
        
        return jsonify({
            'news_id': news.get('_id'),
            'ticker_symbol': news.get('ticker_symbol'),
            'company_name': news.get('company_name'),
            'title': news.get('title'),
            'content': news.get('content'),
            'summary': news.get('summary', {}),
            'url': news.get('url'),
            'published_date': news.get('published_date'),
            'crawled_date': news.get('crawled_date'),
            'sentiment': news.get('sentiment', {})
        })
        
    except Exception as e:
        logger.error(f"Failed to fetch news detail: {e}", exc_info=True)
        return jsonify({'error': '뉴스 조회에 실패했습니다.'}), 500
