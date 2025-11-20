# Software Requirements Specification (SRS)
## 미국 주식 분석 웹서비스

**문서 버전**: 1.0  
**작성일**: 2025년 11월 20일  
**프로젝트명**: Stock Analysis Service

---

## 1. 서론

### 1.1 목적
본 문서는 미국 주식 뉴스 자동 수집 및 분석 웹서비스의 요구사항을 정의한다. 이 시스템은 사용자가 지정한 종목의 뉴스를 자동으로 수집하고, AI를 활용하여 분석한 후 이메일로 전달하는 내부 서비스이다.

### 1.2 범위
- **대상 사용자**: 5인 이하의 내부 사용자
- **동시 사용자**: 최대 3명
- **배포 환경**: 클라우드 우분투 서버 (Docker 컨테이너)
- **보안 수준**: 기본 로그인 인증 (비밀번호 암호화), HTTPS 미적용

### 1.3 용어 정의
- **종목**: 미국 주식 시장의 개별 주식 또는 지수 (예: TSLA, S&P500)
- **호재/악재**: 주가에 긍정적/부정적 영향을 미칠 수 있는 뉴스
- **티커 심볼**: 주식 거래소에서 사용하는 종목 코드 (예: TSLA, AAPL)

---

## 2. 전체 시스템 개요

### 2.1 시스템 개요
사용자가 설정한 관심 종목에 대해 investing.com에서 뉴스를 자동 수집하고, ChatGPT API를 활용하여 다국어로 요약 및 호재/악재 분석을 수행한다. 분석 결과는 ElasticSearch에 저장되며, 사용자가 지정한 시각에 Gmail을 통해 HTML 형식의 보고서로 전달된다.

### 2.2 시스템 아키텍처

```
┌─────────────────┐
│   Web Browser   │ (사용자 인터페이스)
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Backend  │
├─────────────────┤
│ - API Server    │
│ - Scheduler     │
│ - Auth Module   │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    ▼         ▼        ▼        ▼
┌────────┐ ┌────┐ ┌─────────┐ ┌──────┐
│SQLite  │ │ES  │ │ChatGPT  │ │Gmail │
│(사용자)│ │7.0 │ │  API    │ │ SMTP │
└────────┘ └────┘ └─────────┘ └──────┘
                      ▲
                      │
                ┌─────┴──────┐
                │ Selenium/  │
                │Playwright  │
                │ (Crawler)  │
                └────────────┘
                      ▲
                      │
                ┌─────┴──────┐
                │investing.com│
                └────────────┘
```

### 2.3 주요 컴포넌트
1. **웹 인터페이스**: Flask 기반 웹 UI
2. **크롤링 엔진**: Selenium 또는 Playwright를 이용한 뉴스 수집
3. **분석 엔진**: ChatGPT API를 이용한 다국어 요약 및 호재/악재 분석
4. **데이터 저장소**: 
   - SQLite: 사용자 정보, 종목 설정
   - ElasticSearch 7.0.1: 뉴스 및 분석 결과
5. **스케줄러**: 뉴스 수집 및 메일 발송 스케줄 관리
6. **메일 발송**: Gmail SMTP를 통한 HTML 보고서 발송

---

## 3. 기능 요구사항

### 3.1 사용자 관리

#### 3.1.1 사용자 등록 (관리자 기능)
- **FR-001**: 관리자는 새로운 사용자를 수동으로 등록할 수 있다.
- **입력 정보**:
  - 사용자 ID (고유, 필수)
  - 이메일 주소 (필수)
  - 비밀번호 (필수, 암호화 저장)
  - 사용자 이름 (필수)
- **비밀번호 암호화**: bcrypt 또는 werkzeug.security 사용

#### 3.1.2 로그인 / 로그아웃
- **FR-002**: 사용자는 ID와 비밀번호로 로그인할 수 있다.
- **FR-003**: 로그인 시 세션을 생성하여 사용자를 식별한다. (Flask Session 사용)
- **FR-004**: 사용자는 로그아웃하여 세션을 종료할 수 있다.
- **보안**: JWT 같은 고급 인증은 미적용, 기본 세션 기반 인증 사용

#### 3.1.3 사용자 정보 수정
- **FR-005**: 사용자는 자신의 정보를 수정할 수 있다.
  - 비밀번호 변경
  - 이메일 주소 변경

