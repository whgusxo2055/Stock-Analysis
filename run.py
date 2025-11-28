"""
Flask 애플리케이션 실행 스크립트
"""
import os
from app import create_app
from app.utils.config import Config

# 환경 변수 검증
Config.validate_config()

# Flask 앱 생성
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # 개발 서버 실행 (운영에서는 Gunicorn 사용)
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5001)),
        debug=Config.DEBUG
    )
