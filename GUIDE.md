# Docker 배포/실행 가이드

## 사전 준비
- `.env`를 `.env.example`에서 복사 후 필수 값 설정: `OPENAI_API_KEY`, `GMAIL_USERNAME`, `GMAIL_APP_PASSWORD`, `FLASK_SECRET_KEY`.
- ElasticSearch 데이터는 외부 볼륨 `stockanalysis_es-data`에 저장됩니다. 기존 데이터를 유지하려면 동일한 볼륨 이름을 사용하세요.

## 빌드 및 실행
```bash
# 이미지 빌드
docker-compose build

# 컨테이너 기동 (백그라운드)
docker-compose up -d
```

## 상태 확인 및 로그
```bash
# 컨테이너 상태
docker-compose ps

# Flask 앱 로그 tail
docker-compose logs -f flask-app

# ElasticSearch 상태 확인
docker-compose exec elasticsearch curl -s http://localhost:9200/_cluster/health
```

## 종료 및 정리
```bash
# 컨테이너 중지
docker-compose down

# 로그/데이터를 유지한 채 재기동 가능 (외부 볼륨 사용)
```

## 문제 해결 팁
- 볼륨 연결: `docker volume ls`로 `stockanalysis_es-data` 존재 확인 후 `docker-compose up -d`.
- 환경 변수 변경 후: `docker-compose up -d --build`로 재빌드/재기동.
- 크롤러/이메일 시간이 한국표준시(KST)로 저장/표시됩니다.