### 3.2 종목 관리

#### 3.2.1 종목 지정 방식
- **FR-006**: 티커 심볼 + 회사명 매핑 기반 종목 지정
  - 사용자 입력: 티커 심볼 (예: TSLA, AAPL, ^GSPC)
  - 시스템 동작: 입력된 티커 심볼을 내부 매핑 테이블의 회사명과 매칭하여 관리
  - 검색 방식: investing.com에서 "티커심볼 + 회사명" 조합으로 정확도 높은 검색 수행

#### 3.2.2 관심 종목 추가/삭제
- **FR-007**: 사용자는 관심 종목을 추가할 수 있다.
  - 티커 심볼 입력
  - 중복 방지 (동일 사용자, 동일 종목)
- **FR-008**: 사용자는 관심 종목을 삭제할 수 있다.
- **FR-009**: 사용자는 자신의 관심 종목 목록을 조회할 수 있다.

#### 3.2.3 종목 데이터
- **FR-010**: 시스템은 주요 종목의 티커 심볼-회사명 매핑 테이블을 유지한다.
  - 예: TSLA - Tesla Inc., AAPL - Apple Inc.
  - S&P500 지수: ^GSPC - S&P 500 Index

### 3.3 뉴스 수집

#### 3.3.1 크롤링 설정
- **FR-011**: investing.com을 뉴스 소스로 사용한다.
- **FR-012**: Selenium 또는 Playwright를 사용하여 뉴스를 크롤링한다.
- **FR-013**: 3시간마다 자동으로 뉴스를 수집한다. (24시간 운영)
  - 수집 주기: 00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00

#### 3.3.2 수집 범위
- **FR-014**: 최근 3시간 이내에 게시된 뉴스를 수집한다.
- **FR-015**: 각 종목별로 뉴스를 수집한다.
- **FR-016**: 수집할 데이터:
  - 뉴스 제목
  - 뉴스 본문 (전체 또는 요약)
  - 게시 날짜 및 시간
  - 뉴스 URL
  - 종목 정보

#### 3.3.3 중복 방지
- **FR-017**: 동일한 뉴스는 중복 수집하지 않는다. (URL 또는 제목+날짜 기준)

### 3.4 뉴스 분석

#### 3.4.1 ChatGPT API 연동
- **FR-018**: ChatGPT API를 사용하여 뉴스를 분석한다.
- **FR-019**: 분석 내용:
  1. **다국어 요약**: 한국어, 영어, 스페인어, 일본어로 요약
  2. **호재/악재 분석**: 
     - 분류: 호재(Positive) / 악재(Negative) / 중립(Neutral)
     - 점수: -10 ~ +10 범위 (음수: 악재, 양수: 호재, 0: 중립)

#### 3.4.2 프롬프트 설계
- **FR-020**: 자연스러운 요약을 위한 프롬프트 작성
  - 각 언어별 자연스러운 표현 사용
  - 주식 투자자 관점의 핵심 정보 추출
  - 객관적이고 중립적인 분석

**프롬프트 예시**:
```
You are a professional stock market analyst. Analyze the following news article and provide:

1. Summary in Korean (한국어): A natural and fluent summary in Korean (2-3 sentences)
2. Summary in English: A natural and fluent summary in English (2-3 sentences)
3. Summary in Spanish (Español): A natural and fluent summary in Spanish (2-3 sentences)
4. Summary in Japanese (日本語): A natural and fluent summary in Japanese (2-3 sentences)
5. Sentiment Analysis:
   - Classification: Positive (호재) / Negative (악재) / Neutral (중립)
   - Score: -10 to +10 (-10: very negative, 0: neutral, +10: very positive)

News Article:
Title: {title}
Content: {content}
Stock: {stock_symbol}

Please provide the response in JSON format:
{
  "summary_ko": "...",
  "summary_en": "...",
  "summary_es": "...",
  "summary_ja": "...",
  "sentiment": {
    "classification": "Positive/Negative/Neutral",
    "score": 0
  }
}
```

### 3.5 데이터 저장

#### 3.5.1 SQLite 데이터베이스
- **FR-021**: 사용자 정보 저장
  - 테이블: users
  - 필드: id, username, email, password_hash, created_at, updated_at
