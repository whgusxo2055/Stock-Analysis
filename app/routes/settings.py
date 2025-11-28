"""
설정 관리 라우트
- 사용자 알림 설정
- SRS FR-029, FR-030, FR-053, FR-054 구현
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session

from app.extensions import db
from app.models.models import User, UserSetting, UserStock
from app.routes.auth import login_required

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


def get_current_user():
    """현재 로그인된 사용자 조회"""
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])


@settings_bp.route('/')
@login_required
def settings_page():
    """
    설정 페이지
    FR-029: 메일 수신 시각 설정
    FR-030: 수신 언어 선택
    FR-053: 알림 ON/OFF
    """
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('auth.login'))
    
    # 사용자 설정 조회
    user_setting = UserSetting.query.filter_by(user_id=current_user.id).first()
    
    if not user_setting:
        # 기본 설정 생성
        user_setting = UserSetting(
            user_id=current_user.id,
            language='ko',
            notification_time='08:00',
            is_notification_enabled=True
        )
        db.session.add(user_setting)
        db.session.commit()
    
    # 사용자의 관심 종목 수
    stock_count = UserStock.query.filter_by(
        user_id=current_user.id
    ).count()
    
    # 시간 옵션 생성 (00:00 ~ 23:00)
    time_options = [f"{h:02d}:00" for h in range(24)]
    
    # 언어 옵션
    language_options = [
        ('ko', '한국어'),
        ('en', 'English'),
        ('es', 'Español'),
        ('ja', '日本語')
    ]
    
    return render_template(
        'settings.html',
        user=current_user,
        setting=user_setting,
        stock_count=stock_count,
        time_options=time_options,
        language_options=language_options
    )


@settings_bp.route('/update', methods=['POST'])
@login_required
def update_settings():
    """
    설정 업데이트
    """
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('auth.login'))
    
    try:
        user_setting = UserSetting.query.filter_by(user_id=current_user.id).first()
        
        if not user_setting:
            user_setting = UserSetting(user_id=current_user.id)
            db.session.add(user_setting)
        
        # 폼 데이터 처리
        language = request.form.get('language', 'ko')
        notification_time = request.form.get('notification_time', '08:00')
        is_notification_enabled = request.form.get('is_notification_enabled') == 'on'
        
        # 유효성 검증
        valid_languages = ['ko', 'en', 'es', 'ja']
        if language not in valid_languages:
            language = 'ko'
        
        # 시간 형식 검증
        try:
            datetime.strptime(notification_time, '%H:%M')
        except ValueError:
            notification_time = '08:00'
        
        # 설정 업데이트
        user_setting.language = language
        user_setting.notification_time = notification_time
        user_setting.is_notification_enabled = is_notification_enabled
        user_setting.updated_at = datetime.now()
        
        db.session.commit()
        
        flash('설정이 저장되었습니다.', 'success')
        logger.info(f"Settings updated for user {current_user.username}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating settings: {e}")
        flash('설정 저장 중 오류가 발생했습니다.', 'error')
    
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/test-email', methods=['POST'])
@login_required
def send_test_email():
    """
    테스트 이메일 발송
    FR-054: 테스트 메일 발송 버튼
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    
    try:
        from app.services.email_sender import EmailSender
        
        email_sender = EmailSender()
        success, error = email_sender.send_test_email(current_user)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'테스트 이메일이 {current_user.email}로 발송되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'이메일 발송 실패: {error}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({
            'success': False,
            'message': f'오류 발생: {str(e)}'
        }), 500


