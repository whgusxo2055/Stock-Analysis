#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.models import User
from app import create_app


def create_admin_user(username='admin', password='admin123', email='admin@example.com'):
    """관리자 계정 생성"""
    app = create_app()
    
    with app.app_context():
        # 기존 사용자 확인
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"❌ 사용자 '{username}'가 이미 존재합니다.")
            return False
        
        # 새 사용자 생성
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            is_admin=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✅ 관리자 계정이 생성되었습니다:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"   Admin: True")
        
        return True


def create_test_user(username='testuser', password='test123', email='test@example.com'):
    """일반 사용자 계정 생성"""
    app = create_app()
    
    with app.app_context():
        # 기존 사용자 확인
        existing_user = User.query.filter_by(username=username).first()
        
        if existing_user:
            print(f"❌ 사용자 '{username}'가 이미 존재합니다.")
            return False
        
        # 새 사용자 생성
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            is_admin=False
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"✅ 일반 사용자 계정이 생성되었습니다:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
        print(f"   Admin: False")
        
        return True


if __name__ == '__main__':
    print("=" * 60)
    print("사용자 계정 생성 스크립트")
    print("=" * 60)
    
    # 관리자 계정 생성
    create_admin_user()
    
    print()
    
    # 테스트 사용자 계정 생성
    create_test_user()
    
    print()
    print("=" * 60)
    print("계정 생성이 완료되었습니다.")
    print("Flask 앱을 실행하고 http://localhost:5000 에 접속하세요.")
    print("=" * 60)