- **FR-022**: 사용자 설정 저장
  - 테이블: user_settings
  - 필드: user_id, language, notification_time, is_active
- **FR-023**: 관심 종목 저장
  - 테이블: user_stocks
  - 필드: id, user_id, ticker_symbol, company_name, created_at
- **FR-024**: 종목 마스터 데이터
  - 테이블: stock_master
  - 필드: ticker_symbol, company_name, exchange, sector

#### 3.5.2 ElasticSearch 저장
- **FR-025**: 뉴스 및 분석 결과를 ElasticSearch 7.0.1에 저장
- **FR-026**: 인덱스 구조:
```json
{
  "news_id": "unique_id",
  "ticker_symbol": "TSLA",
  "company_name": "Tesla Inc.",
  "title": "원본 제목",
  "content": "원본 내용",
  "url": "뉴스 URL",
  "published_date": "2025-11-20T10:30:00Z",
  "crawled_date": "2025-11-20T12:00:00Z",
  "summary": {
    "ko": "한국어 요약",
    "en": "English summary",
    "es": "Resumen en español",
    "ja": "日本語の要約"
  },
  "sentiment": {
    "classification": "Positive",
    "score": 7
  }
}
```

#### 3.5.3 데이터 보관 정책
- **FR-027**: ElasticSearch 데이터는 2년간 보관한다.
- **FR-028**: 2년 이상된 데이터는 자동으로 삭제한다. (Index Lifecycle Management)

### 3.6 메일 발송

#### 3.6.1 발송 설정
- **FR-029**: 사용자는 메일 수신 시각을 설정할 수 있다.
  - 시간 단위 설정 (예: 09:00, 18:00)
  - 사용자마다 다른 시각 설정 가능
- **FR-030**: 사용자는 수신 언어를 선택할 수 있다. (한/영/스/일 중 1개)
- **FR-031**: Gmail SMTP를 사용하여 메일을 발송한다.

#### 3.6.2 메일 내용
- **FR-032**: HTML 형식의 보고서로 발송한다.
- **FR-033**: 메일 내용:
  - 제목: "[Stock Report] {날짜} - {사용자명}님의 관심 종목 분석"
  - 본문:
    - 인사말
    - 종목별로 구분된 뉴스 리스트
    - 각 뉴스: 제목, 선택 언어 요약, 호재/악재 표시 (아이콘 + 점수)
    - 원문 링크
    - 통계: 총 뉴스 수, 호재/악재 비율
- **FR-034**: 디자인 요구사항:
  - 깔끔하고 전문적인 레이아웃
  - 호재는 녹색, 악재는 빨간색, 중립은 회색으로 표시
  - 모바일에서도 읽기 쉬운 반응형 디자인

#### 3.6.3 발송 로직
- **FR-035**: 사용자가 설정한 시각에 최근 3시간 뉴스를 포함한 메일을 발송한다.
- **FR-036**: 해당 시간대에 새로운 뉴스가 없으면 "새로운 뉴스가 없습니다" 메시지 발송
- **FR-037**: 메일 발송 실패 시 재시도 로직 (최대 3회)
- **FR-038**: 발송 이력을 로그로 기록한다.

### 3.7 웹 UI 기능

#### 3.7.1 대시보드
- **FR-039**: 로그인 후 메인 페이지
- **FR-040**: 표시 내용:
  - 오늘의 주요 뉴스 요약 (전체 종목)
  - 종목별 최신 뉴스 카드 (최대 5개)
  - 호재/악재 통계 요약

#### 3.7.2 관심 종목 관리 페이지
- **FR-041**: 관심 종목 목록 표시
- **FR-042**: 종목 추가 폼 (티커 심볼 입력)
- **FR-043**: 종목 삭제 버튼

#### 3.7.3 뉴스 히스토리 페이지
- **FR-044**: 날짜/종목별 과거 뉴스 조회 및 필터링
- **FR-045**: 날짜 범위 선택 필터
- **FR-046**: 호재/악재 필터
- **FR-047**: 페이지네이션 (페이지당 20개)
- **FR-048**: 각 뉴스 클릭 시 상세 보기 (모든 언어 요약 표시)

#### 3.7.4 통계 보기 페이지
- **FR-049**: 종목별 호재/악재 통계 (최근 7일, 30일)
  - 차트 형태로 시각화 (Chart.js 또는 Plotly 사용)
