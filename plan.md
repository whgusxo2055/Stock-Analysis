# 개발 계획서 (Project Development Plan)
## 프로젝트: Stock Analysis Service
문서 버전: 0.1 (초안)  
작성일: 2025-11-20  
작성자: GitHub Copilot  
참고 문서: SRS v1.0 (`srs.md`)

---
## 1. 개요
미국 주식 관심 종목 뉴스 자동 수집/분석 및 이메일 보고 시스템을 7주 내 최소 기능(Product MVP) 수준으로 구축한다. 본 계획서는 구현 순서, 역할, 일정, 위험, 품질 및 운영 전략을 정의한다.

### 1.1 목표
- SRS에 정의된 핵심 기능 (사용자 관리, 종목 관리, 크롤링, 분석, 저장, 메일 발송, 기본 UI) 구현
- 안정적 크롤링 & 분석 파이프라인 확립 (재시도 및 로그 포함)
- ElasticSearch + SQLite 이중 저장 구조 확립
- 일일 운용이 가능한 스케줄러 기반 자동화 제공

### 1.2 범위(In-Scope)
- Flask 백엔드 + Jinja2 웹 UI (관리/일반 사용자)
- Selenium 또는 Playwright 단일 선택 후 구현 (초기 Selenium 가정)
- ChatGPT API 통한 다국어 요약 & 감성 분석
- Docker Compose 기반 단일 노드 배포 (ES 포함)
- 기본 세션 인증 (비밀번호 해시)

### 1.3 범위 제외(Out-of-Scope)
- HTTPS / JWT / 사용자 자가 가입
- 추가 뉴스 소스 (Investing.com 외)
- 캐싱(Redis), 고급 성능 최적화, 모바일 앱, 실시간 알림

### 1.4 성공 기준(KPIs)
- 크롤링 성공률 ≥ 90% (재시도 후)
- 메일 발송 성공률 ≥ 95%
- ElasticSearch 평균 조회 응답 ≤ 1초 (NFR-002)
- 크롤링 수행 시간 ≤ 30분/회 (NFR-003)

---
## 2. 산출물(Deliverables)
| 구분 | 산출물 | 설명 | 완료 기준 |
|------|--------|------|-----------|
| 코드 | Flask 앱 구조 | 디렉토리 및 초기 앱 팩토리 | 실행 및 기본 라우트 응답 |
| 데이터 | SQLite 스키마 | users, stocks 등 테이블 생성 | 마이그레이션 스크립트 성공 |
| 인덱스 | ES 인덱스 & 정책 | news_analysis + ILM 정책 | 인덱스 생성 & 문서 색인 테스트 |
| 기능 | 크롤러 모듈 | 종목별 뉴스 수집 & 중복 제거 | 지정 종목 1건 이상 색인 |
| 기능 | 분석 모듈 | ChatGPT API 호출/파싱 | JSON 구조 검증 |
| 기능 | 스케줄러 | 크롤링/메일/정리 작업 | APScheduler job 리스트 확인 |
| 운영 | Docker Compose | 로컬/서버 구동 | 단일 명령으로 서비스 기동 |
| 문서 | README | 설치/실행/환경변수 | 리뷰 승인 |
| 문서 | 테스트 보고 | 단위/통합 결과 요약 | CI 통과 로그 |

---
## 3. 일정 및 마일스톤 (총 7주)
| 주차 | 마일스톤 | 세부 작업 | 완료 조건 |
|------|-----------|-----------|-----------|
| 1 | 기반 구조 | 디렉토리, 앱 초기화, 환경설정(.env), DB 스키마, Docker 기본 | 로컬 Flask + ES 컨테이너 기동 |
| 2 | 데이터 & 인덱스 | SQLAlchemy 모델, ES 인덱스 생성, 저장 어댑터 | 모델 CRUD & ES 색인 테스트 |
| 3 | 크롤러 MVP | Selenium 설정, Investing.com 파싱, 중복 로직 | 1개 티커 뉴스 ≥3건 수집 |
| 4 | 분석 & 저장 파이프라인 | ChatGPT 프롬프트, 다국어 요약, 감성 점수, 파이프라인 통합 | 색인 문서에 summary/sentiment 포함 |
| 5 | 웹 UI / API | 인증, 종목 관리, 뉴스 조회, 통계 기본, 관리자 상태 | 핵심 API / 페이지 렌더링 |
| 6 | 메일 & 스케줄러 | HTML 템플릿, SMTP, APScheduler 잡, 재시도/로그 | 사용자별 테스트 메일 발송 성공 |
| 7 | 테스트/배포 | 단위/통합 테스트, 성능 점검, 서버 배포, 문서 업데이트 | 서버 실환경 가동 & 기본 모니터링 |

선행 관계: 1→2→3→4 병행 5 시작 가능(크롤러 일부 데이터 필요), 6은 4/5 완료 후, 7은 모든 기능 통합 후.

---
## 4. 작업 분해 구조(WBS)
번호 체계: P-Phase.M-Module.T-Task

### 4.1 Phase 1 (기반)
- P1.M1.T1: Flask 앱 팩토리 (`app/__init__.py`)
- P1.M1.T2: 환경 변수 로딩 유틸 (`utils/config.py`)
- P1.M2.T3: requirements.txt 초기화
- P1.M3.T4: Dockerfile / docker-compose.yml 초안
- P1.M4.T5: 초기 로그 설정 (logging 기본 핸들러)

### 4.2 Phase 2 (데이터)
- P2.M1.T1: SQLAlchemy 모델 (users/user_settings/stock_master/user_stocks/email_logs/crawl_logs)
- P2.M1.T2: DB 세션 관리 유틸
- P2.M2.T3: ES 클라이언트 초기화
- P2.M2.T4: news_analysis 인덱스 및 ILM policy 생성 스크립트
- P2.M3.T5: 저장 서비스 (뉴스 색인 함수)

### 4.3 Phase 3 (크롤링)
- P3.M1.T1: Selenium 드라이버 초기화 (Headless 옵션)
- P3.M1.T2: 티커→검색 쿼리 생성 유틸
- P3.M1.T3: 뉴스 목록 추출 & 시간 필터
- P3.M1.T4: 중복 검사 (URL 키)
- P3.M1.T5: 에러/재시도 로직 (최대 3회)

