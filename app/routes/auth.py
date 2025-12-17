"""
인증 관련 라우트
- 로그인/로그아웃
- 세션 관리
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from functools import wraps
import logging
import re
from datetime import time

from app.models.models import User, UserSetting
from app.extensions import db

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(f):
    """로그인 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """관리자 권한 필수 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('로그인이 필요합니다.', 'warning')
            return redirect(url_for('auth.login'))
        
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin:
            flash('관리자 권한이 필요합니다.', 'danger')
            return redirect(url_for('main.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지 및 처리"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('아이디와 비밀번호를 입력해주세요.', 'danger')
            return render_template('auth/login.html')
        
        # 입력값 길이 검증
        if len(username) > 50 or len(password) > 255:
            flash('입력값이 너무 깁니다.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.is_active and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            logger.info(f"User logged in: {username}")
            flash(f'{user.username}님, 환영합니다!', 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            logger.warning(f"Failed login attempt for: {username}")
            flash('아이디 또는 비밀번호가 올바르지 않습니다.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 페이지 및 처리 (기본 정보만 입력)"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 필수값 검증
        if not username or not email or not password:
            flash('아이디, 이메일, 비밀번호는 필수입니다.', 'danger')
            return render_template('auth/register.html')

        # 길이/형식 검증
        if len(username) > 50 or len(email) > 100 or len(password) > 255:
            flash('입력값이 너무 깁니다.', 'danger')
            return render_template('auth/register.html')

        if not re.fullmatch(r"[A-Za-z0-9]{3,50}", username):
            flash('아이디는 3~50자의 영문/숫자만 가능합니다.', 'danger')
            return render_template('auth/register.html')

        if not _EMAIL_RE.match(email):
            flash('유효하지 않은 이메일 형식입니다.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 8:
            flash('비밀번호는 최소 8자 이상이어야 합니다.', 'danger')
            return render_template('auth/register.html')

        if confirm_password and password != confirm_password:
            flash('비밀번호 확인이 일치하지 않습니다.', 'danger')
            return render_template('auth/register.html')

        # 중복 검사
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('이미 존재하는 아이디 또는 이메일입니다.', 'danger')
            return render_template('auth/register.html')

        try:
            new_user = User(username=username, email=email, is_active=True, is_admin=False)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()  # ID 할당

            # 기본 설정 생성 (입력받지 않고 기본값 적용)
            user_setting = UserSetting(
                user_id=new_user.id,
                language='ko',
                notification_time=time(9, 0),
                is_notification_enabled=True,
            )
            db.session.add(user_setting)
            db.session.commit()

            # 가입 후 자동 로그인
            session['user_id'] = new_user.id
            session['username'] = new_user.username
            session['is_admin'] = new_user.is_admin

            logger.info(f"User registered: {username}")
            flash('회원가입이 완료되었습니다.', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering user: {e}")
            flash('회원가입 중 오류가 발생했습니다.', 'danger')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
def logout():
    """로그아웃"""
    username = session.get('username', 'Unknown')
    session.clear()
    logger.info(f"User logged out: {username}")
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/session', methods=['GET'])
def check_session():
    """세션 확인 API"""
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'is_admin': user.is_admin
                }
            })
    
    return jsonify({'authenticated': False}), 401


@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """회원가입 API (기본 정보만 입력)"""
    if not request.is_json:
        return jsonify({'success': False, 'error': 'JSON 요청만 지원합니다.'}), 415

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'success': False, 'error': 'username, email, password는 필수입니다.'}), 400

    if len(username) > 50 or len(email) > 100 or len(password) > 255:
        return jsonify({'success': False, 'error': '입력값이 너무 깁니다.'}), 400

    if not re.fullmatch(r"[A-Za-z0-9]{3,50}", username):
        return jsonify({'success': False, 'error': 'username은 3~50자의 영문/숫자만 가능합니다.'}), 400

    if not _EMAIL_RE.match(email):
        return jsonify({'success': False, 'error': '유효하지 않은 이메일 형식입니다.'}), 400

    if len(password) < 8:
        return jsonify({'success': False, 'error': '비밀번호는 최소 8자 이상이어야 합니다.'}), 400

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return jsonify({'success': False, 'error': '이미 존재하는 사용자명 또는 이메일입니다.'}), 400

    try:
        new_user = User(username=username, email=email, is_active=True, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.flush()

        user_setting = UserSetting(
            user_id=new_user.id,
            language='ko',
            notification_time=time(9, 0),
            is_notification_enabled=True,
        )
        db.session.add(user_setting)
        db.session.commit()

        return jsonify(
            {
                'success': True,
                'message': '회원가입이 완료되었습니다.',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username,
                    'email': new_user.email,
                },
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering user via API: {e}")
        return jsonify({'success': False, 'error': '회원가입 중 오류가 발생했습니다.'}), 500