- **FR-050**: 종목별 뉴스 수 통계

#### 3.7.5 설정 페이지
- **FR-051**: 메일 수신 시각 설정
- **FR-052**: 메일 수신 언어 선택 (한/영/스/일 중 1개)
- **FR-053**: 알림 ON/OFF (임시 중단 기능)
- **FR-054**: 테스트 메일 발송 버튼 (설정 확인용 즉시 메일 발송 기능)
- **FR-055**: 비밀번호 변경
- **FR-056**: 이메일 주소 변경

#### 3.7.6 관리자 페이지
- **FR-057**: 사용자 목록 조회
- **FR-058**: 새 사용자 등록
- **FR-059**: 사용자 비활성화/활성화
- **FR-060**: 시스템 상태 모니터링
  - 크롤링 상태
  - ElasticSearch 연결 상태
  - 마지막 메일 발송 시각

---

## 4. 비기능 요구사항

### 4.1 성능 요구사항
- **NFR-001**: 웹 페이지 로딩 시간은 3초 이내여야 한다.
- **NFR-002**: ElasticSearch 쿼리 응답 시간은 1초 이내여야 한다.
- **NFR-003**: 3시간마다 수행되는 크롤링은 30분 이내에 완료되어야 한다.
- **NFR-004**: 동시 사용자 3명까지 원활하게 지원한다.

### 4.2 확장성
- **NFR-005**: 단순한 프로젝트 구조로 설계하여 유지보수가 쉬워야 한다.
- **NFR-006**: 향후 사용자 증가 시 확장 가능한 구조여야 한다.

### 4.3 신뢰성
- **NFR-007**: 시스템 가용성 95% 이상 (월간 기준)
- **NFR-008**: 크롤링 실패 시 자동 재시도 (최대 3회)
- **NFR-009**: 메일 발송 실패 시 자동 재시도 (최대 3회)
- **NFR-010**: 에러 발생 시 로그 기록 및 관리자 알림

### 4.4 보안
- **NFR-011**: 비밀번호는 암호화하여 저장한다. (bcrypt 또는 werkzeug.security)
- **NFR-012**: 세션 기반 인증으로 로그인 상태 유지
- **NFR-013**: SQL Injection 방지 (ORM 사용)
- **NFR-014**: XSS 공격 방지 (입력값 검증 및 이스케이프)
- **NFR-015**: HTTPS 통신은 현 시점에서 미적용 (향후 적용 가능)

### 4.5 사용성
- **NFR-016**: 직관적이고 간단한 UI/UX
- **NFR-017**: 반응형 웹 디자인 (모바일, 태블릿, 데스크톱 지원)
- **NFR-018**: 한국어 UI (기본)

### 4.6 유지보수성
- **NFR-019**: 코드는 PEP 8 스타일 가이드를 따른다.
- **NFR-020**: 주요 함수 및 모듈에 대한 주석 작성
- **NFR-021**: 환경 변수를 통한 설정 관리 (.env 파일)
- **NFR-022**: 로깅 시스템 구축 (Python logging 모듈)

---

## 5. 기술 스택

### 5.1 백엔드
- **언어**: Python 3.9+
- **프레임워크**: Flask 2.x
- **ORM**: SQLAlchemy (SQLite 연동)
- **스케줄러**: APScheduler
- **크롤링**: Selenium 또는 Playwright (선택 예정)

### 5.2 프론트엔드
- **템플릿 엔진**: Jinja2 (Flask 기본)
- **CSS 프레임워크**: Bootstrap 5 또는 Tailwind CSS
- **JavaScript**: Vanilla JS 또는 jQuery
- **차트 라이브러리**: Chart.js 또는 Plotly.js

### 5.3 데이터베이스
- **관계형 DB**: SQLite 3
- **검색 엔진**: ElasticSearch 7.0.1

### 5.4 외부 API
- **AI 분석**: OpenAI ChatGPT API (GPT-5)
- **메일 발송**: Gmail SMTP

### 5.5 인프라
- **컨테이너화**: Docker, Docker Compose
- **운영체제**: Ubuntu Server (클라우드)
- **웹 서버**: Gunicorn (WSGI) + Nginx (리버스 프록시, 선택적)

