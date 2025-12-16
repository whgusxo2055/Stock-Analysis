"""
이메일 발송 서비스
- Gmail SMTP를 통한 HTML 보고서 발송
- SRS FR-029~038 구현
"""

import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple

from flask import render_template

from app.utils.config import Config
from app.models.models import User, UserSetting, EmailLog, KST
from app.extensions import db

logger = logging.getLogger(__name__)


class EmailSender:
    """
    이메일 발송 엔진
    Gmail SMTP를 사용한 HTML 보고서 발송
    """

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            smtp_server: SMTP 서버 주소
            smtp_port: SMTP 포트
            username: Gmail 사용자명
            password: Gmail 앱 비밀번호
        """
        self.smtp_server = smtp_server or Config.GMAIL_SMTP_SERVER
        self.smtp_port = smtp_port or Config.GMAIL_SMTP_PORT
        self.username = username or Config.GMAIL_USERNAME
        self.password = password or Config.GMAIL_APP_PASSWORD
        
        if not self.username or not self.password:
            logger.warning("Gmail credentials not configured")
        else:
            logger.info(f"EmailSender initialized with {self.username}")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        max_retries: int = 3,
        retry_delay: int = 60
    ) -> Tuple[bool, Optional[str]]:
        """
        이메일 발송 (재시도 로직 포함)
        
        Args:
            to_email: 수신자 이메일
            subject: 메일 제목
            html_content: HTML 본문
            max_retries: 최대 재시도 횟수 (FR-037)
            retry_delay: 재시도 간격 (초)
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        if not self.username or not self.password:
            return False, "Gmail credentials not configured"
        
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Sending email attempt {attempt}/{max_retries} to {to_email}"
                )
                
                # 메시지 생성
                message = MIMEMultipart('alternative')
                message['Subject'] = subject
                message['From'] = self.username
                message['To'] = to_email
                
                # HTML 파트 추가
                html_part = MIMEText(html_content, 'html', 'utf-8')
                message.attach(html_part)
                
                # SMTP 연결 및 발송
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.username, self.password)
                    server.sendmail(
                        self.username,
                        to_email,
                        message.as_string()
                    )
                
                logger.info(f"Email sent successfully to {to_email}")
                return True, None
                
            except smtplib.SMTPAuthenticationError as e:
                last_error = f"SMTP Authentication failed: {str(e)}"
                logger.error(last_error)
                # 인증 오류는 재시도 의미 없음
                return False, last_error
                
            except smtplib.SMTPRecipientsRefused as e:
                last_error = f"Recipient refused: {str(e)}"
                logger.error(last_error)
                return False, last_error
                
            except smtplib.SMTPException as e:
                last_error = f"SMTP error: {str(e)}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.warning(f"Attempt {attempt} failed: {last_error}")
            
            # 재시도 대기
            if attempt < max_retries:
                logger.info(f"Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
        
        logger.error(f"All email attempts failed for {to_email}: {last_error}")
        return False, last_error

    def send_stock_report(
        self,
        user: User,
        news_by_stock: Dict[str, List[Dict]],
        language: str = 'ko'
    ) -> Tuple[bool, Optional[str]]:
        """
        주식 뉴스 보고서 이메일 발송
        
        Args:
            user: 사용자 객체
            news_by_stock: 종목별 뉴스 리스트
                {
                    'TSLA': [{'title': ..., 'summary': {...}, 'sentiment': {...}}, ...],
                    'AAPL': [...]
                }
            language: 요약 언어 (ko/en/es/ja)
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        try:
            # 현재 날짜
            today = datetime.now(KST).strftime('%Y-%m-%d')
            
            # 이메일 제목 (FR-033)
            subject = f"[Stock Report] {today} - {user.username}님의 관심 종목 분석"
            
            # 통계 계산
            total_news = sum(len(news_list) for news_list in news_by_stock.values())
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for news_list in news_by_stock.values():
                for news in news_list:
                    sentiment = news.get('sentiment', {})
                    classification = sentiment.get('classification', 'neutral').lower()
                    
                    if classification == 'positive':
                        positive_count += 1
                    elif classification == 'negative':
                        negative_count += 1
                    else:
                        neutral_count += 1
            
            # HTML 렌더링
            html_content = self._render_report_template(
                user=user,
                news_by_stock=news_by_stock,
                language=language,
                date=today,
                total_news=total_news,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count
            )
            
            # 발송
            success, error = self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content
            )
            
            # 로그 기록 (FR-038)
            self._save_email_log(
                user_id=user.id,
                status='success' if success else 'failed',
                news_count=total_news,
                error_message=error
            )
            
            return success, error
            
        except Exception as e:
            error_msg = f"Failed to send report: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            self._save_email_log(
                user_id=user.id,
                status='failed',
                news_count=0,
                error_message=error_msg
            )
            
            return False, error_msg

    def _render_report_template(
        self,
        user: User,
        news_by_stock: Dict[str, List[Dict]],
        language: str,
        date: str,
        total_news: int,
        positive_count: int,
        negative_count: int,
        neutral_count: int
    ) -> str:
        """
        HTML 보고서 템플릿 렌더링
        
        Args:
            user: 사용자 객체
            news_by_stock: 종목별 뉴스
            language: 언어 코드
            date: 날짜 문자열
            total_news: 총 뉴스 수
            positive_count: 호재 수
            negative_count: 악재 수
            neutral_count: 중립 수
        
        Returns:
            렌더링된 HTML 문자열
        """
        # Flask 앱 컨텍스트 내에서 render_template 사용
        try:
            html = render_template(
                'email/report.html',
                user=user,
                news_by_stock=news_by_stock,
                language=language,
                date=date,
                total_news=total_news,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                dashboard_url=Config.get('DASHBOARD_URL', 'http://localhost:5001')
            )
            return html
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            # 폴백: 간단한 HTML 생성
            return self._generate_fallback_html(
                user, news_by_stock, language, date,
                total_news, positive_count, negative_count, neutral_count
            )

    def _generate_fallback_html(
        self,
        user: User,
        news_by_stock: Dict[str, List[Dict]],
        language: str,
        date: str,
        total_news: int,
        positive_count: int,
        negative_count: int,
        neutral_count: int
    ) -> str:
        """
        템플릿 렌더링 실패 시 폴백 HTML 생성
        """
        stocks_html = ""
        
        for ticker, news_list in news_by_stock.items():
            news_items_html = ""
            for news in news_list:
                sentiment = news.get('sentiment', {})
                classification = sentiment.get('classification', 'Neutral')
                score = sentiment.get('score', 0)
                
                # 색상 설정 (FR-034)
                if classification == 'Positive':
                    color = '#34a853'
                    label = '호재'
                elif classification == 'Negative':
                    color = '#ea4335'
                    label = '악재'
                else:
                    color = '#999'
                    label = '중립'
                
                # 언어별 요약 가져오기
                summary = news.get('summary', {})
                if isinstance(summary, dict):
                    summary_text = summary.get(language, summary.get('ko', '요약 없음'))
                else:
                    summary_text = str(summary)
                
                news_items_html += f"""
                <div style="padding: 15px; border-bottom: 1px solid #eee;">
                    <h3 style="margin: 0 0 10px 0; font-size: 16px;">{news.get('title', 'N/A')}</h3>
                    <p style="color: #666; margin: 0 0 10px 0;">{summary_text}</p>
                    <span style="display: inline-block; padding: 5px 10px; border-radius: 4px; background: {color}20; color: {color};">
                        {label} ({score:+d})
                    </span>
                    <a href="{news.get('url', '#')}" style="float: right; color: #1a73e8;">원문 보기 →</a>
                    <div style="clear: both;"></div>
                </div>
                """
            
            stocks_html += f"""
            <div style="margin: 20px 0; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                <h2 style="background: #f5f5f5; margin: 0; padding: 15px; font-size: 18px;">{ticker}</h2>
                {news_items_html if news_items_html else '<p style="padding: 15px; color: #999;">새로운 뉴스가 없습니다.</p>'}
            </div>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
    <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0;">📊 Stock Analysis Report</h1>
        <p style="margin: 10px 0 0 0;">{user.username}님의 관심 종목 분석 - {date}</p>
    </div>
    
    {stocks_html if stocks_html else '<p style="padding: 20px; text-align: center; color: #999;">새로운 뉴스가 없습니다.</p>'}
    
    <div style="text-align: center; padding: 20px; color: #666; background: #f5f5f5; border-radius: 0 0 8px 8px;">
        <p style="margin: 0;">총 {total_news}건 | 호재 {positive_count}건 | 악재 {negative_count}건 | 중립 {neutral_count}건</p>
    </div>
</body>
</html>
        """

    def _save_email_log(
        self,
        user_id: int,
        status: str,
        news_count: int,
        error_message: Optional[str]
    ) -> None:
        """
        이메일 발송 로그 저장 (FR-038)
        
        Args:
            user_id: 사용자 ID
            status: 발송 상태 (success/failed)
            news_count: 발송된 뉴스 수
            error_message: 에러 메시지
        """
        try:
            log = EmailLog(
                user_id=user_id,
                status=status,
                news_count=news_count,
                error_message=error_message,
                sent_at=datetime.now(KST)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.debug(f"Email log saved: user_id={user_id}, status={status}")
            
        except Exception as e:
            logger.error(f"Failed to save email log: {e}")
            db.session.rollback()

    def send_no_news_notification(
        self,
        user: User,
        language: str = 'ko'
    ) -> Tuple[bool, Optional[str]]:
        """
        새 뉴스 없음 알림 발송 (FR-036)
        
        Args:
            user: 사용자 객체
            language: 언어 코드
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        today = datetime.now(KST).strftime('%Y-%m-%d')
        subject = f"[Stock Report] {today} - 새로운 뉴스가 없습니다"
        
        messages = {
            'ko': '관심 종목에 대한 새로운 뉴스가 없습니다.',
            'en': 'There are no new news for your watchlist.',
            'es': 'No hay nuevas noticias para su lista de seguimiento.',
            'ja': 'ウォッチリストに関する新しいニュースはありません。'
        }
        
        message = messages.get(language, messages['ko'])
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="margin: 0;">📊 Stock Analysis Report</h1>
        <p style="margin: 10px 0 0 0;">{today}</p>
    </div>
    
    <div style="padding: 40px 20px; text-align: center; background: #f9f9f9;">
        <p style="font-size: 18px; color: #666; margin: 0;">
            📭 {message}
        </p>
    </div>
    
    <div style="text-align: center; padding: 20px; color: #999; font-size: 14px;">
        <p>다음 보고서에서 만나요!</p>
    </div>
</body>
</html>
        """
        
        success, error = self.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )
        
        self._save_email_log(
            user_id=user.id,
            status='success' if success else 'failed',
            news_count=0,
            error_message=error
        )
        
        return success, error

    def send_test_email(self, user: User) -> Tuple[bool, Optional[str]]:
        """
        테스트 이메일 발송 (FR-054)
        
        Args:
            user: 사용자 객체
        
        Returns:
            (성공 여부, 에러 메시지)
        """
        subject = "[Stock Analysis] 테스트 이메일"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #34a853; color: white; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="margin: 0;">✅ 테스트 이메일</h1>
    </div>
    
    <div style="padding: 30px 20px; text-align: center; background: #f9f9f9;">
        <p style="font-size: 16px; color: #333; margin: 0 0 20px 0;">
            안녕하세요, <strong>{user.username}</strong>님!
        </p>
        <p style="font-size: 16px; color: #666; margin: 0;">
            이메일 설정이 정상적으로 완료되었습니다. 🎉
        </p>
    </div>
    
    <div style="text-align: center; padding: 20px; color: #999; font-size: 14px;">
            <p>발송 시각: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Stock Analysis Service</p>
    </div>
</body>
</html>
        """
        
        return self.send_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )


# 싱글톤 인스턴스
_email_sender: Optional[EmailSender] = None


def get_email_sender() -> EmailSender:
    """
    EmailSender 싱글톤 인스턴스 반환
    
    Returns:
        EmailSender 인스턴스
    """
    global _email_sender
    
    if _email_sender is None:
        _email_sender = EmailSender()
    
    return _email_sender
