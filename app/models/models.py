"""
SQLAlchemy 데이터베이스 모델
SRS Section 7.1 참조
"""
from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """사용자 테이블 (SRS 7.1.1)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    settings = db.relationship('UserSetting', back_populates='user', uselist=False, cascade='all, delete-orphan')
    stocks = db.relationship('UserStock', back_populates='user', cascade='all, delete-orphan')
    email_logs = db.relationship('EmailLog', back_populates='user', cascade='all, delete-orphan')
    
    def set_password(self, password: str):
        """비밀번호 해싱"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password: str) -> bool:
        """비밀번호 검증"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserSetting(db.Model):
    """사용자 설정 테이블 (SRS 7.1.2)"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    language = db.Column(db.String(10), default='ko', nullable=False)  # ko, en, es, ja
    notification_time = db.Column(db.Time, nullable=False)  # 예: 09:00:00
    is_notification_enabled = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 관계
    user = db.relationship('User', back_populates='settings')
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'language': self.language,
            'notification_time': self.notification_time.strftime('%H:%M:%S') if self.notification_time else None,
            'is_notification_enabled': self.is_notification_enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<UserSetting user_id={self.user_id}>'


class StockMaster(db.Model):
    """종목 마스터 데이터 테이블 (SRS 7.1.3)"""
    __tablename__ = 'stock_master'
    
    ticker_symbol = db.Column(db.String(10), primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    exchange = db.Column(db.String(50))  # NYSE, NASDAQ, etc.
    sector = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    user_stocks = db.relationship('UserStock', back_populates='stock')
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'ticker_symbol': self.ticker_symbol,
            'company_name': self.company_name,
            'exchange': self.exchange,
            'sector': self.sector,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<StockMaster {self.ticker_symbol} - {self.company_name}>'


class UserStock(db.Model):
    """사용자 관심 종목 테이블 (SRS 7.1.4)"""
    __tablename__ = 'user_stocks'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'ticker_symbol', name='unique_user_stock'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ticker_symbol = db.Column(db.String(10), db.ForeignKey('stock_master.ticker_symbol'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    user = db.relationship('User', back_populates='stocks')
    stock = db.relationship('StockMaster', back_populates='user_stocks')
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'ticker_symbol': self.ticker_symbol,
            'company_name': self.stock.company_name if self.stock else None,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<UserStock user_id={self.user_id} ticker={self.ticker_symbol}>'


class EmailLog(db.Model):
    """이메일 발송 로그 테이블 (SRS 7.1.5)"""
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, failed
    error_message = db.Column(db.Text)
    news_count = db.Column(db.Integer, default=0, nullable=False)
    
    # 관계
    user = db.relationship('User', back_populates='email_logs')
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sent_at': self.sent_at.isoformat(),
            'status': self.status,
            'error_message': self.error_message,
            'news_count': self.news_count
        }
    
    def __repr__(self):
        return f'<EmailLog user_id={self.user_id} status={self.status}>'


class CrawlLog(db.Model):
    """크롤링 로그 테이블 (SRS 7.1.6)"""
    __tablename__ = 'crawl_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticker_symbol = db.Column(db.String(10))
    crawled_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, failed
    news_count = db.Column(db.Integer, default=0, nullable=False)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'id': self.id,
            'ticker_symbol': self.ticker_symbol,
            'crawled_at': self.crawled_at.isoformat(),
            'status': self.status,
            'news_count': self.news_count,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        return f'<CrawlLog ticker={self.ticker_symbol} status={self.status}>'