@settings_bp.route('/api/status')
@login_required
def get_status():
    """
    현재 설정 상태 API
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        user_setting = UserSetting.query.filter_by(user_id=current_user.id).first()
        
        stock_count = UserStock.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).count()
        
        if user_setting:
            return jsonify({
                'language': user_setting.language,
                'notification_time': user_setting.notification_time,
                'is_notification_enabled': user_setting.is_notification_enabled,
                'stock_count': stock_count,
                'updated_at': user_setting.updated_at.isoformat() if user_setting.updated_at else None
            })
        else:
            return jsonify({
                'language': 'ko',
                'notification_time': '08:00',
                'is_notification_enabled': False,
                'stock_count': stock_count,
                'updated_at': None
            })
            
    except Exception as e:
        logger.error(f"Error getting settings status: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/api/toggle-notification', methods=['POST'])
@login_required
def toggle_notification():
    """
    알림 ON/OFF 토글 API
    FR-053: 알림 ON/OFF 버튼
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        user_setting = UserSetting.query.filter_by(user_id=current_user.id).first()
        
        if not user_setting:
            user_setting = UserSetting(
                user_id=current_user.id,
                language='ko',
                notification_time='08:00',
                is_notification_enabled=True
            )
            db.session.add(user_setting)
        else:
            user_setting.is_notification_enabled = not user_setting.is_notification_enabled
        
        user_setting.updated_at = datetime.now()
        db.session.commit()
        
        status = "활성화" if user_setting.is_notification_enabled else "비활성화"
        logger.info(f"Notification {status} for user {current_user.username}")
        
        return jsonify({
            'success': True,
            'is_enabled': user_setting.is_notification_enabled,
            'message': f'알림이 {status}되었습니다.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling notification: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================
# 프로필 관리 API (SRS FR-005, FR-055, FR-056)
# ============================================================

@settings_bp.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    """
    프로필 조회 API
    S9.3-001: GET /api/user/profile
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        return jsonify({
            'success': True,
            'profile': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'is_admin': current_user.is_admin,
                'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
                'updated_at': current_user.updated_at.isoformat() if current_user.updated_at else None
            }
        })
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    """
    프로필 수정 API
    S9.3-002: PUT /api/user/profile - 이메일/비밀번호 변경
    FR-005: 사용자 정보 수정
    FR-055: 비밀번호 변경
    FR-056: 이메일 변경
    """
    current_user = get_current_user()
    if not current_user:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '요청 데이터가 없습니다.'}), 400
        
        updated_fields = []
        
        # 비밀번호 변경
        if data.get('new_password'):
            # 현재 비밀번호 확인 필수
            current_password = data.get('current_password')
            if not current_password:
                return jsonify({
                    'success': False,
                    'error': '현재 비밀번호를 입력해주세요.'
                }), 400
            
            # S9.3-003: 비밀번호 변경 검증
            if not current_user.check_password(current_password):
                return jsonify({
                    'success': False,
                    'error': '현재 비밀번호가 일치하지 않습니다.'
                }), 400
            
            # 새 비밀번호 유효성 검사
            new_password = data.get('new_password')
            if len(new_password) < 6:
                return jsonify({
                    'success': False,
                    'error': '새 비밀번호는 6자 이상이어야 합니다.'
                }), 400
            
            # 비밀번호 확인
            confirm_password = data.get('confirm_password')
            if new_password != confirm_password:
                return jsonify({
                    'success': False,
                    'error': '새 비밀번호와 확인 비밀번호가 일치하지 않습니다.'
                }), 400
            
            current_user.set_password(new_password)
            updated_fields.append('비밀번호')
            logger.info(f"Password updated for user {current_user.username}")
        
        # 이메일 변경
        new_email = data.get('email')
        if new_email and new_email != current_user.email:
            # 이메일 형식 검증 (간단한 정규식)
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, new_email):
                return jsonify({
                    'success': False,
                    'error': '유효하지 않은 이메일 형식입니다.'
                }), 400
            
            # 중복 이메일 확인
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'error': '이미 사용 중인 이메일입니다.'
                }), 400
            
            current_user.email = new_email
            updated_fields.append('이메일')
            logger.info(f"Email updated for user {current_user.username}: {new_email}")
        
        if not updated_fields:
            return jsonify({
                'success': False,
                'error': '변경할 내용이 없습니다.'
            }), 400
        
        current_user.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{", ".join(updated_fields)}이(가) 변경되었습니다.',
            'profile': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'updated_at': current_user.updated_at.isoformat() if current_user.updated_at else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {e}")
        return jsonify({
            'success': False,
            'error': f'프로필 수정 중 오류가 발생했습니다: {str(e)}'
        }), 500


@settings_bp.route('/profile')
@login_required
def profile_page():
    """
    프로필 편집 페이지
    S9.3-004: /settings/profile 라우트
    """
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('auth.login'))
    
    return render_template(
        'settings/profile.html',
        user=current_user
    )