### 5.6 개발 도구
- **버전 관리**: Git
- **패키지 관리**: pip, requirements.txt
- **가상 환경**: venv 또는 virtualenv

---

## 6. 시스템 제약사항

### 6.1 환경 제약사항
- **CON-001**: 우분투 서버에 Docker가 설치되어 있어야 한다.
- **CON-002**: 인터넷 연결이 필수적이다. (크롤링, API 호출)
- **CON-003**: Gmail SMTP 사용을 위한 앱 비밀번호 설정 필요

### 6.2 외부 의존성
- **CON-004**: investing.com의 웹사이트 구조 변경 시 크롤러 수정 필요
- **CON-005**: OpenAI API 사용량 및 비용 관리 필요
- **CON-006**: Gmail 발송 제한 (일일 500통) 준수 필요

### 6.3 기술적 제약사항
- **CON-007**: ElasticSearch 7.0.1 버전 사용 (호환성 고려)
- **CON-008**: 최대 5명 사용자, 동시 3명 접속 환경
- **CON-009**: HTTPS 미적용 (내부 서비스)

---

## 7. 데이터베이스 스키마

### 7.1 SQLite 테이블 설계

#### 7.1.1 users 테이블
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 7.1.2 user_settings 테이블
```sql
CREATE TABLE user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    language VARCHAR(10) DEFAULT 'ko',  -- ko, en, es, ja
    notification_time TIME NOT NULL,     -- 예: 09:00:00
    is_notification_enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### 7.1.3 stock_master 테이블
```sql
CREATE TABLE stock_master (
    ticker_symbol VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(200) NOT NULL,
    exchange VARCHAR(50),  -- NYSE, NASDAQ, etc.
    sector VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 7.1.4 user_stocks 테이블
```sql
CREATE TABLE user_stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker_symbol VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (ticker_symbol) REFERENCES stock_master(ticker_symbol),
    UNIQUE(user_id, ticker_symbol)
);
```

#### 7.1.5 email_logs 테이블
```sql
CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),  -- success, failed
    error_message TEXT,
    news_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

#### 7.1.6 crawl_logs 테이블
```sql
CREATE TABLE crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker_symbol VARCHAR(10),
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),  -- success, failed
    news_count INTEGER DEFAULT 0,
    error_message TEXT
);
```

### 7.2 ElasticSearch 인덱스 설계

#### 7.2.1 news_analysis 인덱스
```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "index": {
      "lifecycle": {
        "name": "news_policy",
        "rollover_alias": "news_analysis"
      }
    }
  },
  "mappings": {
    "properties": {
      "news_id": { "type": "keyword" },
      "ticker_symbol": { "type": "keyword" },
      "company_name": { "type": "text" },
      "title": { "type": "text", "analyzer": "standard" },
      "content": { "type": "text", "analyzer": "standard" },
      "url": { "type": "keyword" },
      "published_date": { "type": "date" },
      "crawled_date": { "type": "date" },
      "summary": {
        "properties": {
          "ko": { "type": "text", "analyzer": "korean" },
          "en": { "type": "text", "analyzer": "english" },
          "es": { "type": "text", "analyzer": "spanish" },
          "ja": { "type": "text", "analyzer": "cjk" }
        }
      },
      "sentiment": {
        "properties": {
          "classification": { "type": "keyword" },
          "score": { "type": "integer" }
        }
      }
    }
  }
}
```

#### 7.2.2 Index Lifecycle Policy (2년 보관)
```json
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {}
      },
      "delete": {
        "min_age": "730d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

---

## 8. API 설계

### 8.1 인증 API

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/auth/login` | 로그인 | `{username, password}` | `{success, session_id}` |
| POST | `/api/auth/logout` | 로그아웃 | - | `{success}` |
| GET | `/api/auth/session` | 세션 확인 | - | `{authenticated, user}` |

### 8.2 사용자 API

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/api/user/profile` | 내 정보 조회 | - | `{user_info}` |
| PUT | `/api/user/profile` | 내 정보 수정 | `{email, password}` | `{success}` |
| GET | `/api/user/settings` | 설정 조회 | - | `{settings}` |
| PUT | `/api/user/settings` | 설정 수정 | `{language, notification_time, is_enabled}` | `{success}` |

### 8.3 종목 API

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/api/stocks/my-stocks` | 내 관심 종목 조회 | - | `{stocks: [...]}` |
| POST | `/api/stocks/add` | 관심 종목 추가 | `{ticker_symbol}` | `{success}` |
| DELETE | `/api/stocks/remove/{id}` | 관심 종목 삭제 | - | `{success}` |
| GET | `/api/stocks/search` | 종목 검색 | `?q=TSLA` | `{stocks: [...]}` |

### 8.4 뉴스 API

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| GET | `/api/news/latest` | 최신 뉴스 조회 | `?ticker=TSLA&limit=10` | `{news: [...]}` |
| GET | `/api/news/history` | 뉴스 히스토리 | `?from=date&to=date&ticker=TSLA&page=1` | `{news: [...], total}` |
| GET | `/api/news/{news_id}` | 뉴스 상세 | - | `{news_detail}` |
| GET | `/api/news/statistics` | 통계 조회 | `?ticker=TSLA&period=7d` | `{stats}` |

### 8.5 관리자 API

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/api/admin/users` | 사용자 생성 | `{username, email, password}` | `{success, user_id}` |
| GET | `/api/admin/users` | 사용자 목록 | - | `{users: [...]}` |
| PUT | `/api/admin/users/{id}` | 사용자 활성화/비활성화 | `{is_active}` | `{success}` |
| GET | `/api/admin/system-status` | 시스템 상태 | - | `{status}` |
| POST | `/api/admin/test-email` | 테스트 메일 발송 | `{user_id}` | `{success}` |

---

## 9. 스케줄링 설계

### 9.1 뉴스 크롤링 스케줄
- **주기**: 3시간마다 (00:00, 03:00, 06:00, 09:00, 12:00, 15:00, 18:00, 21:00)
- **작업 내용**:
  1. 모든 사용자의 관심 종목 목록 조회
  2. 종목별로 investing.com에서 뉴스 크롤링
  3. 최근 3시간 이내 뉴스만 필터링
  4. 중복 체크 (URL 기준)
  5. ChatGPT API로 분석 (요약 + 호재/악재 판단)
  6. ElasticSearch에 저장
  7. 로그 기록

### 9.2 메일 발송 스케줄
- **주기**: 매시간 체크 (00:00, 01:00, ..., 23:00)
- **작업 내용**:
  1. 현재 시각에 메일 수신을 원하는 사용자 조회
  2. 각 사용자별로:
     - 관심 종목의 최근 3시간 뉴스 조회 (ElasticSearch)
     - 사용자가 선택한 언어로 요약 추출
     - HTML 메일 생성
     - Gmail SMTP로 발송
     - 발송 이력 로그 기록
  3. 발송 실패 시 재시도 (최대 3회, 5분 간격)

### 9.3 데이터 정리 스케줄
- **주기**: 매일 02:00
- **작업 내용**:
  1. ElasticSearch에서 2년 이상 된 데이터 삭제
  2. SQLite 로그 테이블 정리 (1년 이상 로그 삭제)

---

## 10. 메일 템플릿 설계

### 10.1 HTML 메일 구조
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* 반응형 스타일 */
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .header { background: #1a73e8; color: white; padding: 20px; }
        .stock-section { margin: 20px 0; border: 1px solid #ddd; border-radius: 8px; }
        .news-item { padding: 15px; border-bottom: 1px solid #eee; }
        .positive { color: #34a853; }
        .negative { color: #ea4335; }
        .neutral { color: #999; }
        .score-badge { display: inline-block; padding: 5px 10px; border-radius: 4px; }
        .footer { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Stock Analysis Report</h1>
        <p>{{user_name}}님의 관심 종목 분석 - {{date}}</p>
    </div>
    
    <!-- 종목별 섹션 반복 -->
    {% for stock in stocks %}
    <div class="stock-section">
        <h2>{{stock.ticker_symbol}} - {{stock.company_name}}</h2>
        
        {% for news in stock.news_list %}
        <div class="news-item">
            <h3>{{news.title}}</h3>
            <p>{{news.summary}}</p>
            
            <div class="sentiment">
                <span class="score-badge {{news.sentiment.classification}}">
                    {{news.sentiment.classification}} 
                    (점수: {{news.sentiment.score}})
                </span>
            </div>
            
            <p><a href="{{news.url}}">원문 보기 →</a></p>
            <small>{{news.published_date}}</small>
        </div>
        {% endfor %}
    </div>
    {% endfor %}
    
    <div class="footer">
        <p>총 {{total_news}}건의 뉴스 | 호재 {{positive_count}}건 | 악재 {{negative_count}}건</p>
        <p><a href="{{dashboard_url}}">대시보드에서 자세히 보기</a></p>
    </div>
</body>
</html>
```

---

## 11. 에러 처리

### 11.1 크롤링 에러
- **ERR-001**: investing.com 접속 실패 → 5분 후 재시도 (최대 3회)
- **ERR-002**: 페이지 구조 변경 → 로그 기록 및 관리자 알림
- **ERR-003**: 타임아웃 → 다음 스케줄에서 재시도

### 11.2 API 에러
- **ERR-004**: ChatGPT API 호출 실패 → 재시도 또는 기본 요약 생성
- **ERR-005**: API 요금 한도 초과 → 관리자 알림, 임시 중단
- **ERR-006**: 잘못된 응답 형식 → 로그 기록, 기본값 사용

### 11.3 데이터베이스 에러
- **ERR-007**: ElasticSearch 연결 실패 → 재연결 시도, 로그 파일에 임시 저장
- **ERR-008**: SQLite 락 → 대기 후 재시도

### 11.4 메일 발송 에러
- **ERR-009**: SMTP 인증 실패 → 관리자 알림
- **ERR-010**: 발송 실패 → 5분 간격 3회 재시도, 로그 기록
- **ERR-011**: 일일 발송 한도 초과 → 관리자 알림, 다음날 재시도

---

## 12. 로깅 전략

### 12.1 로그 레벨
- **DEBUG**: 개발 시 상세 정보
- **INFO**: 일반 작업 완료 (크롤링 완료, 메일 발송 완료)
- **WARNING**: 경고 (재시도 발생)
- **ERROR**: 에러 발생 (재시도 실패)
- **CRITICAL**: 시스템 중단 레벨 에러

### 12.2 로그 파일
- `app.log`: 전체 애플리케이션 로그
- `crawler.log`: 크롤링 관련 로그
- `email.log`: 메일 발송 로그
- `error.log`: 에러만 모아서 기록

### 12.3 로그 형식
```
[2025-11-20 12:00:00] [INFO] [crawler] Successfully crawled 15 news for TSLA
[2025-11-20 12:05:00] [ERROR] [email] Failed to send email to user@example.com: SMTP timeout
```

---

## 13. 보안 고려사항

### 13.1 인증 및 권한
- 비밀번호 해싱: bcrypt (cost factor: 12)
- 세션 타임아웃: 24시간
- 관리자 권한 분리

### 13.2 입력 검증
- 티커 심볼: 알파벳 대문자 + 최대 10자
- 이메일: 정규식 검증
- SQL Injection 방지: SQLAlchemy ORM 사용
- XSS 방지: 사용자 입력 이스케이프 (Jinja2 자동 처리)

### 13.3 API 키 관리
- 시스템 공용 API 키 사용 (환경 변수로 관리)
- Git에 커밋하지 않음 (.gitignore)
- Docker 시크릿 사용 고려

### 13.4 Rate Limiting
- API 엔드포인트별 요청 제한 (Flask-Limiter)
- 로그인 실패 5회 시 계정 잠금 (10분)

---

## 14. 배포 구성

### 14.1 Docker Compose 구조
```yaml
version: '3.8'

services:
  flask-app:
    build: ./app
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=sqlite:///data/app.db
      - ELASTICSEARCH_URL=http://elasticsearch:9200
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - elasticsearch

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.0.1
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data

volumes:
  es-data:
```

### 14.2 환경 변수 (.env)
```
# Flask
FLASK_SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database
DATABASE_URL=sqlite:///data/app.db
ELASTICSEARCH_URL=http://elasticsearch:9200

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# Gmail
GMAIL_USERNAME=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password

# Crawler
CRAWLER_TYPE=selenium  # or playwright
HEADLESS=true
```

### 14.3 디렉토리 구조
```
scockAnalysis/
├── app/
│   ├── __init__.py
│   ├── models/          # SQLAlchemy 모델
│   ├── routes/          # Flask 라우트
│   ├── services/        # 비즈니스 로직
│   │   ├── crawler.py
│   │   ├── analyzer.py
│   │   ├── email_sender.py
│   │   └── scheduler.py
│   ├── templates/       # Jinja2 템플릿
│   ├── static/          # CSS, JS, 이미지
│   └── utils/           # 유틸리티 함수
├── data/                # SQLite DB 파일
├── logs/                # 로그 파일
├── tests/               # 테스트 코드
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 15. 테스트 계획

### 15.1 단위 테스트
- 크롤러 함수 테스트
- ChatGPT 프롬프트 결과 검증
- 데이터베이스 CRUD 테스트
- 메일 발송 함수 테스트

### 15.2 통합 테스트
- 전체 뉴스 수집 → 분석 → 저장 플로우
- 스케줄러 작동 테스트
- API 엔드포인트 테스트

### 15.3 수동 테스트
- 웹 UI 사용성 테스트
- 메일 수신 확인
- 다양한 종목에 대한 크롤링 테스트

---

## 16. 프로젝트 일정 (예상)

### Phase 1: 기본 인프라 구축 (1주)
- Flask 애플리케이션 구조 설정
- SQLite 데이터베이스 스키마 생성
- ElasticSearch 연동
- Docker 환경 구성

### Phase 2: 크롤링 및 분석 (2주)
- investing.com 크롤러 개발
- ChatGPT API 연동 및 프롬프트 최적화
- 데이터 저장 로직 구현
- 스케줄러 설정

### Phase 3: 웹 UI 개발 (2주)
- 로그인/로그아웃 기능
- 대시보드
- 종목 관리 페이지
- 뉴스 히스토리 및 통계 페이지
- 설정 페이지

### Phase 4: 메일 발송 (1주)
- HTML 메일 템플릿 디자인
- Gmail SMTP 연동
- 메일 발송 스케줄러

### Phase 5: 테스트 및 배포 (1주)
- 통합 테스트
- 버그 수정
- 우분투 서버 배포
- 모니터링 설정

**총 예상 기간**: 7주

---

## 17. 향후 개선 사항 (Optional)

### 17.1 기능 개선
- **OPT-001**: 사용자 직접 회원가입 기능 (이메일 인증)
- **OPT-002**: JWT 기반 인증으로 업그레이드
- **OPT-003**: HTTPS 적용
- **OPT-004**: 실시간 알림 (웹 푸시 또는 Slack 연동)
- **OPT-005**: 더 많은 뉴스 소스 추가 (Bloomberg, Reuters, etc.)
- **OPT-006**: 종목 추천 기능 (AI 기반)
- **OPT-007**: 모바일 앱 개발

### 17.2 성능 개선
- **OPT-008**: 캐싱 시스템 도입 (Redis)
- **OPT-009**: 비동기 크롤링 (asyncio)
- **OPT-010**: 데이터베이스 최적화 (인덱싱)

### 17.3 분석 고도화
- **OPT-011**: 감정 분석 정확도 향상 (Fine-tuning)
- **OPT-012**: 주가 예측 모델 추가
- **OPT-013**: 뉴스 트렌드 분석

---

## 18. 부록

### 18.1 참고 자료
- Flask 공식 문서: https://flask.palletsprojects.com/
- ElasticSearch 7.x 문서: https://www.elastic.co/guide/en/elasticsearch/reference/7.0/
- OpenAI API 문서: https://platform.openai.com/docs/
- Selenium 문서: https://selenium-python.readthedocs.io/
- Playwright 문서: https://playwright.dev/python/

### 18.2 용어집
- **SRS**: Software Requirements Specification (소프트웨어 요구사항 명세서)
- **SMTP**: Simple Mail Transfer Protocol (이메일 전송 프로토콜)
- **ORM**: Object-Relational Mapping (객체-관계 매핑)
- **WSGI**: Web Server Gateway Interface (웹 서버 게이트웨이 인터페이스)
- **JWT**: JSON Web Token (JSON 웹 토큰)

### 18.3 연락처
- 프로젝트 관리자: [담당자 정보]
- 기술 지원: [지원 이메일]

---

## 19. 문서 개정 이력

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0 | 2025-11-20 | GitHub Copilot | 초안 작성 |

---

**문서 종료**
