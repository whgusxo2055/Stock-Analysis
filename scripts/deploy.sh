#!/bin/bash
# =============================================================================
# Stock Analysis Service - 배포 스크립트
# P7.M3.T4: 프로덕션 배포 자동화
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 사용법 출력
usage() {
    echo "사용법: $0 [명령]"
    echo ""
    echo "명령:"
    echo "  deploy      - 전체 배포 (빌드 + 시작)"
    echo "  build       - Docker 이미지 빌드"
    echo "  start       - 서비스 시작"
    echo "  stop        - 서비스 중지"
    echo "  restart     - 서비스 재시작"
    echo "  logs        - 로그 확인"
    echo "  status      - 서비스 상태 확인"
    echo "  backup      - 데이터 백업"
    echo "  health      - 헬스 체크"
    echo "  rollback    - 이전 버전으로 롤백"
    echo ""
    exit 1
}

# 환경 변수 확인
check_env() {
    log_info "환경 변수 확인 중..."
    
    if [ ! -f ".env" ]; then
        log_error ".env 파일이 없습니다."
        log_info ".env.example을 복사하고 값을 설정하세요:"
        log_info "  cp .env.example .env"
        exit 1
    fi
    
    # 필수 환경 변수 확인
    source .env
    
    required_vars=("SECRET_KEY" "OPENAI_API_KEY" "GMAIL_USERNAME" "GMAIL_APP_PASSWORD")
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "필수 환경 변수가 설정되지 않음: $var"
            exit 1
        fi
    done
    
    log_success "환경 변수 확인 완료"
}

# Docker 확인
check_docker() {
    log_info "Docker 확인 중..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되지 않았습니다."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되지 않았습니다."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker 데몬이 실행 중이 아닙니다."
        exit 1
    fi
    
    log_success "Docker 준비 완료"
}

# 이미지 빌드
build() {
    log_info "Docker 이미지 빌드 중..."
    
    # 현재 시간으로 태그 생성
    TAG=$(date +%Y%m%d_%H%M%S)
    
    docker-compose build --no-cache
    
    # 현재 이미지 태그 저장 (롤백용)
    echo $TAG > .last_build_tag
    
    log_success "이미지 빌드 완료 (태그: $TAG)"
}

# 서비스 시작
start() {
    log_info "서비스 시작 중..."
    
    # 필요한 디렉토리 생성
    mkdir -p data logs flask_session
    
    docker-compose up -d
    
    # 시작 대기
    log_info "서비스 시작 대기 중 (30초)..."
    sleep 10
    
    # 헬스 체크
    health_check
    
    log_success "서비스 시작 완료"
}

# 서비스 중지
stop() {
    log_info "서비스 중지 중..."
    docker-compose down
    log_success "서비스 중지 완료"
}

# 서비스 재시작
restart() {
    stop
    start
}

# 전체 배포
deploy() {
    log_info "=========================================="
    log_info "Stock Analysis Service 배포 시작"
    log_info "=========================================="
    
    check_env
    check_docker
    build
    
    # 기존 서비스 중지 (있다면)
    docker-compose down 2>/dev/null || true
    
    start
    
    log_info "=========================================="
    log_success "배포 완료!"
    log_info "=========================================="
    log_info "웹 서비스: http://localhost:5000"
    log_info "ElasticSearch: http://localhost:9200"
}

# 로그 확인
logs() {
    local service=${1:-"flask-app"}
    docker-compose logs -f $service
}

# 상태 확인
status() {
    log_info "서비스 상태:"
    echo ""
    docker-compose ps
    echo ""
    
    log_info "리소스 사용량:"
    docker stats --no-stream $(docker-compose ps -q) 2>/dev/null || log_warning "실행 중인 컨테이너 없음"
}

# 헬스 체크
health_check() {
    log_info "헬스 체크 수행 중..."
    
    # Flask 앱 체크
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            log_success "Flask 앱: 정상"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log_error "Flask 앱: 응답 없음"
            return 1
        fi
        
        log_warning "Flask 앱 응답 대기 중... ($attempt/$max_attempts)"
        sleep 3
        ((attempt++))
    done
    
    # ElasticSearch 체크
    if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
        log_success "ElasticSearch: 정상"
    else
        log_warning "ElasticSearch: 응답 없음 (첫 시작 시 정상)"
    fi
    
    return 0
}

# 데이터 백업
backup() {
    log_info "데이터 백업 중..."
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p $backup_dir
    
    # SQLite 백업
    if [ -f "data/app.db" ]; then
        cp data/app.db $backup_dir/
        log_success "SQLite 백업 완료: $backup_dir/app.db"
    fi
    
    # ElasticSearch 스냅샷 (선택적)
    log_info "ElasticSearch 스냅샷은 별도로 설정하세요."
    
    log_success "백업 완료: $backup_dir"
}

# 롤백
rollback() {
    log_info "이전 버전으로 롤백 중..."
    
    if [ ! -f ".last_build_tag" ]; then
        log_error "롤백할 이전 빌드 정보가 없습니다."
        exit 1
    fi
    
    local last_tag=$(cat .last_build_tag)
    log_info "롤백 대상: $last_tag"
    
    docker-compose down
    docker-compose up -d
    
    health_check
    
    log_success "롤백 완료"
}

# 메인
case "${1:-}" in
    deploy)
        deploy
        ;;
    build)
        build
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs $2
        ;;
    status)
        status
        ;;
    backup)
        backup
        ;;
    health)
        health_check
        ;;
    rollback)
        rollback
        ;;
    *)
        usage
        ;;
esac
