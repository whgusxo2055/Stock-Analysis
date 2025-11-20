"""
ElasticSearch 인덱스 설정 스크립트
SRS 7.2.1 참조
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.elasticsearch_client import get_es_client
from app.utils.config import Config


def setup_index():
    """
    news_analysis 인덱스 설정 및 생성
    """
    print("="*60)
    print("ElasticSearch Index Setup")
    print("="*60)
    
    # ES 클라이언트 가져오기
    es_client = get_es_client()
    
    # 연결 확인
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        print(f"   URL: {Config.ELASTICSEARCH_URL}")
        print("\n💡 해결 방법:")
        print("   1. docker-compose up -d 로 ElasticSearch 시작")
        print("   2. URL이 올바른지 확인 (.env 파일)")
        return False
    
    print(f"✓ ElasticSearch 연결 성공: {Config.ELASTICSEARCH_URL}")
    
    # 인덱스 생성
    print(f"\n📝 인덱스 생성 중: {Config.ELASTICSEARCH_INDEX}")
    
    if es_client.create_index():
        print(f"✓ 인덱스 '{Config.ELASTICSEARCH_INDEX}' 생성 완료!")
        
        # 인덱스 정보 출력
        info = es_client.client.indices.get(index=Config.ELASTICSEARCH_INDEX)
        print(f"\n📊 인덱스 정보:")
        print(f"   - Shards: {info[Config.ELASTICSEARCH_INDEX]['settings']['index']['number_of_shards']}")
        print(f"   - Replicas: {info[Config.ELASTICSEARCH_INDEX]['settings']['index']['number_of_replicas']}")
        
        # 매핑 정보 출력
        mappings = info[Config.ELASTICSEARCH_INDEX]['mappings']['properties']
        print(f"   - 필드 수: {len(mappings)}")
        print(f"   - 주요 필드: {', '.join(list(mappings.keys())[:5])}...")
        
        return True
    else:
        print(f"❌ 인덱스 생성 실패!")
        return False


def delete_index():
    """
    기존 인덱스 삭제 (재설정 시 사용)
    """
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    index_name = Config.ELASTICSEARCH_INDEX
    
    if es_client.client.indices.exists(index=index_name):
        print(f"⚠️  기존 인덱스 '{index_name}' 삭제 중...")
        es_client.client.indices.delete(index=index_name)
        print(f"✓ 인덱스 삭제 완료")
        return True
    else:
        print(f"ℹ️  인덱스 '{index_name}'가 존재하지 않습니다")
        return False


def show_index_info():
    """
    인덱스 정보 조회
    """
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    index_name = Config.ELASTICSEARCH_INDEX
    
    if not es_client.client.indices.exists(index=index_name):
        print(f"❌ 인덱스 '{index_name}'가 존재하지 않습니다")
        return False
    
    # 인덱스 통계
    stats = es_client.client.indices.stats(index=index_name)
    count = es_client.client.count(index=index_name)
    
    print(f"\n📊 인덱스 '{index_name}' 정보:")
    print(f"   - 문서 수: {count['count']}")
    print(f"   - 크기: {stats['_all']['total']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB")
    print(f"   - 상태: {stats['_all']['health']}")
    
    # 매핑 정보
    mappings = es_client.client.indices.get_mapping(index=index_name)
    fields = mappings[index_name]['mappings']['properties']
    print(f"   - 필드 수: {len(fields)}")
    
    return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ElasticSearch 인덱스 관리')
    parser.add_argument('action', 
                       choices=['create', 'delete', 'recreate', 'info'], 
                       help='수행할 작업')
    args = parser.parse_args()
    
    if args.action == 'create':
        setup_index()
    
    elif args.action == 'delete':
        confirm = input("⚠️  정말로 인덱스를 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_index()
        else:
            print("취소되었습니다")
    
    elif args.action == 'recreate':
        confirm = input("⚠️  인덱스를 삭제하고 재생성하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_index()
            print()
            setup_index()
        else:
            print("취소되었습니다")
    
    elif args.action == 'info':
        show_index_info()
