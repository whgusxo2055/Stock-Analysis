# Stock Analysis Service

미국 주식 뉴스 자동 수집 및 분석 웹서비스

## 📋 프로젝트 개요

이 프로젝트는 사용자가 지정한 미국 주식 종목의 뉴스를 자동으로 수집하고, AI를 활용하여 분석한 후 이메일로 전달하는 내부 서비스입니다.

### 주요 기능
- ✅ 사용자 인증 및 관리
- ✅ 관심 종목 설정 (티커 심볼 기반)
- ✅ Investing.com 뉴스 자동 크롤링 (3시간 주기)
- ✅ ChatGPT API 기반 다국어 요약 및 호재/악재 분석
- ✅ ElasticSearch를 통한 뉴스 저장 및 검색
- ✅ 사용자 맞춤 HTML 이메일 보고서 발송
- ✅ 웹 대시보드 및 통계 기능

## 🏗️ 기술 스택

### 백엔드
- Python 3.9+
- Flask 2.3.3
- SQLAlchemy + SQLite
- ElasticSearch 7.17.9
- APScheduler

### 크롤링 & 분석
- Selenium
- OpenAI ChatGPT API

### 인프라
- Docker & Docker Compose
- Gunicorn (WSGI)

## 📁 프로젝트 구조

```
stockAnalysis/
├── app/
│   ├── __init__.py          # Flask 앱 팩토리
│   ├── models/              # SQLAlchemy 모델
│   │   └── models.py
│   ├── routes/              # Flask 라우트 (추후 구현)
│   ├── services/            # 비즈니스 로직 (크롤러, 분석, 메일)
│   ├── templates/           # Jinja2 템플릿
│   ├── static/              # CSS, JS, 이미지
│   └── utils/               # 유틸리티 함수
│       ├── config.py        # 환경 설정
│       ├── elasticsearch_client.py
│       └── logger.py        # 로깅 시스템
├── data/                    # SQLite DB 파일
├── logs/                    # 로그 파일
├── scripts/                 # 관리 스크립트
│   └── init_db.py          # DB 초기화
├── tests/                   # 테스트 코드
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py                   # 앱 실행 스크립트
├── .env.example            # 환경 변수 예시
└── README.md
```

## 🚀 설치 및 실행

### 1. 사전 요구사항
- Docker & Docker Compose
- Python 3.9+ (로컬 개발 시)

### 2. 환경 변수 설정

`.env` 파일을 생성하고 필요한 값을 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 편집:
```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=sk-your-actual-api-key-here

# Gmail 설정 (필수)
GMAIL_USERNAME=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password

# Flask Secret Key (운영 환경에서 변경 필요)
FLASK_SECRET_KEY=your-secret-key-here
```

### 3. Docker로 실행 (권장)

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

서비스가 실행되면:
- Flask 앱: http://localhost:5000
- ElasticSearch: http://localhost:9200

### 4. 로컬 개발 환경 실행

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python scripts/init_db.py init

# 개발 서버 실행
python run.py
```

## 🗄️ 데이터베이스 초기화

```bash
# Docker 환경에서
docker-compose exec flask-app python scripts/init_db.py init

# 로컬 환경에서
python scripts/init_db.py init
```

초기 데이터:
- 관리자 계정: `admin` / `admin123`
- 샘플 종목: TSLA, AAPL, MSFT, GOOGL, AMZN 등

## 📊 ElasticSearch 설정

### 1. 인덱스 생성

```bash
# Docker 환경에서
docker-compose up -d elasticsearch
sleep 15  # ES 시작 대기

# 인덱스 생성
source venv/bin/activate
python scripts/setup_es_index.py create

# 인덱스 정보 확인
python scripts/setup_es_index.py info
```

### 2. ILM 정책 설정

2년(730일) 데이터 보관 정책 적용:

```bash
# ILM 정책 생성 및 적용
python scripts/setup_ilm.py setup

# 정책 상태 확인
python scripts/setup_ilm.py status
```

ILM 정책 구조:
- **Hot 단계**: 0일~ (30일 또는 50GB마다 롤오버)
- **Warm 단계**: 90일~ (샤드 축소, 우선순위 낮춤)
- **Delete 단계**: 730일(2년) 후 자동 삭제

### 3. 뉴스 저장 어댑터 사용

```python
from app.services import get_news_storage

