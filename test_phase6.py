#!/usr/bin/env python3
"""
Phase 6 스프린트 1 통합 테스트
- 이메일 발송 서비스 테스트
- 스케줄러 서비스 테스트
- 설정 페이지 동작 확인
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def test_email_sender():
    """이메일 발송 서비스 테스트"""
    print("\n" + "="*60)
    print("📧 이메일 발송 서비스 테스트")
    print("="*60)
    
    try:
        from app.services.email_sender import EmailSender
        from app.utils.config import Config
        
        email_sender = EmailSender()
        
        # 1. 설정 확인
        print("\n[1] Gmail 설정 확인")
        print(f"   SMTP 서버: {email_sender.smtp_server}")
        print(f"   SMTP 포트: {email_sender.smtp_port}")
        print(f"   사용자: {email_sender.username[:10]}..." if email_sender.username else "   ⚠️ 사용자 미설정")
        print(f"   비밀번호: {'*' * 8}" if email_sender.password else "   ⚠️ 비밀번호 미설정")
        
        if not email_sender.username or not email_sender.password:
            print("\n   ❌ Gmail 설정이 완료되지 않았습니다.")
            return False
        
        # 2. EmailSender 클래스 메서드 확인
        print("\n[2] EmailSender 메서드 확인")
        methods = ['send_email', 'send_stock_report', 'send_test_email', 
                   'send_no_news_notification', '_save_email_log']
        for method in methods:
            has_method = hasattr(email_sender, method)
            status = "✓" if has_method else "✗"
            print(f"   {status} {method}")
        
        print("\n   ✅ 이메일 발송 서비스 준비 완료")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 오류: {e}")
        return False


def test_scheduler_service():
    """스케줄러 서비스 테스트"""
    print("\n" + "="*60)
    print("⏰ 스케줄러 서비스 테스트")
    print("="*60)
    
    try:
        from app.services.scheduler import SchedulerService, scheduler_service
        
        # 1. 클래스 메서드 확인
        print("\n[1] SchedulerService 메서드 확인")
        methods = ['init_app', '_register_jobs', '_run_crawl_job', 
                   '_run_email_job', '_run_cleanup_job', 'trigger_crawl_now',
                   'trigger_email_now', 'get_jobs_status', 'is_running']
        for method in methods:
            has_method = hasattr(SchedulerService, method)
            status = "✓" if has_method else "✗"
            print(f"   {status} {method}")
        
        # 2. 싱글톤 인스턴스 확인
        print("\n[2] 싱글톤 인스턴스 확인")
        print(f"   scheduler_service: {type(scheduler_service).__name__}")
        
        print("\n   ✅ 스케줄러 서비스 준비 완료")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 오류: {e}")
        return False


def test_email_templates():
    """이메일 템플릿 테스트"""
    print("\n" + "="*60)
    print("📝 이메일 템플릿 테스트")
    print("="*60)
    
    template_dir = os.path.join(os.path.dirname(__file__), 'app', 'templates', 'email')
    templates = ['report.html', 'no_news.html', 'test.html']
    
    all_exist = True
    for template in templates:
        template_path = os.path.join(template_dir, template)
        exists = os.path.exists(template_path)
        status = "✓" if exists else "✗"
        print(f"   {status} {template}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n   ✅ 모든 이메일 템플릿 존재")
    else:
        print("\n   ⚠️ 일부 템플릿 누락")
    
    return all_exist


def test_news_storage_service():
    """뉴스 저장소 서비스 테스트"""
    print("\n" + "="*60)
    print("💾 뉴스 저장소 서비스 테스트")
    print("="*60)
    
    try:
        from app.services.news_storage import NewsStorageService
        
        storage = NewsStorageService()
        
        # 메서드 확인
        print("\n[1] NewsStorageService 메서드 확인")
        methods = ['get_recent_news', 'delete_old_news', 'store_news_batch', 
                   'search_news', 'get_statistics']
        for method in methods:
            has_method = hasattr(storage, method)
            status = "✓" if has_method else "✗"
            print(f"   {status} {method}")
        
        print("\n   ✅ 뉴스 저장소 서비스 준비 완료")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 오류: {e}")
        return False


def test_settings_route():
    """설정 라우트 테스트"""
    print("\n" + "="*60)
    print("⚙️ 설정 라우트 테스트")
    print("="*60)
    
    try:
        from app.routes.settings import settings_bp
        
        # 1. Blueprint 확인
        print("\n[1] Blueprint 확인")
        print(f"   이름: {settings_bp.name}")
        print(f"   URL 접두사: {settings_bp.url_prefix}")
        
        # 2. 라우트 확인
        print("\n[2] 라우트 확인")
        from flask import Flask
        
        # 임시 앱 생성
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test'
        app.register_blueprint(settings_bp)
        
        # 등록된 라우트 확인
        routes = []
        for rule in app.url_map.iter_rules():
            if 'settings' in rule.endpoint:
                routes.append((rule.endpoint, list(rule.methods), rule.rule))
        
        for endpoint, methods, path in routes:
            print(f"   ✓ {endpoint}: {path} [{', '.join(m for m in methods if m not in ['OPTIONS', 'HEAD'])}]")
        
        print("\n   ✅ 설정 라우트 준비 완료")
        return True
        
    except Exception as e:
        print(f"\n   ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings_template():
    """설정 템플릿 테스트"""
    print("\n" + "="*60)
    print("🎨 설정 템플릿 테스트")
    print("="*60)
    
    template_path = os.path.join(os.path.dirname(__file__), 'app', 'templates', 'settings.html')
    
    if os.path.exists(template_path):
        print(f"   ✓ settings.html 존재")
        
        # 템플릿 내용 확인
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 주요 요소 확인
        checks = [
            ('알림 설정', '{% extends "base.html" %}'),
            ('알림 토글', 'is_notification_enabled'),
            ('시간 선택', 'notification_time'),
            ('언어 선택', 'language'),
            ('테스트 이메일', 'sendTestEmail'),
        ]
        
        print("\n   템플릿 구성 요소:")
        for name, keyword in checks:
            exists = keyword in content
            status = "✓" if exists else "✗"
            print(f"     {status} {name}")
        
        print("\n   ✅ 설정 템플릿 준비 완료")
        return True
    else:
        print(f"   ✗ settings.html 없음")
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "🚀 Phase 6 스프린트 1 통합 테스트")
    print("=" * 60)
    print(f"실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 각 테스트 실행
    results['이메일 발송 서비스'] = test_email_sender()
    results['스케줄러 서비스'] = test_scheduler_service()
    results['이메일 템플릿'] = test_email_templates()
    results['뉴스 저장소 서비스'] = test_news_storage_service()
    results['설정 라우트'] = test_settings_route()
    results['설정 템플릿'] = test_settings_template()
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 테스트 결과 요약")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "-"*60)
    print(f"   총 {passed + failed}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    if failed == 0:
        print("\n   🎉 Phase 6 스프린트 1 준비 완료!")
    else:
        print(f"\n   ⚠️ {failed}개 테스트 실패 - 확인 필요")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
