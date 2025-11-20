"""
데이터베이스 초기화 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app, db
from app.models.models import User, UserSetting, StockMaster, UserStock, EmailLog, CrawlLog
from datetime import time


def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    app = create_app()
    
    with app.app_context():
        # 모든 테이블 생성
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully!")
        
        # 초기 데이터 생성 (선택적)
        if User.query.count() == 0:
            print("\nCreating initial data...")
            create_initial_data()
            print("✓ Initial data created successfully!")
        else:
            print("\nDatabase already has data. Skipping initial data creation.")


def create_initial_data():
    """초기 데이터 생성"""
    # 관리자 사용자 생성
    admin = User(
        username='admin',
        email='admin@stockanalysis.com',
        is_admin=True
    )
    admin.set_password('admin123')  # 실제 운영에서는 변경 필요
    db.session.add(admin)
    
    # 관리자 설정 생성
    admin_setting = UserSetting(
        user_id=1,
        language='ko',
        notification_time=time(9, 0, 0),
        is_notification_enabled=True
    )
    db.session.add(admin_setting)
    
    # 샘플 종목 마스터 데이터
    stocks_data = [
        {'ticker_symbol': 'TSLA', 'company_name': 'Tesla Inc.', 'exchange': 'NASDAQ', 'sector': 'Automotive'},
        {'ticker_symbol': 'AAPL', 'company_name': 'Apple Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
        {'ticker_symbol': 'MSFT', 'company_name': 'Microsoft Corporation', 'exchange': 'NASDAQ', 'sector': 'Technology'},
        {'ticker_symbol': 'GOOGL', 'company_name': 'Alphabet Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
        {'ticker_symbol': 'AMZN', 'company_name': 'Amazon.com Inc.', 'exchange': 'NASDAQ', 'sector': 'E-commerce'},
        {'ticker_symbol': 'NVDA', 'company_name': 'NVIDIA Corporation', 'exchange': 'NASDAQ', 'sector': 'Technology'},
        {'ticker_symbol': '^GSPC', 'company_name': 'S&P 500 Index', 'exchange': 'INDEX', 'sector': 'Index'},
        {'ticker_symbol': 'META', 'company_name': 'Meta Platforms Inc.', 'exchange': 'NASDAQ', 'sector': 'Technology'},
        {'ticker_symbol': 'JPM', 'company_name': 'JPMorgan Chase & Co.', 'exchange': 'NYSE', 'sector': 'Finance'},
        {'ticker_symbol': 'V', 'company_name': 'Visa Inc.', 'exchange': 'NYSE', 'sector': 'Finance'},
    ]
    
    for stock_data in stocks_data:
        stock = StockMaster(**stock_data)
        db.session.add(stock)
    
    # 커밋
    db.session.commit()
    
    print(f"  ✓ Created admin user: admin / admin123")
    print(f"  ✓ Created {len(stocks_data)} sample stocks")


def drop_all_tables():
    """모든 테이블 삭제 (주의: 데이터 손실)"""
    app = create_app()
    
    with app.app_context():
        print("WARNING: This will delete all database tables and data!")
        confirm = input("Type 'yes' to confirm: ")
        
        if confirm.lower() == 'yes':
            db.drop_all()
            print("✓ All tables dropped successfully!")
        else:
            print("Operation cancelled.")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Database management script')
    parser.add_argument('action', choices=['init', 'drop'], help='Action to perform')
    args = parser.parse_args()
    
    if args.action == 'init':
        init_db()
    elif args.action == 'drop':
        drop_all_tables()