### 4.4 Phase 4 (분석)
- P4.M1.T1: ChatGPT 요청 포맷 정의 (FR-020 활용)
- P4.M1.T2: 응답 JSON 파싱 및 검증
- P4.M1.T3: 감성 점수 정상 범위(-10~10) 확인
- P4.M1.T4: 파이프라인 결합 (크롤링→분석→저장)

### 4.5 Phase 5 (API & UI)
- P5.M1.T1: 인증 라우트 (/api/auth/*)
- P5.M1.T2: 사용자 설정/종목 API
- P5.M1.T3: 뉴스 조회/히스토리/통계 API
- P5.M1.T4: 관리자 API (시스템 상태)
- P5.M2.T5: Jinja 템플릿: 대시보드/종목/뉴스/통계/설정/관리자

### 4.6 Phase 6 (메일 & 스케줄)
- P6.M1.T1: HTML 메일 템플릿 구현
- P6.M1.T2: 이메일 전송 함수 (재시도 포함)
- P6.M2.T3: 스케줄러 잡 등록 (크롤링/메일/정리)
- P6.M2.T4: 통계 집계 유틸 (호재/악재 비율)

### 4.7 Phase 7 (테스트/배포)
- P7.M1.T1: 단위 테스트 (모델/크롤러/분석)
- P7.M1.T2: 통합 테스트 (전체 파이프라인)
- P7.M2.T3: 로드 샘플(소규모 성능 테스트)
- P7.M3.T4: 서버 배포 스크립트 (prod .env)
- P7.M3.T5: 최종 문서 & 운영 핸드북

---
## 5. 요구사항 추적 매트릭스 (요약)
| FR/NFR | 매핑 모듈/작업 | 검증 방식 |
|--------|----------------|-----------|
| FR-001~005 | 사용자/설정 API (P5.M1.T1~T2) | API 테스트 & DB 확인 |
| FR-006~010 | 종목 관리 & stock_master (P2.M1.T1, P5.M1.T2) | CRUD 테스트 |
| FR-011~017 | 크롤러 (P3.*) | 크롤링 로그 & 중복 테스트 |
| FR-018~020 | 분석 엔진 (P4.*) | 응답 JSON 구조 검증 |
| FR-021~024 | SQLite 모델 (P2.M1.T1) | 마이그레이션 + 단위 테스트 |
| FR-025~028 | ES 인덱스 & 정책 (P2.M2.T4) | 문서 색인 & 삭제 시뮬레이션 |
| FR-029~038 | 메일 & 스케줄러 (P6.*) | 스케줄 실행 로그 |
| FR-039~060 | UI/관리자 (P5.M2.T5) | 페이지 렌더 & 기능 테스트 |
| NFR-001~004 | 성능 테스트 (P7.M2.T3) | 측정 리포트 |
| NFR-011~015 | 보안(해시/세션/XSS) | 코드 리뷰 & 침투 테스트 기초 |
| NFR-019~022 | 코드 스타일/로깅 | 린트 결과 & 로그 파일 |

---
## 6. 기술 구현 전략
### 6.1 Flask 구조
- 앱 팩토리 패턴 + Blueprint: auth, user, stocks, news, admin
- 서비스 레이어 분리: `services/` (crawler, analyzer, email_sender, scheduler)

### 6.2 크롤러 선택
- 초기: Selenium (풍부한 사례, 안정성)
- 드라이버: Chrome headless (추후 Playwright 전환 가능성 열어둠)
- 타임아웃 & 암묵적 대기 설정 (예: 10s)

### 6.3 분석 엔진
- ChatGPT 요청 배치 처리 최소화 (뉴스 건수 많을 경우 속도 고려)
- 실패 시 재시도 + Fallback: 간단한 규칙 기반 요약 (Title 기반 1문장)

### 6.4 저장 로직
- 뉴스 단위 트랜잭션: 크롤링 후 메모리 목록 → 분석 후 ES Bulk 색인
- SQLite는 사용자/설정/로그만. 뉴스 본문은 ES에만 저장.

### 6.5 스케줄러
- APScheduler BackgroundScheduler + jobstore (기본 메모리)
- Job 목록: crawl_job(3h), email_job(1h check), cleanup_job(daily)

---
## 7. 테스트 전략
### 7.1 단위 테스트
- 모델 CRUD (pytest + sqlite memory)
- 크롤러 파싱 함수 (HTML fixture)
- 분석 응답 파서 (Mock OpenAI 응답)

### 7.2 통합 테스트
- End-to-end: 티커 → 크롤링 → 분석 → ES 색인 → API 응답

### 7.3 성능 테스트(샘플)
- 10개 뉴스 분석 평균 소요 시간 측정
- ES 검색 latency 측정 (p95 < 1s 목표)

### 7.4 품질 게이트
- 린트: flake8 / black (PEP8 준수)
- 타입(옵션): mypy (핵심 서비스 레이어)

---
## 8. 보안 & 운영 전략
- 비밀번호: bcrypt cost=12
- 세션 보호: SECRET_KEY .env 관리
- 환경변수 로딩: python-dotenv
- 로그 회전: 주 단위(추가 개선 여지)
- API 키: .env + .gitignore

---
## 9. 배포 전략
### 9.1 Docker
- 다중 서비스: flask-app, elasticsearch
- Gunicorn 실행 (예: workers=2, threads=4, timeout=120)

### 9.2 배포 단계
1. 이미지 빌드 & 태그
2. 서버 .env 배치
3. docker-compose pull/build/up
4. 헬스체크: /api/auth/session, ES 상태, 크롤링 로그

### 9.3 롤백
- 이전 태그 이미지 유지 → docker-compose 다운 후 이전 버전 up

---
## 10. 로깅 & 모니터링
- 로그 파일 분리: app.log, crawler.log, email.log, error.log
- 포맷: 시간 | 레벨 | 모듈 | 메시지
- 모니터링 지표(수동): 크롤링 성공 건수, 메일 발송 실패율

---
## 11. 위험(Risk) 및 대응
| 유형 | 리스크 | 영향 | 확률 | 대응/완화 |
|------|--------|------|------|-----------|
| 기술 | Investing DOM 변경 | 크롤링 실패 | 중 | 파싱 추상화 & Selector 예비안 |
| 기술 | OpenAI 속도/비용 | 분석 지연/비용 증가 | 중 | 캐싱·요약 길이 제한 |
| 운영 | Gmail 한도 초과 | 메일 중단 | 저 | 사용자 수 제한 + 발송 모니터링 |
| 일정 | 크롤러 지연 | 후속 단계 밀림 | 중 | 초기 단순 버전 → 점진 개선 |
| 품질 | ES 색인 오류 누적 | 통계 부정확 | 저 | 색인 검증 & 에러 로그 경고 |

---
## 12. 역할 및 리소스 (가정)
| 역할 | 담당 | 주요 책임 |
|------|------|-----------|
| 백엔드 개발 | Dev A | Flask, 모델, API |
| 크롤링/분석 | Dev B | Selenium, ChatGPT 연동 |
| 프론트/UI | Dev C | Jinja 템플릿, 차트 |
| 테스트/품질 | Dev D | 테스트 코드, CI |
| 운영/배포 | Dev E | Docker, 배포, 로그 |
(소규모 팀이므로 실제론 2~3명이 복수 역할 수행 가능)

---
## 13. 커뮤니케이션 & 협업
- 일일 스탠드업 (15분): 진행/이슈/차일드 태스크
- 주간 리뷰: 마일스톤 점검
- 이슈 트래킹: GitHub Issues (태그: backend, crawler, ui, ops, test)
- 코드 리뷰: 최소 1명 승인 후 main 병합

---
## 14. 변경 관리
- 요구 변경 발생 시 Issue → 영향 분석(범위/일정) → 승인 → 반영
- SRS 변경 시 추적 매트릭스 업데이트

---
## 15. 환경 변수 관리
- `.env.example` 제공 → 민감 정보 제외
- 운영 환경: 별도 .env (권한 제한)

---
## 16. 성능 최적화(초기 가이드)
- 크롤링 병렬성 제한: 순차 또는 소규모 배치 (티커 ≤ 10 가정)
- ChatGPT 호출: 필요시 rate limit 대기
- ES 쿼리: 필요한 필드만 반환 (source filtering)

---
## 17. 종료 & 인수 기준
- 모든 FR 주요 기능 동작 (크롤링→분석→저장→메일)
- 관리자 페이지로 상태 확인 가능
- 테스트 통과율 ≥ 85% (단위 + 통합)
- 문서(README, plan, SRS) 최신화

---
## 18. 향후 확장 고려 요약
- 다중 뉴스 소스 / Redis 캐시 / JWT / HTTPS / 실시간 알림 / 추천 기능 / 분석 고도화

---
## 19. SRS 개정에 따른 추가 개발 계획 (Phase 8)

### 19.1 개정 배경
SRS v1.1 개정으로 ElasticSearch 인덱스 구조가 변경됨. 기존 `url` 필드가 임의 생성된 URL을 저장하는 문제를 해결하고, 데이터 추적성 및 분석 품질 향상을 위한 필드가 추가됨.

### 19.2 주요 변경 사항 (FR-026, 7.2.1 개정)

| 구분 | 기존 | 변경 | 변경 사유 |
|------|------|------|-----------|
| 필드명 | `url` | `source_url` | 명확한 의미 전달, 실제 기사 URL 저장 |
| 신규 필드 | - | `source_name` | 뉴스 출처 추적 (예: Investing.com) |
| 신규 필드 | - | `analyzed_date` | GPT 분석 완료 시점 기록 |
| 신규 필드 | - | `metadata` | word_count, language, gpt_model 메타정보 |
| 값 규칙 | `"Positive"` | `"positive"` | sentiment.classification lowercase 통일 |
| 형식 | - | UUID v4 | news_id 형식 명시 |

### 19.3 영향 분석

#### 19.3.1 코드 영향 범위
| 파일/모듈 | 영향도 | 수정 내용 |
|-----------|--------|-----------|
| `app/utils/elasticsearch_client.py` | 높음 | 인덱스 매핑 변경, 필드명 수정 |
| `app/services/crawler.py` | 높음 | 실제 기사 URL 추출 로직 개선 |
| `app/services/analyzer.py` | 중간 | metadata 필드 추가, analyzed_date 기록 |
| `app/routes/news.py` | 중간 | source_url 필드 참조 변경 |
| `app/templates/news/detail.html` | 낮음 | 원문 링크 필드명 변경 (이미 content로 대체됨) |
| `scripts/fix_news_data.py` | 낮음 | 마이그레이션 스크립트 갱신 |

#### 19.3.2 데이터 영향 범위
| 대상 | 영향 | 대응 방안 |
|------|------|-----------|
| 기존 ES 데이터 (13건) | 필드명 불일치 | 마이그레이션 스크립트로 갱신 |
| 신규 저장 데이터 | 필드 누락 없이 저장 필요 | 코드 수정 후 테스트 |

### 19.4 개발 작업 분해 (WBS)

#### Phase 8: SRS 개정 반영 (예상 2일)

| 작업 ID | 작업명 | 설명 | 선행 작업 | 예상 시간 |
|---------|--------|------|-----------|-----------|
| P8.T1 | ES 인덱스 매핑 수정 | `elasticsearch_client.py`의 `create_index()` 매핑 갱신 | - | 1시간 |
| P8.T2 | 크롤러 URL 추출 개선 | `source_url`에 실제 기사 URL 저장, `source_name` 추가 | - | 2시간 |
| P8.T3 | 분석기 metadata 추가 | `analyzed_date`, `metadata` 필드 생성 로직 | P8.T1 | 1시간 |
| P8.T4 | 라우트/템플릿 필드 수정 | `url` → `source_url` 참조 변경 | P8.T1 | 30분 |
| P8.T5 | 기존 데이터 마이그레이션 | 13건 데이터 필드 업데이트 스크립트 | P8.T1~T3 | 1시간 |
| P8.T6 | 단위/통합 테스트 | 변경 사항 검증 | P8.T1~T5 | 2시간 |
| P8.T7 | 문서 갱신 | README, 운영 핸드북 갱신 | P8.T6 | 30분 |

### 19.5 상세 구현 계획

#### P8.T1: ES 인덱스 매핑 수정
**파일**: `app/utils/elasticsearch_client.py`

```python
# 변경 전
"url": {"type": "keyword"},

# 변경 후
"source_url": {"type": "keyword"},
"source_name": {"type": "keyword"},
"analyzed_date": {"type": "date"},
"metadata": {
    "properties": {
        "word_count": {"type": "integer"},
        "language": {"type": "keyword"},
        "gpt_model": {"type": "keyword"}
    }
}
```

**주의사항**: 기존 인덱스가 존재하므로 인덱스 재생성 또는 매핑 업데이트 필요

#### P8.T2: 크롤러 URL 추출 개선
**파일**: `app/services/crawler.py`

**현재 문제**: `_extract_article_data()`에서 `url` 변수에 실제 기사 URL을 저장하나, 저장 시 다른 경로에서 덮어쓰기 가능

**수정 내용**:
1. 반환 딕셔너리 키를 `source_url`로 변경
2. `source_name` 필드 추가 (기본값: "Investing.com")
3. URL 추출 로직 검증 및 강화

```python
# 변경 전
return {
    'title': title,
    'content': content,
    'url': url,
    'source': 'investing.com',
    ...
}

# 변경 후
return {
    'title': title,
    'content': content,
    'source_url': url,  # 실제 기사 URL
    'source_name': 'Investing.com',
    ...
}
```

#### P8.T3: 분석기 metadata 추가
**파일**: `app/services/analyzer.py`

**수정 내용**:
1. `analyzed_date` 필드에 분석 완료 시점 기록
2. `metadata` 객체 생성:
   - `word_count`: 기사 본문 단어 수
   - `language`: 원문 언어 (영어 기본)
   - `gpt_model`: 사용된 GPT 모델명

```python
# 추가할 필드
"analyzed_date": datetime.now(timezone.utc).isoformat(),
"metadata": {
    "word_count": len(content.split()),
    "language": "en",
    "gpt_model": "gpt-4"
}
```

#### P8.T4: 라우트/템플릿 필드 수정
**파일**: `app/routes/news.py`

**수정 내용**: 기존 `url` 필드 참조를 `source_url`로 변경

```python
# 변경 전
'url': news.get('url', ''),

# 변경 후
'source_url': news.get('source_url', ''),
'source_name': news.get('source_name', 'Unknown'),
```

#### P8.T5: 기존 데이터 마이그레이션
**파일**: `scripts/migrate_es_schema_v1_1.py` (신규 생성)

**작업 내용**:
1. 기존 13개 문서 조회
2. 필드명 변경 (`url` → `source_url`, `source` → `source_name`)
3. 누락 필드 추가 (`analyzed_date`, `metadata`)
4. sentiment.classification lowercase 변환
5. 업데이트된 문서 재색인

### 19.6 테스트 계획

| 테스트 유형 | 테스트 항목 | 검증 기준 |
|-------------|-------------|-----------|
| 단위 테스트 | ES 인덱스 매핑 | 새 필드 포함 확인 |
| 단위 테스트 | 크롤러 URL 추출 | source_url에 유효한 URL 저장 |
| 단위 테스트 | 분석기 metadata | 필드 값 정상 생성 |
| 통합 테스트 | 크롤링→분석→저장 | 모든 필드 정상 저장 |
| 통합 테스트 | 뉴스 상세 페이지 | source_url 정상 표시 |
| 회귀 테스트 | 기존 기능 | 뉴스 조회, 필터링 정상 동작 |

### 19.7 롤백 계획

| 단계 | 롤백 조치 |
|------|-----------|
| ES 인덱스 | 기존 매핑 백업 후 수정, 문제 시 백업에서 복원 |
| 코드 변경 | Git 브랜치 분리 (feature/srs-v1.1), 문제 시 main 롤백 |
| 데이터 마이그레이션 | 마이그레이션 전 ES 스냅샷 생성 |

### 19.8 완료 기준

- [ ] ES 인덱스에 `source_url`, `source_name`, `analyzed_date`, `metadata` 필드 포함
- [ ] 신규 크롤링 시 `source_url`에 실제 기사 URL 저장
- [ ] `sentiment.classification`이 lowercase로 저장
- [ ] 기존 13건 데이터 마이그레이션 완료
- [ ] 뉴스 상세 페이지에서 출처 정보 정상 표시
- [ ] 단위/통합 테스트 통과율 ≥ 90%

---
## 20. 현재 구현 상태 분석 (2025-11-27 기준)

### 20.1 전체 진행률
- **전체 FR 구현률**: 약 85% (51/60)
- **핵심 기능**: 완료 (크롤링, 분석, 저장, 메일, 기본 UI)
- **미구현 핵심**: 관리자 페이지, 통계 페이지, 사용자 프로필 수정

### 20.2 구현 완료 항목

#### ✅ 사용자 관리 (FR-001~005)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-002 | 로그인 | ✅ 완료 | `routes/auth.py` |
| FR-003 | 세션 관리 | ✅ 완료 | Flask Session |
| FR-004 | 로그아웃 | ✅ 완료 | `routes/auth.py` |

#### ✅ 종목 관리 (FR-006~010)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-006 | 티커-회사명 매핑 | ✅ 완료 | `models/stock.py` |
| FR-007 | 관심 종목 추가 | ✅ 완료 | `routes/stocks.py` |
| FR-008 | 관심 종목 삭제 | ✅ 완료 | `routes/stocks.py` |
| FR-009 | 관심 종목 조회 | ✅ 완료 | `routes/stocks.py` |
| FR-010 | stock_master 유지 | ✅ 완료 | `models/stock.py` |

#### ✅ 뉴스 수집 (FR-011~017)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-011 | investing.com 소스 | ✅ 완료 | `services/crawler.py` |
| FR-012 | Selenium 크롤링 | ✅ 완료 | `services/crawler.py` |
| FR-013 | 3시간 자동 크롤링 | ✅ 완료 | `services/scheduler.py` |
| FR-014 | 최근 뉴스 수집 | ✅ 완료 | `services/crawler.py` |
| FR-015 | 종목별 뉴스 수집 | ✅ 완료 | `services/crawler.py` |
| FR-016 | 뉴스 데이터 수집 | ✅ 완료 | `services/crawler.py` |
| FR-017 | 중복 방지 | ✅ 완료 | `services/news_storage.py` |

#### ✅ 뉴스 분석 (FR-018~020)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-018 | ChatGPT API 연동 | ✅ 완료 | `services/news_analyzer.py` |
| FR-019 | 다국어 요약 + 감성분석 | ✅ 완료 | `services/news_analyzer.py` |
| FR-020 | 프롬프트 설계 | ✅ 완료 | `services/news_analyzer.py` |

#### ✅ 데이터 저장 (FR-021~028)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-021 | users 테이블 | ✅ 완료 | `models/user.py` |
| FR-022 | user_settings 테이블 | ✅ 완료 | `models/user.py` |
| FR-023 | user_stocks 테이블 | ✅ 완료 | `models/stock.py` |
| FR-024 | stock_master 테이블 | ✅ 완료 | `models/stock.py` |
| FR-025 | ES 뉴스 저장 | ✅ 완료 | `services/news_storage.py` |
| FR-026 | ES 인덱스 구조 | ✅ 완료 | `utils/elasticsearch_client.py` |
| FR-027 | 2년 보관 정책 | ✅ 완료 | `services/scheduler.py` |
| FR-028 | 오래된 데이터 삭제 | ✅ 완료 | `services/scheduler.py` |

#### ✅ 메일 발송 (FR-029~038)
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-029 | 메일 수신 시각 설정 | ✅ 완료 | `routes/settings.py` |
| FR-030 | 수신 언어 선택 | ✅ 완료 | `routes/settings.py` |
| FR-031 | Gmail SMTP 발송 | ✅ 완료 | `services/email_sender.py` |
| FR-032 | HTML 보고서 | ✅ 완료 | `templates/email/` |
| FR-033 | 메일 내용 구성 | ✅ 완료 | `services/email_sender.py` |
| FR-034 | 디자인 요구사항 | ✅ 완료 | `templates/email/` |
| FR-035 | 스케줄 메일 발송 | ✅ 완료 | `services/scheduler.py` |
| FR-036 | 새 뉴스 없음 알림 | ✅ 완료 | `services/email_sender.py` |
| FR-037 | 재시도 로직 | ✅ 완료 | `services/email_sender.py` |
| FR-038 | 발송 이력 로그 | ✅ 완료 | `services/email_sender.py` |

#### ✅ 웹 UI (FR-039~056) - 부분 완료
| FR | 항목 | 상태 | 구현 파일 |
|-----|------|------|-----------|
| FR-039 | 대시보드 메인 | ✅ 완료 | `templates/dashboard.html` |
| FR-040 | 오늘의 뉴스/통계 | ✅ 완료 | `routes/main.py` |
| FR-041 | 관심 종목 목록 | ✅ 완료 | `templates/stocks/` |
| FR-042 | 종목 추가 폼 | ✅ 완료 | `templates/stocks/` |
| FR-043 | 종목 삭제 버튼 | ✅ 완료 | `templates/stocks/` |
| FR-044 | 뉴스 히스토리 | ✅ 완료 | `templates/news/` |
| FR-045 | 날짜 필터 | ✅ 완료 | `routes/news.py` |
| FR-046 | 호재/악재 필터 | ✅ 완료 | `routes/news.py` |
| FR-047 | 페이지네이션 | ✅ 완료 | `routes/news.py` |
| FR-048 | 뉴스 상세 보기 | ✅ 완료 | `templates/news/detail.html` |
| FR-051 | 메일 시각 설정 | ✅ 완료 | `templates/settings.html` |
| FR-052 | 언어 선택 | ✅ 완료 | `templates/settings.html` |
| FR-053 | 알림 ON/OFF | ✅ 완료 | `routes/settings.py` |
| FR-054 | 테스트 메일 발송 | ✅ 완료 | `routes/settings.py` |

### 20.3 미구현 항목

#### ❌ 필수 구현 (핵심 기능 누락)
| FR | 항목 | 우선순위 | 예상 시간 |
|-----|------|----------|-----------|
| FR-001 | 관리자 사용자 등록 UI | 🔴 높음 | 2시간 |
| FR-005 | 비밀번호/이메일 변경 | 🔴 높음 | 2시간 |
| FR-049 | 종목별 호재/악재 통계 차트 | 🔴 높음 | 4시간 |
| FR-050 | 종목별 뉴스 수 통계 | 🔴 높음 | 2시간 |
| FR-055 | 비밀번호 변경 UI | 🟡 중간 | 1시간 |
| FR-056 | 이메일 변경 UI | 🟡 중간 | 1시간 |
| FR-057 | 사용자 목록 조회 | 🔴 높음 | 2시간 |
| FR-058 | 새 사용자 등록 | 🔴 높음 | 2시간 |
| FR-059 | 사용자 활성화/비활성화 | 🔴 높음 | 1시간 |
| FR-060 | 시스템 상태 모니터링 | 🔴 높음 | 3시간 |

#### ❌ 미구현 API (SRS 8장 기준)
| Method | Endpoint | 설명 | 우선순위 |
|--------|----------|------|----------|
| GET | `/api/user/profile` | 내 정보 조회 | 🟡 중간 |
| PUT | `/api/user/profile` | 내 정보 수정 | 🔴 높음 |
| GET | `/api/news/statistics` | 통계 조회 | 🔴 높음 |
| POST | `/api/admin/users` | 사용자 생성 | 🔴 높음 |
| GET | `/api/admin/users` | 사용자 목록 | 🔴 높음 |
| PUT | `/api/admin/users/{id}` | 사용자 활성화 | 🔴 높음 |
| GET | `/api/admin/system-status` | 시스템 상태 | 🔴 높음 |

#### ❌ 미구현 페이지
| 페이지 | 설명 | 관련 FR |
|--------|------|---------|
| 통계 페이지 | Chart.js 차트 시각화 | FR-049, FR-050 |
| 관리자 - 사용자 목록 | 사용자 관리 테이블 | FR-057 |
| 관리자 - 사용자 등록 | 등록 폼 | FR-058 |
| 관리자 - 시스템 상태 | 크롤링/ES/메일 상태 | FR-060 |

---
## 21. Phase 9: 미구현 기능 개발 계획 (총 3 스프린트)

### 21.1 스프린트 개요

| 스프린트 | 기간 | 목표 | 스토리 포인트 |
|----------|------|------|---------------|
| Sprint 9.1 | 1일 | 관리자 페이지 - API 및 기본 UI | 13 SP |
| Sprint 9.2 | 1일 | 통계 페이지 - ES 집계 및 차트 | 10 SP |
| Sprint 9.3 | 0.5일 | 사용자 프로필 수정 및 통합 테스트 | 8 SP |
| Sprint 9.4 | 0.5일 | 종목 검색/자동완성 기능 | 10 SP |

**총 예상 기간**: 3일 (24시간)  
**총 스토리 포인트**: 41 SP

---

### 21.2 Sprint 9.1: 관리자 페이지 (1일)

#### 📋 스프린트 목표
관리자가 사용자를 관리하고 시스템 상태를 모니터링할 수 있는 페이지 구현

#### 🎯 스프린트 백로그

| 태스크 ID | 태스크명 | 설명 | SP | 담당 | 상태 |
|-----------|----------|------|-----|------|------|
| S9.1-001 | 관리자 Blueprint 생성 | `routes/admin.py` 신규 생성, Blueprint 등록 | 1 | - | ⬜ TODO |
| S9.1-002 | @admin_required 검증 | 기존 데코레이터 동작 확인 및 테스트 | 1 | - | ⬜ TODO |
| S9.1-003 | 사용자 목록 API | `GET /api/admin/users` - 전체 사용자 조회 | 2 | - | ⬜ TODO |
| S9.1-004 | 사용자 등록 API | `POST /api/admin/users` - 신규 사용자 생성 | 2 | - | ⬜ TODO |
| S9.1-005 | 사용자 활성화 API | `PUT /api/admin/users/{id}` - 활성/비활성 토글 | 1 | - | ⬜ TODO |
| S9.1-006 | 시스템 상태 API | `GET /api/admin/system-status` - ES/크롤러/메일 상태 | 3 | - | ⬜ TODO |
| S9.1-007 | 관리자 사용자 목록 UI | `templates/admin/users.html` - 테이블 + 액션 버튼 | 2 | - | ⬜ TODO |
| S9.1-008 | 관리자 시스템 상태 UI | `templates/admin/system_status.html` - 상태 카드 | 1 | - | ⬜ TODO |

#### 📁 산출물
```
app/
├── routes/
│   └── admin.py (신규)
├── templates/
│   └── admin/
│       ├── users.html
│       └── system_status.html
```

#### ✅ 완료 조건 (DoD)
- [ ] 관리자 로그인 후 `/admin/users` 접근 가능
- [ ] 비관리자 접근 시 403 또는 리다이렉트 처리
- [ ] 사용자 목록 테이블 정상 렌더링
- [ ] 사용자 등록 폼 → DB 저장 완료
- [ ] 사용자 활성/비활성 토글 동작
- [ ] 시스템 상태 (ES 연결, 문서 수, 마지막 크롤링) 표시

#### 🔧 기술 상세

**S9.1-006: 시스템 상태 API 응답 형식**
```python
{
    "elasticsearch": {
        "status": "connected" | "disconnected",
        "documents": 57,
        "index": "news_analysis"
    },
    "crawler": {
        "last_run": "2025-11-27T17:06:00Z",
        "status": "success" | "failed",
        "articles_collected": 57
    },
    "email": {
        "last_sent": "2025-11-27T09:00:00Z",
        "status": "success" | "failed",
        "pending_count": 0
    },
    "scheduler": {
        "jobs": ["crawl_job", "email_job", "cleanup_job"],
        "status": "running" | "stopped"
    }
}
```

---

### 21.3 Sprint 9.2: 통계 페이지 (1일)

#### 📋 스프린트 목표
종목별 호재/악재 통계를 차트로 시각화하는 통계 페이지 구현

#### 🎯 스프린트 백로그

| 태스크 ID | 태스크명 | 설명 | SP | 담당 | 상태 |
|-----------|----------|------|-----|------|------|
| S9.2-001 | 통계 API 엔드포인트 | `GET /api/news/statistics` - 기본 구조 | 1 | - | ⬜ TODO |
| S9.2-002 | ES 종목별 집계 쿼리 | ticker별 positive/negative/neutral 카운트 | 3 | - | ⬜ TODO |
| S9.2-003 | ES 기간별 집계 쿼리 | 7일/30일 기간 필터 + date_histogram | 2 | - | ⬜ TODO |
| S9.2-004 | 통계 라우트 생성 | `routes/news.py`에 통계 페이지 라우트 추가 | 1 | - | ⬜ TODO |
| S9.2-005 | 통계 페이지 템플릿 | `templates/statistics.html` - 레이아웃 | 1 | - | ⬜ TODO |
| S9.2-006 | Chart.js 통합 | CDN 추가, 기본 설정 | 1 | - | ⬜ TODO |
| S9.2-007 | 호재/악재 Doughnut 차트 | 종목별 감성 비율 시각화 | 1 | - | ⬜ TODO |

#### 📁 산출물
```
app/
├── routes/
│   └── news.py (수정 - 통계 라우트 추가)
├── templates/
│   └── statistics.html (신규)
```

#### ✅ 완료 조건 (DoD)
- [ ] `/statistics` 페이지 정상 렌더링
- [ ] 기간 선택 (7일/30일) 드롭다운 동작
- [ ] 종목별 호재/악재/중립 비율 Doughnut 차트 표시
- [ ] 뉴스 없을 때 "데이터 없음" 메시지 표시
- [ ] API 응답 시간 < 2초

#### 🔧 기술 상세

**S9.2-002: ES 집계 쿼리**
```python
{
    "size": 0,
    "query": {
        "bool": {
            "filter": [
                {"range": {"crawled_date": {"gte": "now-7d"}}}
            ]
        }
    },
    "aggs": {
        "by_ticker": {
            "terms": {"field": "ticker_symbol", "size": 20},
            "aggs": {
                "sentiment_avg": {"avg": {"field": "sentiment.score"}},
                "positive": {"filter": {"term": {"sentiment.classification": "positive"}}},
                "negative": {"filter": {"term": {"sentiment.classification": "negative"}}},
                "neutral": {"filter": {"term": {"sentiment.classification": "neutral"}}}
            }
        },
        "total_count": {"value_count": {"field": "news_id"}}
    }
}
```

**Chart.js 차트 유형**:
| 차트 | 용도 | 데이터 |
|------|------|--------|
| Doughnut | 종목별 감성 비율 | positive/negative/neutral % |
| Bar | 종목별 뉴스 수 | ticker별 article count |
| Line | 일별 뉴스 추이 | date_histogram (선택적) |

---

### 21.4 Sprint 9.3: 사용자 프로필 및 마무리 (0.5일)

#### 📋 스프린트 목표
사용자 프로필 수정 기능 및 전체 통합 테스트 완료

#### 🎯 스프린트 백로그

| 태스크 ID | 태스크명 | 설명 | SP | 담당 | 상태 |
|-----------|----------|------|-----|------|------|
| S9.3-001 | 프로필 조회 API | `GET /api/user/profile` - 현재 사용자 정보 | 1 | - | ⬜ TODO |
| S9.3-002 | 프로필 수정 API | `PUT /api/user/profile` - 이메일/비밀번호 변경 | 2 | - | ⬜ TODO |
| S9.3-003 | 비밀번호 변경 검증 | 현재 비밀번호 확인 로직 | 1 | - | ⬜ TODO |
| S9.3-004 | 설정 페이지 프로필 섹션 | `settings.html` 확장 - 프로필 편집 폼 | 2 | - | ⬜ TODO |
| S9.3-005 | 네비게이션 메뉴 업데이트 | 관리자 메뉴, 통계 링크 추가 | 1 | - | ⬜ TODO |
| S9.3-006 | 통합 테스트 | 전체 기능 E2E 테스트 | 1 | - | ⬜ TODO |

#### 📁 산출물
```
app/
├── routes/
│   └── settings.py (수정 - 프로필 API 추가)
├── templates/
│   ├── settings.html (수정 - 프로필 섹션)
│   └── base.html (수정 - 네비게이션)
```

#### ✅ 완료 조건 (DoD)
- [ ] 설정 페이지에서 비밀번호 변경 가능
- [ ] 설정 페이지에서 이메일 변경 가능
- [ ] 현재 비밀번호 틀리면 에러 메시지
- [ ] 네비게이션에 "통계", "관리자" 메뉴 표시 (권한별)
- [ ] 모든 신규 API 정상 동작

#### 🔧 기술 상세

**S9.3-002: 프로필 수정 API**
```python
@settings_bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.get_json()
    current_user = get_current_user()
    
    # 비밀번호 변경
    if 'new_password' in data and data['new_password']:
        if not data.get('current_password'):
            return jsonify({'error': '현재 비밀번호를 입력해주세요'}), 400
        if not current_user.check_password(data['current_password']):
            return jsonify({'error': '현재 비밀번호가 일치하지 않습니다'}), 400
        current_user.set_password(data['new_password'])
    
    # 이메일 변경
    if 'email' in data and data['email'] != current_user.email:
        existing = User.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({'error': '이미 사용 중인 이메일입니다'}), 400
        current_user.email = data['email']
    
    db.session.commit()
    return jsonify({'success': True, 'message': '프로필이 수정되었습니다'})
```

---

### 21.5 Sprint 9.4: 종목 검색 기능 ✅ DONE (0.5일)

#### 📋 스프린트 목표
588개 종목에서 빠르게 원하는 종목을 찾을 수 있는 실시간 검색/자동완성 기능 구현

#### 🎯 스프린트 백로그

| 태스크 ID | 태스크명 | 설명 | SP | 담당 | 상태 |
|-----------|----------|------|-----|------|------|
| S9.4-001 | 종목 검색 API | `GET /stocks/api/search?q=` - 티커/회사명 검색 | 2 | - | ✅ DONE |
| S9.4-002 | 검색 쿼리 최적화 | SQLite LIKE 쿼리 + 우선순위 정렬 | 1 | - | ✅ DONE |
| S9.4-003 | 자동완성 UI 컴포넌트 | 검색창 + 드롭다운 결과 표시 | 2 | - | ✅ DONE |
| S9.4-004 | 디바운싱 구현 | 입력 300ms 후 API 호출 (과도한 요청 방지) | 1 | - | ✅ DONE |
| S9.4-005 | 종목 선택 및 추가 | 드롭다운에서 종목 클릭 시 관심종목 추가 | 1 | - | ✅ DONE |
| S9.4-006 | 이미 추가된 종목 표시 | 관심종목에 있는 항목은 체크 아이콘 표시 | 1 | - | ✅ DONE |
| S9.4-007 | 키보드 네비게이션 | 화살표 키로 결과 탐색, Enter로 선택 | 1 | - | ✅ DONE |
| S9.4-008 | 통합 테스트 | 검색 기능 E2E 테스트 | 1 | - | ✅ DONE |

#### 📁 산출물
```
app/
├── routes/
│   └── stocks.py (수정 - 검색 API 추가: search_stocks())
├── templates/
│   └── stocks/
│       └── index.html (수정 - 검색 UI + JavaScript 인라인 구현)
```

**구현 특징:**
- 우선순위 정렬: 정확히 일치 > 접두사 일치 > 부분 일치
- JavaScript 인라인 구현 (별도 JS 파일 불필요)
- CSS3 트랜지션 효과로 부드러운 UI

#### ✅ 완료 조건 (DoD)
- [x] 검색창에 2글자 이상 입력 시 자동완성 결과 표시
- [x] 티커 심볼과 회사명 모두 검색 가능
- [x] 검색 결과 최대 20개 표시
- [x] 드롭다운에서 종목 클릭 시 관심종목에 추가
- [x] 이미 관심종목인 항목은 ✓ 표시
- [x] 키보드 (↑↓ Enter Esc) 네비게이션 동작
- [x] 검색 응답 시간 < 200ms

#### 🔧 기술 상세

**S9.4-001: 종목 검색 API**
```python
@stocks_bp.route('/api/stocks/search')
@login_required
def search_stocks():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'stocks': []})
    
    # 티커 심볼 또는 회사명으로 검색 (대소문자 무시)
    search_pattern = f'%{query}%'
    stocks = StockMaster.query.filter(
        db.or_(
            StockMaster.ticker_symbol.ilike(search_pattern),
            StockMaster.company_name.ilike(search_pattern)
        )
    ).limit(20).all()
    
    # 현재 사용자의 관심종목 목록
    user_stocks = set([us.ticker_symbol for us in current_user.stocks])
    
    return jsonify({
        'stocks': [{
            'ticker': s.ticker_symbol,
            'name': s.company_name,
            'sector': s.sector,
            'exchange': s.exchange,
            'is_watchlist': s.ticker_symbol in user_stocks
        } for s in stocks]
    })
```

**S9.4-003: 자동완성 UI (HTML)**
```html
<div class="stock-search-container">
    <input type="text" 
           id="stockSearchInput" 
           class="form-control" 
           placeholder="종목 검색 (예: AAPL, Apple)"
           autocomplete="off">
    <div id="searchResults" class="search-dropdown"></div>
</div>
```

**S9.4-004: 디바운싱 JavaScript**
```javascript
let debounceTimer;
const searchInput = document.getElementById('stockSearchInput');

searchInput.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const query = this.value.trim();
    
    if (query.length < 2) {
        hideDropdown();
        return;
    }
    
    debounceTimer = setTimeout(() => {
        fetchStocks(query);
    }, 300);
});

async function fetchStocks(query) {
    const response = await fetch(`/api/stocks/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    renderDropdown(data.stocks);
}
```

**검색 결과 드롭다운 스타일**
```css
.search-dropdown {
    position: absolute;
    width: 100%;
    max-height: 400px;
    overflow-y: auto;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    z-index: 1000;
}

.search-item {
    padding: 10px 15px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.search-item:hover, .search-item.selected {
    background-color: #f5f5f5;
}

.search-item .ticker {
    font-weight: bold;
    color: #2196F3;
}

.search-item .name {
    color: #666;
    font-size: 0.9em;
}

.search-item .sector {
    font-size: 0.8em;
    color: #999;
}

.search-item .watchlist-badge {
    color: #4CAF50;
}
```

---

### 21.6 스프린트 일정표 (간트 차트)

```
Day 1 (8h)
├─ Sprint 9.1: 관리자 페이지
│  ├─ 09:00-09:30  S9.1-001, S9.1-002 (Blueprint, 데코레이터)
│  ├─ 09:30-12:00  S9.1-003, S9.1-004, S9.1-005 (사용자 API)
│  ├─ 13:00-15:00  S9.1-006 (시스템 상태 API)
│  └─ 15:00-18:00  S9.1-007, S9.1-008 (관리자 UI)

Day 2 (8h)
├─ Sprint 9.2: 통계 페이지
│  ├─ 09:00-12:00  S9.2-001, S9.2-002, S9.2-003 (통계 API + ES)
│  ├─ 13:00-15:00  S9.2-004, S9.2-005 (라우트 + 템플릿)
│  └─ 15:00-18:00  S9.2-006, S9.2-007 (Chart.js 차트)

Day 3 (8h)
├─ Sprint 9.3: 프로필 및 마무리 (4h)
│  ├─ 09:00-11:00  S9.3-001~S9.3-004 (프로필 수정)
│  └─ 11:00-13:00  S9.3-005, S9.3-006 (네비게이션 + 테스트)
│
├─ Sprint 9.4: 종목 검색 기능 (4h)
│  ├─ 14:00-15:00  S9.4-001, S9.4-002 (검색 API)
│  ├─ 15:00-16:30  S9.4-003, S9.4-004 (자동완성 UI + 디바운싱)
│  └─ 16:30-18:00  S9.4-005~S9.4-008 (선택/추가 + 테스트)
```

---

### 21.7 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 방안 |
|--------|------|------|-----------|
| ES 집계 쿼리 복잡도 | 통계 지연 | 중 | 캐싱 또는 쿼리 단순화 |
| Chart.js 호환성 | 차트 미표시 | 저 | CDN fallback, 버전 고정 |
| 프로필 수정 보안 | 비인가 접근 | 중 | 세션 검증 강화 |
| 검색 쿼리 성능 | 500+개 종목 검색 지연 | 저 | DB 인덱스 + LIMIT 20 |
| 자동완성 UX | 과도한 API 호출 | 중 | 디바운싱 300ms 적용 |

---

### 21.8 전체 완료 기준 (Phase 9 DoD)

#### 기능 완료
- [ ] 관리자 페이지에서 사용자 목록 조회/등록/활성화 가능
- [ ] 관리자 페이지에서 시스템 상태 (ES, 크롤러, 메일) 확인 가능
- [ ] 통계 페이지에서 종목별 호재/악재 차트 표시
- [ ] 통계 페이지에서 기간별 (7일/30일) 필터 동작
- [ ] 설정 페이지에서 비밀번호 변경 가능
- [ ] 설정 페이지에서 이메일 변경 가능
- [ ] 네비게이션에 통계/관리자 메뉴 권한별 표시
- [ ] 종목 검색 시 실시간 자동완성 동작
- [ ] 검색 결과에서 종목 선택 시 관심종목 추가
- [ ] 이미 관심종목인 항목 구분 표시

#### 품질 기준
- [ ] 모든 API 엔드포인트 정상 응답 (200/201/4xx)
- [ ] 비관리자 접근 시 403 또는 리다이렉트
- [ ] 페이지 로딩 시간 < 3초
- [ ] 종목 검색 응답 시간 < 200ms
- [ ] 콘솔 에러 없음

#### 문서화
- [ ] API 엔드포인트 README 업데이트
- [ ] 관리자 가이드 작성 (선택적)

---
## 22. 크롤러 성능 개선 현황 (2025-11-27)

### 22.1 멀티스레드 크롤링 도입
- **구현 완료**: `batch_crawl_parallel()` 함수
- **성능 향상**: 5개 워커 동시 실행
- **성공률**: 60% (6/10 종목) → 기존 20% 대비 3배 향상

### 22.2 봇 차단 우회 전략
| 전략 | 상태 | 설명 |
|------|------|------|
| User-Agent 로테이션 | ✅ 구현 | 7개 UA 랜덤 선택 |
| 프록시 인프라 | ✅ 준비 | `PROXY_LIST` + `get_next_proxy()` |
| 랜덤 딜레이 | ✅ 구현 | 10-15초 랜덤 대기 |
| 멀티스레드 | ✅ 구현 | ThreadPoolExecutor 5 workers |

### 22.3 향후 개선 사항
- 실제 프록시 서버 추가 시 성공률 추가 향상 예상
- Playwright 전환 검토 (더 나은 안티봇 우회)

---
## 23. 문서 개정 이력
| 버전 | 날짜 | 작성자 | 변경 내용 |
|-------|------|--------|-----------|
| 0.1 | 2025-11-20 | Copilot | 초안 작성 |
| 0.2 | 2025-11-27 | Copilot | SRS v1.1 개정 반영 개발 계획 추가 (Phase 8) |
| 0.3 | 2025-11-27 | Copilot | 현재 구현 상태 분석 및 Phase 9 미구현 기능 개발 계획 추가 |
| 0.4 | 2025-11-28 | Copilot | Sprint 9.4 종목 검색/자동완성 기능 개발 계획 추가 |

(끝)
