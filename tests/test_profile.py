"""
프로필 관리 기능 테스트
Sprint 9.3: 사용자 프로필 수정 기능 테스트

테스트 범위:
- S9.3-001: 프로필 조회 API (GET /settings/api/user/profile)
- S9.3-002: 프로필 수정 API (PUT /settings/api/user/profile)
- S9.3-003: 비밀번호 변경 검증
- S9.3-004: 프로필 편집 페이지
"""

import pytest
import sys
import os
import uuid
from datetime import time

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.models import User, UserSetting


@pytest.fixture
def app():
    """테스트용 Flask 앱 생성"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    # 고유한 인메모리 DB 사용
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///:memory:?cache=shared&uri=true&mode=memory&unique={uuid.uuid4().hex}'
    
    with app.app_context():
        # 테이블 초기화
        db.drop_all()
        db.create_all()
        
        # 유니크한 테스트 사용자 생성
        unique_id = uuid.uuid4().hex[:8]
        test_user = User(
            username=f'testuser_{unique_id}',
            email=f'test_{unique_id}@example.com',
            is_active=True,
            is_admin=False
        )
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.flush()  # ID 할당
        
        # 테스트 사용자 설정 추가
        test_setting = UserSetting(
            user_id=test_user.id,
            language='ko',
            notification_time=time(8, 0),  # Time 객체로 변환
            is_notification_enabled=True
        )
        db.session.add(test_setting)
        
        # 다른 사용자 (이메일 중복 테스트용)
        other_user = User(
            username=f'otheruser_{unique_id}',
            email=f'other_{unique_id}@example.com',
            is_active=True,
            is_admin=False
        )
        other_user.set_password('password123')
        db.session.add(other_user)
        
        db.session.commit()
        
        # 테스트에서 사용할 정보 저장
        app.test_user_username = test_user.username
        app.test_user_email = test_user.email
        app.other_user_email = other_user.email
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """테스트 클라이언트"""
    return app.test_client()


@pytest.fixture
def authenticated_client(app, client):
    """인증된 테스트 클라이언트"""
    with app.app_context():
        user = User.query.filter_by(username=app.test_user_username).first()
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['username'] = user.username
            sess['is_admin'] = user.is_admin
    return client


class TestProfileAPI:
    """프로필 API 테스트"""
    
    def test_get_profile_unauthenticated(self, client):
        """S9.3-001: 비인증 상태에서 프로필 조회 시 리다이렉트"""
        response = client.get('/settings/api/user/profile')
        assert response.status_code == 302  # 로그인 페이지로 리다이렉트
    
    def test_get_profile_authenticated(self, app, authenticated_client):
        """S9.3-001: 인증 상태에서 프로필 조회 성공"""
        response = authenticated_client.get('/settings/api/user/profile')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'profile' in data
        assert data['profile']['username'] == app.test_user_username
        assert data['profile']['email'] == app.test_user_email
    
    def test_update_profile_no_data(self, authenticated_client):
        """S9.3-002: 빈 데이터로 프로필 수정 시 에러"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        # 빈 데이터이므로 '요청 데이터가 없습니다' 또는 '변경할 내용' 메시지
        assert 'error' in data


class TestEmailChange:
    """이메일 변경 테스트"""
    
    def test_change_email_success(self, app, authenticated_client):
        """이메일 변경 성공"""
        new_email = f'newemail_{uuid.uuid4().hex[:8]}@example.com'
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={'email': new_email},
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert '이메일' in data['message']
        
        # DB 확인
        with app.app_context():
            user = User.query.filter_by(username=app.test_user_username).first()
            assert user.email == new_email
    
    def test_change_email_same(self, app, authenticated_client):
        """동일한 이메일로 변경 시 에러"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={'email': app.test_user_email},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '변경할 내용' in data['error']
    
    def test_change_email_duplicate(self, app, authenticated_client):
        """중복 이메일로 변경 시 에러"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={'email': app.other_user_email},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '이미 사용 중' in data['error']
    
    def test_change_email_invalid_format(self, authenticated_client):
        """잘못된 이메일 형식"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={'email': 'invalid-email'},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '유효하지 않은 이메일' in data['error']


class TestPasswordChange:
    """비밀번호 변경 테스트 (S9.3-003)"""
    
    def test_change_password_success(self, app, authenticated_client):
        """비밀번호 변경 성공"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'current_password': 'password123',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert '비밀번호' in data['message']
        
        # 새 비밀번호로 로그인 가능 확인
        with app.app_context():
            user = User.query.filter_by(username=app.test_user_username).first()
            assert user.check_password('newpassword123') is True
            assert user.check_password('password123') is False
    
    def test_change_password_wrong_current(self, authenticated_client):
        """현재 비밀번호 틀림"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'current_password': 'wrongpassword',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '일치하지 않습니다' in data['error']
    
    def test_change_password_no_current(self, authenticated_client):
        """현재 비밀번호 미입력"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '현재 비밀번호' in data['error']
    
    def test_change_password_too_short(self, authenticated_client):
        """새 비밀번호 너무 짧음"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'current_password': 'password123',
                'new_password': '123',
                'confirm_password': '123'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '6자 이상' in data['error']
    
    def test_change_password_mismatch(self, authenticated_client):
        """새 비밀번호 확인 불일치"""
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'current_password': 'password123',
                'new_password': 'newpassword123',
                'confirm_password': 'differentpassword'
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        
        data = response.get_json()
        assert data['success'] is False
        assert '확인 비밀번호가 일치하지 않습니다' in data['error']


class TestProfilePage:
    """프로필 편집 페이지 테스트 (S9.3-004)"""
    
    def test_profile_page_unauthenticated(self, client):
        """비인증 상태에서 프로필 페이지 접근 시 리다이렉트"""
        response = client.get('/settings/profile')
        assert response.status_code == 302
    
    def test_profile_page_authenticated(self, app, authenticated_client):
        """인증 상태에서 프로필 페이지 접근 성공"""
        response = authenticated_client.get('/settings/profile')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        assert '프로필 편집' in html
        assert '이메일 변경' in html
        assert '비밀번호 변경' in html
        assert app.test_user_username in html
    
    def test_settings_page_has_profile_link(self, authenticated_client):
        """설정 페이지에 프로필 편집 링크 존재"""
        response = authenticated_client.get('/settings/')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        assert '프로필 편집' in html
        assert '/settings/profile' in html


class TestBothEmailAndPassword:
    """이메일과 비밀번호 동시 변경 테스트"""
    
    def test_change_both_success(self, app, authenticated_client):
        """이메일과 비밀번호 동시 변경 성공"""
        new_email = f'newemail_{uuid.uuid4().hex[:8]}@example.com'
        response = authenticated_client.put(
            '/settings/api/user/profile',
            json={
                'email': new_email,
                'current_password': 'password123',
                'new_password': 'newpassword123',
                'confirm_password': 'newpassword123'
            },
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert '비밀번호' in data['message']
        assert '이메일' in data['message']
        
        # DB 확인
        with app.app_context():
            user = User.query.filter_by(username=app.test_user_username).first()
            assert user.email == new_email
            assert user.check_password('newpassword123') is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