storage = get_news_storage()

# 단일 뉴스 저장
news = {
    "news_id": "unique_id",
    "ticker_symbol": "TSLA",
    "title": "Tesla stock rises",
    "content": "...",
    "published_date": "2024-01-15T10:00:00"
}
storage.save_news(news)

# 벌크 저장 (크롤러용)
news_list = [...]
result = storage.bulk_save_news(news_list)

# 검색
results = storage.search_news(ticker_symbol="TSLA", size=10)

# 통계
stats = storage.get_statistics("TSLA", days=7)
```

## 🧪 테스트

### Phase 1 테스트

```bash
# Phase 1 검증 (기반 인프라)
pytest test_phase1.py -v

# 6개 테스트: imports, config, logging, app, database, API
```

### Phase 2 테스트

```bash
# ElasticSearch 인덱스 매핑 테스트
pytest tests/test_es_mapping.py -v  # 7개 테스트

# ILM 정책 테스트
pytest tests/test_ilm.py -v  # 5개 테스트

# 뉴스 저장 어댑터 단위 테스트
pytest tests/test_news_storage.py -v  # 13개 테스트

# Phase 2 통합 테스트
pytest tests/test_phase2_integration.py -v  # 4개 테스트
```

### 모든 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app --cov-report=html

# 특정 디렉토리 테스트
pytest tests/ -v
```

## 🔍 API 엔드포인트

### 기본
- `GET /` - API 정보
- `GET /health` - 헬스 체크

### 인증 (Phase 5에서 구현 예정)
- `POST /api/auth/login` - 로그인
- `POST /api/auth/logout` - 로그아웃

### 사용자 관리 (Phase 5에서 구현 예정)
- `GET /api/user/profile` - 내 정보 조회
- `PUT /api/user/profile` - 내 정보 수정

### 종목 관리 (Phase 5에서 구현 예정)
- `GET /api/stocks/my-stocks` - 관심 종목 조회
- `POST /api/stocks/add` - 관심 종목 추가

## 📝 로그 파일

로그는 `logs/` 디렉토리에 저장됩니다:

- `app.log` - 전체 애플리케이션 로그
- `crawler.log` - 크롤링 관련 로그
- `email.log` - 이메일 발송 로그
- `error.log` - 에러만 모은 로그

## 🔒 보안 고려사항

- 비밀번호는 PBKDF2-SHA256으로 해싱
- 세션 기반 인증
- 환경 변수로 민감 정보 관리
- `.gitignore`에 `.env` 파일 포함

## 📅 개발 로드맵

### Phase 1: 기반 구조 (완료 ✅)
- [x] Flask 앱 팩토리 패턴
- [x] SQLite 데이터베이스 스키마
- [x] ElasticSearch 연동
- [x] Docker 환경 구성
- [x] 로깅 시스템

### Phase 2: 데이터 & 인덱스 (완료 ✅)
- [x] ElasticSearch 인덱스 매핑 (SRS 7.2.1)
- [x] ILM 정책 구현 (2년 보관, SRS 3.5.3)
- [x] 뉴스 저장 어댑터 (NewsStorageAdapter)
- [x] 단위 테스트 (13개) 및 통합 테스트 (4개)

### Phase 3: 크롤러 MVP
- [ ] Selenium 설정
- [ ] Investing.com 파싱

### Phase 4: 분석 & 저장 파이프라인
- [ ] ChatGPT 프롬프트
- [ ] 다국어 요약 및 감성 분석

### Phase 5: 웹 UI / API
- [ ] 인증, 종목 관리
- [ ] 뉴스 조회, 통계

### Phase 6: 메일 & 스케줄러
- [ ] HTML 메일 템플릿
- [ ] APScheduler 작업

### Phase 7: 테스트/배포
- [ ] 단위 및 통합 테스트
- [ ] 서버 배포

## 🤝 기여

내부 프로젝트이므로 외부 기여는 받지 않습니다.

## 📄 라이선스

내부 사용 전용 (Proprietary)

## 📞 문의

프로젝트 관련 문의는 팀 내부 채널을 이용해주세요.

---

**현재 상태**: Phase 2 완료 ✅  
**다음 단계**: Phase 3 (크롤러 MVP)  
**마지막 업데이트**: 2025-01-20
