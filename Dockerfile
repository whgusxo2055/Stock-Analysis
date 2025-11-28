FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 필요한 디렉토리 생성
RUN mkdir -p /app/data /app/logs /app/flask_session

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

# 포트 노출
EXPOSE 5000

# Gunicorn으로 실행 (스케줄러 중복 방지를 위해 preload 사용)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "--preload", "--access-logfile", "-", "--error-logfile", "-", "run:app"]
