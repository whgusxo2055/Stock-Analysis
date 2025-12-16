"""
스케줄러 서비스
- APScheduler를 이용한 크롤링/메일/정리 작업 스케줄링
- SRS FR-035~038, plan.md 6.5 구현
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from flask import Flask

from app.extensions import db
from app.models.models import User, UserSetting, UserStock, CrawlLog, KST
from app.utils.config import Config

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    백그라운드 작업 스케줄러
    
    Jobs:
    - crawl_job: 3시간마다 뉴스 크롤링
    - email_job: 1시간마다 메일 발송 체크
    - cleanup_job: 매일 오래된 데이터 정리
    """

    _instance: Optional['SchedulerService'] = None
    _scheduler: Optional[BackgroundScheduler] = None
    _app: Optional[Flask] = None

    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app: Optional[Flask] = None):
        """
        초기화
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """
        Flask 앱과 연결
        
        Args:
            app: Flask 애플리케이션 인스턴스
        """
        if SchedulerService._scheduler is not None:
            logger.warning("Scheduler already initialized")
            return

        SchedulerService._app = app
        
        # 스케줄러 생성
        SchedulerService._scheduler = BackgroundScheduler(
            timezone='Asia/Seoul',  # 한국 시간대
            job_defaults={
                'coalesce': True,       # 놓친 작업 합치기
                'max_instances': 1,     # 동시 실행 방지
                'misfire_grace_time': 300  # 5분 유예
            }
        )

        # 작업 등록 (앱 컨텍스트에서)
        with app.app_context():
            self._register_jobs()

        # 스케줄러 시작
        SchedulerService._scheduler.start()
        logger.info("Scheduler started successfully")

        # 앱 종료 시 스케줄러 정지
        atexit.register(self.shutdown)

    def _register_jobs(self) -> None:
        """작업 등록"""
        if SchedulerService._scheduler is None:
            logger.error("Scheduler not initialized")
            return

        # 1. 크롤링 작업 - 3시간마다 (FR-013)
        crawl_interval = max(Config.CRAWL_INTERVAL_HOURS, 1)
        SchedulerService._scheduler.add_job(
            func=self._run_crawl_job,
            trigger=IntervalTrigger(hours=crawl_interval),
            id='crawl_job',
            name='News Crawling Job',
            replace_existing=True
        )
        logger.info(f"Registered crawl_job: every {crawl_interval} hours")

        # 2. 이메일 발송 체크 - 1시간마다 (FR-035)
        SchedulerService._scheduler.add_job(
            func=self._run_email_job,
            trigger=IntervalTrigger(hours=1),
            id='email_job',
            name='Email Sending Job',
            replace_existing=True
        )
        logger.info("Registered email_job: every 1 hour")

        # 3. 데이터 정리 - 매일 새벽 2시 (SRS 9.3)
        SchedulerService._scheduler.add_job(
            func=self._run_cleanup_job,
            trigger=CronTrigger(hour=2, minute=0),
            id='cleanup_job',
            name='Data Cleanup Job',
            replace_existing=True
        )
        logger.info("Registered cleanup_job: daily at 02:00")

    def _run_crawl_job(self) -> None:
        """
        뉴스 크롤링 작업 실행
        모든 활성 사용자의 관심 종목에 대해 뉴스 수집
        """
        logger.info("Starting crawl_job...")
        
        if SchedulerService._app is None:
            logger.error("Flask app not available")
            return

        with SchedulerService._app.app_context():
            try:
                from app.services.crawler_service import CrawlerService
                from app.services.news_storage import NewsStorageAdapter
                
                # 서비스 초기화
                storage = NewsStorageAdapter()
                crawler = CrawlerService(
                    db_session=db.session,
                    news_storage=storage
                )
                crawl_window_hours = max(Config.CRAWL_LOOKBACK_HOURS, Config.CRAWL_INTERVAL_HOURS * 2)
                
                # 모든 관심 종목 조회 (활성 사용자의 종목만)
                active_users = User.query.filter_by(is_active=True).all()
                user_ids = [u.id for u in active_users]
                active_stocks = UserStock.query.filter(UserStock.user_id.in_(user_ids)).all()
                tickers = list(set([stock.ticker_symbol for stock in active_stocks]))
                
                if not tickers:
                    logger.info("No active stocks to crawl")
                    return

                logger.info(f"Crawling news for {len(tickers)} tickers: {tickers}")
                
                total_news = 0
                for ticker in tickers:
                    try:
                        # 뉴스 크롤링 (crawl_ticker 사용)
                        result = crawler.crawl_ticker(ticker, hours_ago=crawl_window_hours)
                        
                        if result.get('status') in ['SUCCESS', 'PARTIAL']:
                            count = result.get('count', 0)
                            total_news += count
                            logger.info(
                                f"Crawled {count} news for {ticker} "
                                f"(lookback {crawl_window_hours}h)"
                            )
                        else:
                            logger.warning(f"Crawl failed for {ticker}: {result.get('error')}")
                        
                    except Exception as e:
                        logger.error(f"Error crawling {ticker}: {e}")
                        continue

                # 크롤링 로그 기록
                crawl_log = CrawlLog(
                    ticker_symbol=','.join(tickers),
                    status='success' if total_news > 0 else 'no_news',
                    news_count=total_news
                )
                db.session.add(crawl_log)
                db.session.commit()

                logger.info(f"Crawl job completed: {total_news} news items stored")

            except Exception as e:
                logger.error(f"Crawl job failed: {e}")
                # 에러 로그 기록
                try:
                    crawl_log = CrawlLog(
                        ticker_symbol='ALL',
                        status='error',
                        news_count=0,
                        error_message=str(e)[:500]
                    )
                    db.session.add(crawl_log)
                    db.session.commit()
                except:
                    pass

    def _run_email_job(self) -> None:
        """
        이메일 발송 작업 실행
        현재 시간에 알림을 받아야 할 사용자에게 이메일 발송
        """
        logger.info("Starting email_job...")
        
        if SchedulerService._app is None:
            logger.error("Flask app not available")
            return

        with SchedulerService._app.app_context():
            try:
                from app.services.email_sender import EmailSender
                from app.services.news_storage import NewsStorageService
                from datetime import time as dt_time
                
                email_sender = EmailSender()
                storage = NewsStorageService()
                
                # 현재 시간 확인 (한국 시간)
                now = datetime.now(KST)
                current_time = dt_time(now.hour, 0)  # time 객체로 변환 (분은 0)
                
                logger.info(f"Checking users for notification time: {current_time.strftime('%H:%M')}")
                
                # 해당 시간에 알림 설정된 사용자 조회
                users_to_notify = self._get_users_to_notify(current_time)
                
                if not users_to_notify:
                    logger.info(f"No users to notify at {current_time.strftime('%H:%M')}")
                    return

                logger.info(f"Found {len(users_to_notify)} users to notify")
                
                for user, setting in users_to_notify:
                    try:
                        # 사용자의 관심 종목 조회
                        user_stocks = UserStock.query.filter_by(
                            user_id=user.id
                        ).all()
                        
                        if not user_stocks:
                            logger.info(f"No stocks for user {user.username}")
                            continue
                        
                        tickers = [stock.ticker_symbol for stock in user_stocks]
                        
                        # 마지막 보고서 발송 이후의 뉴스 조회 (24시간, UTC 기준)
                        # 크롤링 주기가 3시간이지만, 뉴스 발행 시점이 다를 수 있음
                        news_by_stock = {}
                        for ticker in tickers:
                            news_list = storage.get_recent_news(ticker, hours=48)
                            if news_list:
                                news_by_stock[ticker] = news_list
                        
                        # 이메일 발송
                        language = setting.language if setting else 'ko'
                        
                        if news_by_stock:
                            success, error = email_sender.send_stock_report(
                                user=user,
                                news_by_stock=news_by_stock,
                                language=language
                            )
                        else:
                            # 뉴스 없음 알림 (FR-036)
                            success, error = email_sender.send_no_news_notification(
                                user=user,
                                language=language
                            )
                        
                        if success:
                            logger.info(f"Email sent to {user.email}")
                        else:
                            logger.warning(f"Failed to send email to {user.email}: {error}")

                    except Exception as e:
                        logger.error(f"Error sending email to {user.username}: {e}")
                        continue

                logger.info("Email job completed")

            except Exception as e:
                logger.error(f"Email job failed: {e}")

    def _get_users_to_notify(self, current_time) -> List[tuple]:
        """
        알림 받을 사용자 목록 조회
        
        Args:
            current_time: 현재 시각 (time 객체)
            
        Returns:
            [(User, UserSetting), ...]
        """
        try:
            from datetime import time as dt_time
            
            # time 객체로 변환 (문자열이 들어올 경우 대비)
            if isinstance(current_time, str):
                # "HH:00" 형식의 문자열 처리
                hour = int(current_time.split(':')[0])
                current_time = dt_time(hour, 0)
            
            # 알림 활성화 + 해당 시각 설정 사용자 조회
            results = db.session.query(User, UserSetting).join(
                UserSetting,
                User.id == UserSetting.user_id
            ).filter(
                UserSetting.is_notification_enabled == True,
                UserSetting.notification_time == current_time
            ).all()
            
            logger.info(f"Query for notification_time={current_time}, found {len(results)} users")
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting users to notify: {e}")
            return []

    def _run_cleanup_job(self) -> None:
        """
        데이터 정리 작업 실행
        - 2년 이상 오래된 ES 데이터 삭제 (FR-028)
        - 오래된 로그 정리
        """
        logger.info("Starting cleanup_job...")
        
        if SchedulerService._app is None:
            logger.error("Flask app not available")
            return

        with SchedulerService._app.app_context():
            try:
                from app.services.news_storage import NewsStorageService
                
                storage = NewsStorageService()
                
                # 2년 전 날짜 계산
                cutoff_date = datetime.now(KST) - timedelta(days=730)  # 약 2년
                
                # 오래된 뉴스 삭제
                deleted_count = storage.delete_old_news(cutoff_date)
                logger.info(f"Deleted {deleted_count} old news items")
                
                # 오래된 이메일 로그 삭제 (SRS: 1년 이상)
                self._cleanup_old_logs(days=365)
                
                # 오래된 크롤링 로그 삭제 (SRS: 1년 이상)
                self._cleanup_crawl_logs(days=365)
                
                logger.info("Cleanup job completed")

            except Exception as e:
                logger.error(f"Cleanup job failed: {e}")

    def _cleanup_old_logs(self, days: int = 180) -> None:
        """
        오래된 이메일 로그 삭제
        
        Args:
            days: 보관 일수
        """
        try:
            from app.models.models import EmailLog
            
            cutoff = datetime.now(KST) - timedelta(days=days)
            deleted = EmailLog.query.filter(EmailLog.sent_at < cutoff).delete()
            db.session.commit()
            
            if deleted:
                logger.info(f"Deleted {deleted} old email logs")
                
        except Exception as e:
            logger.error(f"Error cleaning email logs: {e}")
            db.session.rollback()

    def _cleanup_crawl_logs(self, days: int = 90) -> None:
        """
        오래된 크롤링 로그 삭제
        
        Args:
            days: 보관 일수
        """
        try:
            cutoff = datetime.now(KST) - timedelta(days=days)
            deleted = CrawlLog.query.filter(CrawlLog.crawled_at < cutoff).delete()
            db.session.commit()
            
            if deleted:
                logger.info(f"Deleted {deleted} old crawl logs")
                
        except Exception as e:
            logger.error(f"Error cleaning crawl logs: {e}")
            db.session.rollback()

    # ===== 수동 트리거 메서드 =====

    def trigger_crawl_now(self) -> bool:
        """
        크롤링 작업 즉시 실행
        
        Returns:
            성공 여부
        """
        try:
            if SchedulerService._scheduler:
                SchedulerService._scheduler.add_job(
                    func=self._run_crawl_job,
                    trigger='date',  # 즉시 실행
                    id='crawl_job_manual',
                    replace_existing=True
                )
                logger.info("Manual crawl job triggered")
                return True
        except Exception as e:
            logger.error(f"Failed to trigger crawl: {e}")
        return False

    def trigger_email_now(self, user_id: Optional[int] = None) -> bool:
        """
        이메일 발송 즉시 실행
        
        Args:
            user_id: 특정 사용자 ID (None이면 전체)
            
        Returns:
            성공 여부
        """
        try:
            if SchedulerService._app is None:
                return False
                
            with SchedulerService._app.app_context():
                from app.services.email_sender import EmailSender
                from app.services.news_storage import NewsStorageService
                
                email_sender = EmailSender()
                storage = NewsStorageService()
                
                if user_id:
                    # 특정 사용자
                    user = User.query.get(user_id)
                    if not user:
                        return False
                    
                    setting = UserSetting.query.filter_by(user_id=user_id).first()
                    users_to_notify = [(user, setting)]
                else:
                    # 알림 활성화된 모든 사용자
                    users_to_notify = db.session.query(User, UserSetting).join(
                        UserSetting,
                        User.id == UserSetting.user_id
                    ).filter(
                        UserSetting.is_notification_enabled == True
                    ).all()

                for user, setting in users_to_notify:
                    user_stocks = UserStock.query.filter_by(
                        user_id=user.id
                    ).all()
                    
                    tickers = [stock.ticker_symbol for stock in user_stocks]
                    language = setting.language if setting else 'ko'
                    
                    news_by_stock = {}
                    for ticker in tickers:
                        news_list = storage.get_recent_news(ticker, hours=24)  # 최근 24시간
                        if news_list:
                            news_by_stock[ticker] = news_list
                    
                    if news_by_stock:
                        email_sender.send_stock_report(user, news_by_stock, language)
                    else:
                        email_sender.send_no_news_notification(user, language)

                logger.info("Manual email job completed")
                return True
                
        except Exception as e:
            logger.error(f"Failed to trigger email: {e}")
        return False

    # ===== 상태 조회 =====

    def get_jobs_status(self) -> List[Dict[str, Any]]:
        """
        등록된 작업 상태 조회
        
        Returns:
            작업 목록
        """
        jobs = []
        if SchedulerService._scheduler:
            for job in SchedulerService._scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': str(job.next_run_time) if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs

    def is_running(self) -> bool:
        """스케줄러 실행 여부"""
        if SchedulerService._scheduler:
            return SchedulerService._scheduler.running
        return False

    def pause_job(self, job_id: str) -> bool:
        """
        작업 일시 중지
        
        Args:
            job_id: 작업 ID
            
        Returns:
            성공 여부
        """
        try:
            if SchedulerService._scheduler:
                SchedulerService._scheduler.pause_job(job_id)
                logger.info(f"Paused job: {job_id}")
                return True
        except JobLookupError:
            logger.error(f"Job not found: {job_id}")
        except Exception as e:
            logger.error(f"Failed to pause job: {e}")
        return False

    def resume_job(self, job_id: str) -> bool:
        """
        작업 재개
        
        Args:
            job_id: 작업 ID
            
        Returns:
            성공 여부
        """
        try:
            if SchedulerService._scheduler:
                SchedulerService._scheduler.resume_job(job_id)
                logger.info(f"Resumed job: {job_id}")
                return True
        except JobLookupError:
            logger.error(f"Job not found: {job_id}")
        except Exception as e:
            logger.error(f"Failed to resume job: {e}")
        return False

    def send_email_now(self) -> Dict[str, Any]:
        """
        모든 활성 사용자에게 즉시 이메일 발송 (수동 트리거용)
        시간 체크 없이 알림이 활성화된 모든 사용자에게 발송
        
        Returns:
            발송 결과 딕셔너리
        """
        logger.info("Starting manual email send (all active users)...")
        
        if SchedulerService._app is None:
            logger.error("Flask app not available")
            return {'success': False, 'error': 'Flask app not available'}

        sent_count = 0
        failed_count = 0
        
        with SchedulerService._app.app_context():
            try:
                from app.services.email_sender import EmailSender
                from app.services.news_storage import NewsStorageService
                
                email_sender = EmailSender()
                storage = NewsStorageService()
                
                # 알림이 활성화된 모든 사용자 조회 (시간 무관)
                users_to_notify = db.session.query(User, UserSetting).join(
                    UserSetting,
                    User.id == UserSetting.user_id
                ).filter(
                    User.is_active == True,
                    UserSetting.is_notification_enabled == True
                ).all()
                
                if not users_to_notify:
                    logger.info("No active users with notifications enabled")
                    return {
                        'success': True,
                        'message': '알림이 활성화된 사용자가 없습니다.',
                        'sent': 0,
                        'failed': 0
                    }

                logger.info(f"Found {len(users_to_notify)} users to notify")
                
                for user, setting in users_to_notify:
                    try:
                        # 사용자의 관심 종목 조회
                        user_stocks = UserStock.query.filter_by(
                            user_id=user.id
                        ).all()
                        
                        if not user_stocks:
                            logger.info(f"No stocks for user {user.username}")
                            continue
                        
                        tickers = [stock.ticker_symbol for stock in user_stocks]
                        
                        # 최근 48시간 뉴스 조회
                        news_by_stock = {}
                        for ticker in tickers:
                            news_list = storage.get_recent_news(ticker, hours=48)
                            if news_list:
                                news_by_stock[ticker] = news_list
                        
                        # 이메일 발송
                        language = setting.language if setting else 'ko'
                        
                        if news_by_stock:
                            success, error = email_sender.send_stock_report(
                                user=user,
                                news_by_stock=news_by_stock,
                                language=language
                            )
                        else:
                            success, error = email_sender.send_no_news_notification(
                                user=user,
                                language=language
                            )
                        
                        if success:
                            sent_count += 1
                            logger.info(f"Email sent to {user.email}")
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to send email to {user.email}: {error}")

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error sending email to {user.username}: {e}")
                        continue

                logger.info(f"Manual email send completed: {sent_count} sent, {failed_count} failed")
                
                return {
                    'success': True,
                    'message': f'{sent_count}명에게 이메일을 발송했습니다.',
                    'sent': sent_count,
                    'failed': failed_count
                }

            except Exception as e:
                logger.error(f"Manual email send failed: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }

    def shutdown(self) -> None:
        """스케줄러 종료"""
        if SchedulerService._scheduler and SchedulerService._scheduler.running:
            SchedulerService._scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown completed")


# 싱글톤 인스턴스
scheduler_service = SchedulerService()


def init_scheduler(app: Flask) -> None:
    """
    Flask 앱 컨텍스트에서 스케줄러 초기화
    
    Args:
        app: Flask 애플리케이션
    """
    scheduler_service.init_app(app)
