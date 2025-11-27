#!/usr/bin/env python3
"""
관리자 계정 생성 스크립트
Admin Account Creation Script

Usage:
    python scripts/create_admin.py
    
Description:
    - 관리자 계정을 생성하거나 기존 사용자를 관리자로 승격합니다
    - 대화형 방식으로 사용자 정보를 입력받습니다
    - 이메일 중복 검사를 수행합니다
"""

import sys
import os
from getpass import getpass

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from datetime import datetime


def validate_email(email):
    """이메일 형식 검증"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def create_admin_account():
    """관리자 계정 생성"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("관리자 계정 생성")
        print("=" * 60)
        print()
        
        # 사용자명 입력
        while True:
            username = input("사용자명 (3-20자): ").strip()
            if not username:
                print("❌ 사용자명을 입력해주세요.")
                continue
            if len(username) < 3 or len(username) > 20:
                print("❌ 사용자명은 3-20자 사이여야 합니다.")
                continue
            
            # 중복 체크
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"❌ 사용자명 '{username}'은(는) 이미 사용 중입니다.")
                continue
            break
        
        # 이메일 입력
        while True:
            email = input("이메일: ").strip().lower()
            if not email:
                print("❌ 이메일을 입력해주세요.")
                continue
            if not validate_email(email):
                print("❌ 올바른 이메일 형식이 아닙니다.")
                continue
            
            # 중복 체크
            existing = User.query.filter_by(email=email).first()
            if existing:
                print(f"❌ 이메일 '{email}'은(는) 이미 사용 중입니다.")
                
                # 기존 사용자를 관리자로 승격할지 물어봄
                upgrade = input("기존 사용자를 관리자로 승격하시겠습니까? (y/n): ").strip().lower()
                if upgrade == 'y':
                    existing.is_admin = True
                    existing.is_active = True
                    db.session.commit()
                    print()
                    print("=" * 60)
                    print(f"✅ '{existing.username}'님이 관리자로 승격되었습니다!")
                    print("=" * 60)
                    print(f"사용자명: {existing.username}")
                    print(f"이메일: {existing.email}")
                    print(f"관리자: {'예' if existing.is_admin else '아니오'}")
                    print(f"활성화: {'예' if existing.is_active else '아니오'}")
                    print("=" * 60)
                    return
                continue
            break
        
        # 비밀번호 입력
        while True:
            password = getpass("비밀번호 (8자 이상): ")
            if not password:
                print("❌ 비밀번호를 입력해주세요.")
                continue
            if len(password) < 8:
                print("❌ 비밀번호는 최소 8자 이상이어야 합니다.")
                continue
            
            password_confirm = getpass("비밀번호 확인: ")
            if password != password_confirm:
                print("❌ 비밀번호가 일치하지 않습니다.")
                continue
            break
        
        # 사용자 생성
        try:
            admin_user = User(
                username=username,
                email=email,
                is_admin=True,
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin_user.set_password(password)
            
            db.session.add(admin_user)
            db.session.commit()
            
            print()
            print("=" * 60)
            print("✅ 관리자 계정이 성공적으로 생성되었습니다!")
            print("=" * 60)
            print(f"사용자명: {username}")
            print(f"이메일: {email}")
            print(f"관리자: 예")
            print(f"활성화: 예")
            print("=" * 60)
            print()
            print("이제 이 계정으로 로그인하여 관리자 기능을 사용할 수 있습니다.")
            print()
            
        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 60)
            print(f"❌ 오류 발생: {str(e)}")
            print("=" * 60)
            sys.exit(1)


def list_admins():
    """현재 관리자 목록 조회"""
    app = create_app()
    
    with app.app_context():
        admins = User.query.filter_by(is_admin=True).all()
        
        print()
        print("=" * 60)
        print(f"현재 관리자 목록 (총 {len(admins)}명)")
        print("=" * 60)
        
        if not admins:
            print("등록된 관리자가 없습니다.")
        else:
            for admin in admins:
                status = "활성" if admin.is_active else "비활성"
                print(f"- {admin.username} ({admin.email}) - {status}")
        
        print("=" * 60)
        print()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='관리자 계정 관리')
    parser.add_argument('--list', action='store_true', help='현재 관리자 목록 조회')
    
    args = parser.parse_args()
    
    if args.list:
        list_admins()
    else:
        create_admin_account()
