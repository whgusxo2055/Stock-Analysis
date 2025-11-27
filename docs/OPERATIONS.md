# =============================================================================
# Stock Analysis Service - 운영 핸드북
# =============================================================================
# 작성일: 2025-01-06
# 버전: 1.0.0
# =============================================================================

## 📋 목차

1. [서비스 개요](#서비스-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [서비스 관리](#서비스-관리)
4. [모니터링](#모니터링)
5. [트러블슈팅](#트러블슈팅)
6. [백업 및 복구](#백업-및-복구)
7. [보안 가이드](#보안-가이드)
8. [성능 튜닝](#성능-튜닝)

---

## 서비스 개요

### 서비스 설명
Stock Analysis Service는 사용자가 등록한 미국 주식에 대한 최신 뉴스를 자동으로 수집하고, 
GPT-4를 활용하여 뉴스를 분석한 후 이메일로 알림을 보내는 서비스입니다.

### 핵심 기능
- **뉴스 크롤링**: Yahoo Finance에서 주식 관련 뉴스 수집
- **AI 분석**: OpenAI GPT-4를 통한 뉴스 요약 및 감성 분석
- **이메일 알림**: 분석 결과를 사용자 이메일로 발송
- **검색 기능**: ElasticSearch 기반 뉴스 검색

### 서비스 URL
- **웹 애플리케이션**: http://localhost:5001
- **ElasticSearch**: http://localhost:9200

---

## 시스템 아키텍처

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   사용자 브라우저  │────▶│   Flask App     │────▶│   SQLite DB     │
└─────────────────┘     │   (Gunicorn)    │     └─────────────────┘
                        └────────┬────────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ElasticSearch  │     │   OpenAI API    │     │   Gmail SMTP    │
│   (뉴스 검색)    │     │  (뉴스 분석)     │     │  (이메일 발송)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 컴포넌트 설명
| 컴포넌트 | 설명 | 포트 |
|---------|------|------|
| Flask App | 웹 애플리케이션 서버 | 5001 |
| Gunicorn | WSGI 서버 | - |
| SQLite | 사용자/종목 데이터 저장 | - |
| ElasticSearch | 뉴스 데이터 검색 엔진 | 9200 |
| APScheduler | 백그라운드 작업 스케줄러 | - |

---

## 서비스 관리

### 서비스 시작

```bash
# 배포 스크립트 사용
./scripts/deploy.sh deploy

# 또는 Docker Compose 직접 사용
docker-compose up -d
```

### 서비스 중지

```bash
# 서비스 중지
docker-compose down

# 볼륨 포함 중지 (데이터 삭제됨!)
docker-compose down -v
```

### 서비스 재시작

```bash
# 특정 서비스만 재시작
docker-compose restart flask-app

# 전체 재시작
docker-compose restart
```

### 서비스 상태 확인

```bash
# 배포 스크립트 사용
./scripts/deploy.sh status

# 또는 직접 확인
docker-compose ps
docker-compose logs -f
```

### 로그 확인

```bash
# 전체 로그
./scripts/deploy.sh logs

# Flask 앱 로그만
docker-compose logs -f flask-app

# ElasticSearch 로그만
docker-compose logs -f elasticsearch

# 로그 파일 확인
tail -f logs/app.log
tail -f logs/crawler.log
```

### 롤백

```bash
# 이전 버전으로 롤백
./scripts/deploy.sh rollback
```

---

## 모니터링

### 헬스체크 엔드포인트

```bash
# Flask 앱 상태
curl http://localhost:5001/health

# ElasticSearch 상태
curl http://localhost:9200/_cluster/health
```

### 주요 모니터링 항목

#### 1. 서비스 가용성
- Flask 앱 응답 시간 (목표: 3초 이내)
- ElasticSearch 쿼리 응답 시간 (목표: 1초 이내)

#### 2. 크롤링 상태
```sql
-- 최근 크롤링 로그 확인
SELECT * FROM crawl_log ORDER BY created_at DESC LIMIT 10;
```

#### 3. 이메일 발송 상태
```sql
-- 최근 이메일 발송 로그
SELECT * FROM email_log ORDER BY sent_at DESC LIMIT 10;
```

#### 4. 리소스 사용량
```bash
# Docker 리소스 모니터링
docker stats

# 디스크 사용량
df -h
du -sh data/
```

### 알림 설정 권장사항

| 항목 | 경고 임계값 | 심각 임계값 |
|------|-----------|-----------|
| 응답 시간 | > 2초 | > 5초 |
| 에러율 | > 1% | > 5% |
| 디스크 사용량 | > 70% | > 90% |
| 메모리 사용량 | > 80% | > 95% |

---

## 트러블슈팅

### 자주 발생하는 문제

#### 1. 서비스가 시작되지 않음

**증상**: `docker-compose up` 실행 후 서비스 접속 불가

**확인 사항**:
```bash
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인
docker-compose logs flask-app
```

**해결 방법**:
- `.env` 파일 존재 여부 확인
- 필수 환경 변수 설정 확인
- 포트 충돌 확인: `lsof -i :5001`

#### 2. 크롤링이 동작하지 않음

**증상**: 뉴스가 수집되지 않음

**확인 사항**:
```bash
# 크롤링 로그 확인
grep "crawler" logs/app.log | tail -20

# 스케줄러 상태 확인
docker-compose exec flask-app python -c "from app import scheduler; print(scheduler.get_jobs())"
```

**해결 방법**:
- Selenium 컨테이너 상태 확인
- 네트워크 연결 확인
- Yahoo Finance 사이트 접근 가능 여부 확인

#### 3. 이메일 발송 실패

**증상**: 이메일 알림이 도착하지 않음

**확인 사항**:
```bash
# 이메일 로그 확인
grep "email" logs/app.log | tail -20
```

**해결 방법**:
- Gmail 앱 비밀번호 확인
- SMTP 설정 확인
- Gmail 보안 설정 확인 (2단계 인증)

#### 4. ElasticSearch 연결 실패

**증상**: 검색 기능 동작 불가

**확인 사항**:
```bash
# ES 상태 확인
curl http://localhost:9200/_cluster/health

# ES 컨테이너 로그
docker-compose logs elasticsearch
```

**해결 방법**:
- ElasticSearch 컨테이너 재시작
- 메모리 설정 확인 (최소 1GB 권장)
- 디스크 공간 확인

#### 5. OpenAI API 오류

**증상**: 뉴스 분석 결과가 없음

**확인 사항**:
```bash
# API 키 테스트
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**해결 방법**:
- API 키 유효성 확인
- API 사용량 및 한도 확인
- 네트워크 연결 확인

---

## 백업 및 복구

### 백업 대상

| 데이터 | 위치 | 백업 주기 |
|--------|------|----------|
| SQLite DB | `data/app.db` | 매일 |
| 로그 파일 | `logs/` | 매주 |
| 환경 설정 | `.env` | 변경시 |

### 백업 스크립트

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR=/backup/stockanalysis
DATE=$(date +%Y%m%d_%H%M%S)

# 디렉토리 생성
mkdir -p $BACKUP_DIR

# SQLite 백업
sqlite3 data/app.db ".backup $BACKUP_DIR/app_$DATE.db"

# 로그 백업
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# 환경 설정 백업
cp .env $BACKUP_DIR/env_$DATE

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 복구 절차

1. **서비스 중지**
   ```bash
   docker-compose down
   ```

2. **데이터 복구**
   ```bash
   # SQLite DB 복구
   cp /backup/stockanalysis/app_YYYYMMDD.db data/app.db
   ```

3. **서비스 시작**
   ```bash
   docker-compose up -d
   ```

4. **데이터 검증**
   ```bash
   # DB 상태 확인
   sqlite3 data/app.db "SELECT COUNT(*) FROM user;"
   ```

---

## 보안 가이드

### API 키 관리

1. **환경 변수 사용**: 코드에 직접 키를 포함하지 않음
2. **`.env` 파일 보호**: `.gitignore`에 포함
3. **정기적 키 로테이션**: 3개월마다 API 키 변경 권장

### 네트워크 보안

```bash
# 방화벽 설정 (UFW 예시)
sudo ufw allow 5001/tcp  # Flask 앱
sudo ufw deny 9200/tcp   # ElasticSearch (외부 차단)
```

### 데이터 보안

- 사용자 비밀번호: bcrypt 해싱
- 세션 관리: Flask-Login 기반
- HTTPS: 프로덕션 환경에서 필수

### 보안 체크리스트

- [ ] SECRET_KEY 변경
- [ ] 기본 포트 변경 고려
- [ ] 디버그 모드 비활성화 (`FLASK_ENV=production`)
- [ ] HTTPS 적용
- [ ] 방화벽 설정
- [ ] 정기적 보안 업데이트

---

## 성능 튜닝

### Gunicorn 설정

```python
# gunicorn.conf.py
workers = 2                    # CPU 코어 수에 맞게 조정
threads = 4                    # 스레드 수
worker_class = 'gthread'       # 스레드 기반 워커
timeout = 120                  # 요청 타임아웃
keepalive = 5                  # Keep-Alive 연결 유지
max_requests = 1000            # 워커 재시작 주기
max_requests_jitter = 50       # 재시작 시간 분산
```

### ElasticSearch 최적화

```yaml
# elasticsearch.yml
indices.memory.index_buffer_size: 30%
indices.queries.cache.size: 10%
thread_pool.search.size: 4
thread_pool.search.queue_size: 1000
```

### 데이터베이스 최적화

```sql
-- 인덱스 추가
CREATE INDEX idx_user_stock_user ON user_stock(user_id);
CREATE INDEX idx_email_log_user ON email_log(user_id);
CREATE INDEX idx_crawl_log_date ON crawl_log(created_at);
```

### 성능 지표 목표

| 항목 | 목표값 | 측정 방법 |
|------|-------|----------|
| 페이지 로딩 | ≤ 3초 | 웹 페이지 응답 시간 |
| API 응답 | ≤ 1초 | API 엔드포인트 응답 시간 |
| 뉴스 분석 | ≤ 5초/건 | 단일 뉴스 분석 시간 |
| ES 쿼리 | ≤ 1초 | 검색 쿼리 응답 시간 |

---

## 연락처

### 기술 지원
- 이슈 트래커: GitHub Issues
- 문서: README.md, SRS.md

### 긴급 대응
1. 서비스 모니터링 확인
2. 로그 분석
3. 필요시 롤백 수행
4. 근본 원인 분석 후 수정

---

**문서 버전**: 1.0.0  
**최종 수정**: 2025-01-06
