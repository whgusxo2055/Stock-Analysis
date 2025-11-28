"""
종목 관리 라우트
- 관심 종목 추가/삭제/조회
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from datetime import datetime
import logging

from app.routes.auth import login_required
from app.models.models import UserStock, StockMaster
from app.extensions import db

logger = logging.getLogger(__name__)

stocks_bp = Blueprint('stocks', __name__, url_prefix='/stocks')


@stocks_bp.route('/')
@login_required
def index():
    """종목 관리 페이지"""
    user_id = session['user_id']
    
    # 사용자 관심 종목 조회
    user_stocks = db.session.query(UserStock, StockMaster)\
        .join(StockMaster, UserStock.ticker_symbol == StockMaster.ticker_symbol)\
        .filter(UserStock.user_id == user_id)\
        .order_by(UserStock.created_at.desc())\
        .all()
    
    # 전체 종목 목록 (추가 가능한 종목)
    all_stocks = StockMaster.query.order_by(StockMaster.ticker_symbol).all()
    
    return render_template(
        'stocks/index.html',
        user_stocks=user_stocks,
        all_stocks=all_stocks
    )


@stocks_bp.route('/api/my-stocks', methods=['GET'])
@login_required
def get_my_stocks():
    """내 관심 종목 조회 API"""
    user_id = session['user_id']
    
    user_stocks = db.session.query(UserStock, StockMaster)\
        .join(StockMaster, UserStock.ticker_symbol == StockMaster.ticker_symbol)\
        .filter(UserStock.user_id == user_id)\
        .all()
    
    stocks = [{
        'id': us.id,
        'ticker_symbol': us.ticker_symbol,
        'company_name': sm.company_name,
        'exchange': sm.exchange,
        'sector': sm.sector,
        'created_at': us.created_at.isoformat() if us.created_at else None
    } for us, sm in user_stocks]
    
    return jsonify({'stocks': stocks})


@stocks_bp.route('/api/add', methods=['POST'])
@login_required
def add_stock():
    """관심 종목 추가 API"""
    user_id = session['user_id']
    data = request.get_json() or request.form
    
    ticker_symbol = data.get('ticker_symbol', '').strip().upper()
    
    if not ticker_symbol:
        return jsonify({'success': False, 'error': '티커 심볼을 입력해주세요.'}), 400
    
    # 티커 심볼 검증 (알파벳과 숫자, 점만 허용)
    if not ticker_symbol.replace('.', '').replace('-', '').isalnum():
        return jsonify({'success': False, 'error': '유효하지 않은 티커 심볼입니다.'}), 400
    
    # 종목 존재 여부 확인
    stock = StockMaster.query.filter_by(ticker_symbol=ticker_symbol).first()
    if not stock:
        return jsonify({'success': False, 'error': f'종목 {ticker_symbol}을(를) 찾을 수 없습니다.'}), 404
    
    # 이미 추가된 종목인지 확인
    existing = UserStock.query.filter_by(
        user_id=user_id,
        ticker_symbol=ticker_symbol
    ).first()
    
    if existing:
        return jsonify({'success': False, 'error': '이미 추가된 종목입니다.'}), 400
    
    # 추가
    try:
        user_stock = UserStock(
            user_id=user_id,
            ticker_symbol=ticker_symbol
        )
        db.session.add(user_stock)
        db.session.commit()
        
        logger.info(f"User {user_id} added stock {ticker_symbol}")
        
        return jsonify({
            'success': True,
            'stock': {
                'id': user_stock.id,
                'ticker_symbol': ticker_symbol,
                'company_name': stock.company_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to add stock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '종목 추가에 실패했습니다.'}), 500


@stocks_bp.route('/api/remove/<int:stock_id>', methods=['DELETE'])
@login_required
def remove_stock(stock_id):
    """관심 종목 삭제 API"""
    user_id = session['user_id']
    
    user_stock = UserStock.query.filter_by(id=stock_id, user_id=user_id).first()
    
    if not user_stock:
        return jsonify({'success': False, 'error': '종목을 찾을 수 없습니다.'}), 404
    
    try:
        ticker = user_stock.ticker_symbol
        db.session.delete(user_stock)
        db.session.commit()
        
        logger.info(f"User {user_id} removed stock {ticker}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to remove stock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '종목 삭제에 실패했습니다.'}), 500


@stocks_bp.route('/api/search', methods=['GET'])
@login_required
def search_stocks():
    """종목 검색 API (FR-009-1 ~ FR-009-5)
    
    실시간 자동완성을 위한 종목 검색
    - 티커 심볼과 회사명으로 검색 (대소문자 무시)
    - 최대 20개 결과 반환
    - 이미 관심종목인 항목 표시
    """
    query = request.args.get('q', '').strip()
    user_id = session['user_id']
    
    # 2글자 미만이면 빈 결과 반환
    if not query or len(query) < 2:
        return jsonify({'stocks': []})
    
    # 입력값 길이 제한
    if len(query) > 50:
        return jsonify({'error': '검색어가 너무 깁니다.'}), 400
    
    try:
        # 티커 심볼, 영문 회사명, 한국어 회사명으로 검색 (대소문자 무시)
        search_pattern = f'%{query}%'
        stocks = StockMaster.query.filter(
            db.or_(
                StockMaster.ticker_symbol.ilike(search_pattern),
                StockMaster.company_name.ilike(search_pattern),
                StockMaster.company_name_ko.ilike(search_pattern)
            )
        ).order_by(
            # 정확히 일치하는 티커를 우선 표시
            db.case(
                (StockMaster.ticker_symbol.ilike(query), 0),
                (StockMaster.ticker_symbol.ilike(f'{query}%'), 1),
                else_=2
            ),
            StockMaster.ticker_symbol
        ).limit(20).all()
        
        # 현재 사용자의 관심종목 목록
        user_watchlist = set([
            us.ticker_symbol for us in 
            UserStock.query.filter_by(user_id=user_id).all()
        ])
        
        results = [{
            'ticker': s.ticker_symbol,
            'name': s.company_name,
            'name_ko': s.company_name_ko,
            'exchange': s.exchange,
            'sector': s.sector,
            'is_watchlist': s.ticker_symbol in user_watchlist
        } for s in stocks]
        
        return jsonify({'stocks': results})
        
    except Exception as e:
        logger.error(f"Stock search error: {e}", exc_info=True)
        return jsonify({'error': '검색 중 오류가 발생했습니다.'}), 500
