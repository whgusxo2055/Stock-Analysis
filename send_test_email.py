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


def send_test_report():
    """보고서 템플릿 테스트 이메일 발송"""
    print("\n📧 보고서 템플릿 테스트 이메일 발송")
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
        
        # 샘플 뉴스 데이터
        sample_news_by_stock = {
            'TSLA': [
                {
                    'title': 'Tesla Q4 실적 발표, 시장 예상치 상회',
                    'summary': {
                        'ko': '테슬라가 4분기 실적을 발표했습니다. 매출과 순이익 모두 시장 예상치를 상회하며 주가에 긍정적인 영향을 미칠 것으로 예상됩니다.',
                        'en': 'Tesla reported Q4 earnings, exceeding market expectations in both revenue and net income.',
                        'es': 'Tesla informó ganancias del cuarto trimestre, superando las expectativas del mercado.',
                        'ja': 'テスラが第4四半期の業績を発表し、売上高と純利益ともに市場予想を上回りました。'
                    },
                    'sentiment': {
                        'classification': 'positive',
                        'score': 8
                    },
                    'url': 'https://www.investing.com/news/tesla-q4-earnings',
                    'published_date': '2025-11-28 09:30:00'
                },
                {
                    'title': 'Elon Musk, 새로운 EV 모델 발표 예정',
                    'summary': {
                        'ko': '엘론 머스크 CEO가 내년 초 새로운 전기차 모델을 발표할 예정이라고 밝혔습니다.',
                        'en': 'CEO Elon Musk announced plans to unveil a new EV model early next year.',
                        'es': 'El CEO Elon Musk anunció planes para presentar un nuevo modelo de vehículo eléctrico.',
                        'ja': 'イーロン・マスクCEOが来年初めに新しいEVモデルを発表する予定だと明らかにしました。'
                    },
                    'sentiment': {
                        'classification': 'positive',
                        'score': 6
                    },
                    'url': 'https://www.investing.com/news/tesla-new-model',
                    'published_date': '2025-11-28 10:15:00'
                }
            ],
            'AAPL': [
                {
                    'title': 'Apple, 중국 시장 점유율 하락 우려',
                    'summary': {
                        'ko': '애플의 중국 스마트폰 시장 점유율이 화웨이에 밀려 하락하고 있다는 보도가 나왔습니다.',
                        'en': 'Reports indicate Apple\'s smartphone market share in China is declining due to competition from Huawei.',
                        'es': 'Los informes indican que la cuota de mercado de Apple en China está disminuyendo.',
                        'ja': 'アップルの中国スマートフォン市場シェアがファーウェイに押されて下落しているという報道が出ました。'
                    },
                    'sentiment': {
                        'classification': 'negative',
                        'score': -5
                    },
                    'url': 'https://www.investing.com/news/apple-china-market',
                    'published_date': '2025-11-28 08:45:00'
                }
            ],
            'NVDA': [
                {
                    'title': 'NVIDIA, AI 칩 수요 증가로 분기 실적 호조',
                    'summary': {
                        'ko': '엔비디아가 AI 관련 GPU 수요 급증으로 분기 실적이 크게 개선되었습니다.',
                        'en': 'NVIDIA reported strong quarterly results driven by surging demand for AI-related GPUs.',
                        'es': 'NVIDIA informó resultados trimestrales sólidos impulsados por la demanda de GPUs para IA.',
                        'ja': 'NVIDIAがAI関連GPU需要の急増により四半期業績が大幅に改善しました。'
                    },
                    'sentiment': {
                        'classification': 'positive',
                        'score': 9
                    },
                    'url': 'https://www.investing.com/news/nvidia-ai-demand',
                    'published_date': '2025-11-28 11:00:00'
                }
            ]
        }
        
        # 이메일 발송
        email_sender = EmailSender()
        
        print("\n[보고서 이메일 발송 중...]")
        success, error = email_sender.send_stock_report(
            user=user,
            news_by_stock=sample_news_by_stock,
            language='ko'
        )
        
        if success:
            print(f"\n✅ 보고서 이메일 발송 성공!")
            print(f"   → {user.email}로 발송되었습니다.")
            return True
        else:
            print(f"\n❌ 보고서 이메일 발송 실패")
            print(f"   오류: {error}")
            return False


if __name__ == '__main__':
    print("\n⚠️  실제 이메일이 발송됩니다!")
    print("\n테스트 유형을 선택하세요:")
    print("  1. 간단한 테스트 이메일")
    print("  2. 보고서 템플릿 테스트 (샘플 뉴스 포함)")
    
    choice = input("\n선택 (1 또는 2): ").strip()
    
    if choice == '1':
        response = input("\n계속하시겠습니까? (y/n): ").strip().lower()
        if response == 'y':
            success = send_test_email()
            sys.exit(0 if success else 1)
        else:
            print("취소되었습니다.")
            sys.exit(0)
    elif choice == '2':
        response = input("\n계속하시겠습니까? (y/n): ").strip().lower()
        if response == 'y':
            success = send_test_report()
            sys.exit(0 if success else 1)
        else:
            print("취소되었습니다.")
            sys.exit(0)
    else:
        print("잘못된 선택입니다.")
        sys.exit(1)
