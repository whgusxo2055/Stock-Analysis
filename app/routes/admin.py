"""
관리자 페이지 라우트
SRS FR-057, FR-058, FR-059, FR-060 구현
"""

import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session

from app.extensions import db
from app.models.models import User, UserSetting, UserStock, EmailLog, CrawlLog
from app.routes.auth import login_required, admin_required
from app.utils.elasticsearch_client import get_es_client

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_current_user():
    """현재 로그인된 사용자 조회"""
    if 'user_id' not in session:
        return None
    return db.session.get(User, session['user_id'])


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """관리자 메인 페이지 - 사용자 목록으로 리다이렉트"""
    return redirect(url_for('admin.users'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    사용자 목록 페이지
    FR-057: 사용자 목록 조회
    """
    try:
        # 전체 사용자 조회 (정렬: 최신순)
        all_users = User.query.order_by(User.created_at.desc()).all()
        
        return render_template(
            'admin/users.html',
            users=all_users,
            total_users=len(all_users),
            active_users=sum(1 for u in all_users if u.is_active),
            admin_users=sum(1 for u in all_users if u.is_admin)
        )
    except Exception as e:
        logger.error(f"Error loading users page: {e}")
        flash('사용자 목록을 불러오는 중 오류가 발생했습니다.', 'danger')
        return redirect(url_for('main.dashboard'))


@admin_bp.route('/system-status')
@login_required
@admin_required
def system_status():
    """
    시스템 상태 페이지
    FR-060: 시스템 상태 모니터링
    """
    return render_template('admin/system_status.html')


# ==================== API 엔드포인트 ====================

@admin_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    """
    사용자 목록 조회 API
    FR-057: 사용자 목록 조회
    """
    try:
        users = User.query.order_by(User.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'users': [user.to_dict() for user in users],
            'total': len(users)
        })
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def api_create_user():
    """
    사용자 생성 API
    FR-058: 새 사용자 등록
    """
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'{field} 필드는 필수입니다.'
                }), 400
        
        # 중복 검사
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({
                'success': False,
                'error': '이미 존재하는 사용자명 또는 이메일입니다.'
            }), 400
        
        # 새 사용자 생성
        new_user = User(
            username=data['username'],
            email=data['email'],
            is_active=data.get('is_active', True),
            is_admin=data.get('is_admin', False)
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        # 기본 설정 생성
        from datetime import time
        user_setting = UserSetting(
            user_id=new_user.id,
            language='ko',
            notification_time=time(9, 0),
            is_notification_enabled=True
        )
        db.session.add(user_setting)
        db.session.commit()
        
        logger.info(f"New user created: {new_user.username} by admin {session.get('username')}")
        
        return jsonify({
            'success': True,
            'message': '사용자가 생성되었습니다.',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {e}")
        return jsonify({
            'success': False,
            'error': f'사용자 생성 중 오류가 발생했습니다: {str(e)}'
        }), 500


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_user(user_id):
    """
    사용자 활성화/비활성화 API
    FR-059: 사용자 활성화/비활성화
    """
    try:
        user = db.session.get(User, user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': '사용자를 찾을 수 없습니다.'
            }), 404
        
        # 자기 자신은 비활성화 불가
        current_user = get_current_user()
        if user.id == current_user.id:
            return jsonify({
                'success': False,
                'error': '자기 자신은 비활성화할 수 없습니다.'
            }), 400
        
        data = request.get_json()
        
        # is_active 업데이트
        if 'is_active' in data:
            user.is_active = data['is_active']
            status = "활성화" if user.is_active else "비활성화"
            logger.info(f"User {user.username} {status} by admin {session.get('username')}")
        
        # is_admin 업데이트 (선택적)
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'사용자가 {status}되었습니다.',
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/test-email', methods=['POST'])
@login_required
@admin_required
def api_test_email():
    """
    테스트 이메일 발송 API
    SRS 8.5: POST /api/admin/test-email
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        # user_id가 없으면 현재 관리자에게 발송
        if not user_id:
            current_user = get_current_user()
            user_id = current_user.id
        
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({
                'success': False,
                'error': '사용자를 찾을 수 없습니다.'
            }), 404
        
        # 이메일 발송
        from app.services.email_sender import EmailSender
        
        email_sender = EmailSender()
        success, error = email_sender.send_test_email(user)
        
        if success:
            logger.info(f"Test email sent to {user.email} by admin {session.get('username')}")
            return jsonify({
                'success': True,
                'message': f'{user.email}로 테스트 이메일을 발송했습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': error or '이메일 발송에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/trigger/crawl', methods=['POST'])
@login_required
@admin_required
def api_trigger_crawl():
    """
    수동 크롤링 트리거 API
    """
    try:
        from app.services.scheduler import SchedulerService
        from threading import Thread
        
        scheduler = SchedulerService()
        if SchedulerService._scheduler is None:
            return jsonify({
                'success': False,
                'error': '스케줄러가 초기화되지 않았습니다.'
            }), 500
        
        # 별도 스레드에서 크롤링 작업 실행
        def run_crawl():
            scheduler._run_crawl_job()
        
        thread = Thread(target=run_crawl)
        thread.start()
        
        logger.info(f"Crawl job triggered manually by admin {session.get('username')}")
        return jsonify({
            'success': True,
            'message': '크롤링 작업이 시작되었습니다. 완료까지 몇 분이 소요될 수 있습니다.'
        })
            
    except Exception as e:
        logger.error(f"Error triggering crawl: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/trigger/email', methods=['POST'])
@login_required
@admin_required
def api_trigger_email():
    """
    수동 이메일 발송 트리거 API
    """
    try:
        from app.services.scheduler import SchedulerService
        from threading import Thread
        
        scheduler = SchedulerService()
        if SchedulerService._scheduler is None:
            return jsonify({
                'success': False,
                'error': '스케줄러가 초기화되지 않았습니다.'
            }), 500
        
        # 별도 스레드에서 이메일 작업 실행
        def run_email():
            scheduler._run_email_job()
        
        thread = Thread(target=run_email)
        thread.start()
        
        logger.info(f"Email job triggered manually by admin {session.get('username')}")
        return jsonify({
            'success': True,
            'message': '이메일 발송 작업이 시작되었습니다.'
        })
            
    except Exception as e:
        logger.error(f"Error triggering email: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@admin_bp.route('/api/system-status', methods=['GET'])
@login_required
@admin_required
def api_system_status():
    """
    시스템 상태 조회 API
    FR-060: 시스템 상태 모니터링
    """
    try:
        status = {
            'elasticsearch': _get_elasticsearch_status(),
            'crawler': _get_crawler_status(),
            'email': _get_email_status(),
            'scheduler': _get_scheduler_status()
        }
        
        return jsonify({
            'success': True,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 헬퍼 함수 ====================

def _get_elasticsearch_status():
    """ElasticSearch 상태 조회"""
    try:
        es = get_es_client()
        
        # 연결 확인 (ElasticsearchClient 래퍼 사용)
        if not es.is_connected():
            return {
                'status': 'disconnected',
                'documents': 0,
                'index': 'news_analysis'
            }
        
        # 문서 수 조회 (내부 client 사용)
        count_result = es.client.count(index=es.index_name)
        
        return {
            'status': 'connected',
            'documents': count_result['count'],
            'index': es.index_name
        }
    except Exception as e:
        logger.error(f"Error checking ES status: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'documents': 0,
            'index': 'news_analysis'
        }


def _get_crawler_status():
    """크롤러 상태 조회"""
    try:
        # 마지막 크롤링 로그 조회
        last_crawl = CrawlLog.query.order_by(CrawlLog.crawled_at.desc()).first()
        
        if not last_crawl:
            return {
                'last_run': None,
                'status': 'never_run',
                'articles_collected': 0
            }
        
        return {
            'last_run': last_crawl.crawled_at.isoformat(),
            'status': last_crawl.status,
            'articles_collected': last_crawl.news_count or 0,
            'ticker_symbol': last_crawl.ticker_symbol
        }
    except Exception as e:
        logger.error(f"Error checking crawler status: {e}")
        return {
            'last_run': None,
            'status': 'error',
            'error': str(e),
            'articles_collected': 0
        }


def _get_email_status():
    """이메일 발송 상태 조회"""
    try:
        # 마지막 메일 발송 로그 조회
        last_email = EmailLog.query.order_by(EmailLog.sent_at.desc()).first()
        
        if not last_email:
            return {
                'last_sent': None,
                'status': 'never_sent',
                'pending_count': 0
            }
        
        # 오늘 발송 대기 중인 사용자 수
        pending_count = UserSetting.query.filter_by(
            is_notification_enabled=True
        ).count()
        
        return {
            'last_sent': last_email.sent_at.isoformat(),
            'status': last_email.status,
            'news_count': last_email.news_count or 0,
            'pending_count': pending_count
        }
    except Exception as e:
        logger.error(f"Error checking email status: {e}")
        return {
            'last_sent': None,
            'status': 'error',
            'error': str(e),
            'pending_count': 0
        }


def _get_scheduler_status():
    """스케줄러 상태 조회"""
    try:
        # SchedulerService 클래스에서 직접 스케줄러 가져오기
        from app.services.scheduler import SchedulerService
        
        scheduler = SchedulerService._scheduler
        
        if scheduler is None:
            return {
                'status': 'not_configured',
                'jobs': []
            }
        
        # 실행 중인 작업 목록
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None
            })
        
        return {
            'status': 'running' if scheduler.running else 'stopped',
            'jobs': jobs
        }
    except Exception as e:
        logger.error(f"Error checking scheduler status: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'jobs': []
        }
