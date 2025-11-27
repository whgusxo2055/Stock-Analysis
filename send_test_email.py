#!/usr/bin/env python3
"""
이메일 발송 실제 테스트
- 테스트 이메일 발송 확인
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def send_test_email():
    """테스트 이메일 발송"""
    print("\n📧 테스트 이메일 발송")
    print("=" * 60)
    
    # Flask 앱 컨텍스트 필요
    from app import create_app
    app = create_app('development')
    
    with app.app_context():
        from app.models.models import User
        from app.services.email_sender import EmailSender
        
        # 첫 번째 사용자 조회
        user = User.query.first()
        
        if not user:
            print("❌ 사용자가 없습니다. 먼저 사용자를 생성하세요.")
            return False
        
        print(f"\n[테스트 대상]")
        print(f"   사용자: {user.username}")
        print(f"   이메일: {user.email}")
        
        # 이메일 발송
        email_sender = EmailSender()
        
        print("\n[이메일 발송 중...]")
        success, error = email_sender.send_test_email(user)
        
        if success:
            print(f"\n✅ 테스트 이메일 발송 성공!")
            print(f"   → {user.email}로 발송되었습니다.")
            return True
        else:
            print(f"\n❌ 테스트 이메일 발송 실패")
            print(f"   오류: {error}")
            return False


if __name__ == '__main__':
    print("\n⚠️  실제 이메일이 발송됩니다!")
    
    response = input("\n계속하시겠습니까? (y/n): ").strip().lower()
    
    if response == 'y':
        success = send_test_email()
        sys.exit(0 if success else 1)
    else:
        print("취소되었습니다.")
        sys.exit(0)
