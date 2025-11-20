"""
ElasticSearch ILM(Index Lifecycle Management) 정책 설정
SRS 3.5.3 (FR-027, FR-028) 참조 - 2년 데이터 보관
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.elasticsearch_client import get_es_client
from app.utils.config import Config


def create_ilm_policy():
    """
    2년(730일) 보관 ILM 정책 생성
    """
    print("="*60)
    print("ILM Policy Setup")
    print("="*60)
    
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    print(f"✓ ElasticSearch 연결 성공")
    
    # ILM 정책 이름
    policy_name = "news_retention_policy"
    
    # 정책 정의 (SRS 3.5.3: 2년 보관)
    policy_body = {
        "policy": {
            "phases": {
                "hot": {
                    "min_age": "0ms",
                    "actions": {
                        "rollover": {
                            "max_age": "30d",  # 30일마다 롤오버
                            "max_size": "50gb"  # 또는 50GB 도달 시
                        },
                        "set_priority": {
                            "priority": 100
                        }
                    }
                },
                "warm": {
                    "min_age": "90d",  # 90일 후 warm 단계
                    "actions": {
                        "set_priority": {
                            "priority": 50
                        },
                        "shrink": {
                            "number_of_shards": 1
                        }
                    }
                },
                "delete": {
                    "min_age": "730d",  # 2년(730일) 후 삭제
                    "actions": {
                        "delete": {}
                    }
                }
            }
        }
    }
    
    try:
        # 기존 정책 확인
        existing_policies = es_client.client.ilm.get_lifecycle()
        
        if policy_name in existing_policies:
            print(f"ℹ️  정책 '{policy_name}'이 이미 존재합니다")
            
            # 기존 정책 업데이트
            print(f"📝 정책 업데이트 중...")
            es_client.client.ilm.put_lifecycle(
                policy=policy_name,
                body=policy_body
            )
            print(f"✓ 정책 '{policy_name}' 업데이트 완료")
        else:
            # 새 정책 생성
            print(f"📝 정책 생성 중: {policy_name}")
            es_client.client.ilm.put_lifecycle(
                policy=policy_name,
                body=policy_body
            )
            print(f"✓ 정책 '{policy_name}' 생성 완료")
        
        # 정책 정보 출력
        print(f"\n📊 ILM 정책 정보:")
        print(f"   - 정책 이름: {policy_name}")
        print(f"   - Hot 단계: 0일~ (롤오버: 30일 또는 50GB)")
        print(f"   - Warm 단계: 90일~ (샤드 축소)")
        print(f"   - Delete 단계: 730일(2년) 후 자동 삭제")
        
        return True
        
    except Exception as e:
        print(f"❌ ILM 정책 설정 실패: {e}")
        return False


def apply_ilm_to_index():
    """
    news_analysis 인덱스에 ILM 정책 적용
    """
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    index_name = Config.ELASTICSEARCH_INDEX
    policy_name = "news_retention_policy"
    
    # 인덱스 존재 확인
    if not es_client.client.indices.exists(index=index_name):
        print(f"❌ 인덱스 '{index_name}'가 존재하지 않습니다")
        print("💡 먼저 'python scripts/setup_es_index.py create' 실행")
        return False
    
    try:
        print(f"\n📌 인덱스에 ILM 정책 적용 중...")
        
        # 인덱스 설정 업데이트
        es_client.client.indices.put_settings(
            index=index_name,
            body={
                "index.lifecycle.name": policy_name,
                "index.lifecycle.rollover_alias": f"{index_name}_alias"
            }
        )
        
        print(f"✓ 인덱스 '{index_name}'에 정책 '{policy_name}' 적용 완료")
        
        # 적용된 설정 확인
        settings = es_client.client.indices.get_settings(index=index_name)
        lifecycle_settings = settings[index_name]['settings']['index'].get('lifecycle', {})
        
        print(f"\n📊 적용된 ILM 설정:")
        print(f"   - Policy: {lifecycle_settings.get('name', 'N/A')}")
        print(f"   - Rollover Alias: {lifecycle_settings.get('rollover_alias', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ILM 정책 적용 실패: {e}")
        return False


def show_ilm_status():
    """
    ILM 정책 상태 조회
    """
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    policy_name = "news_retention_policy"
    
    try:
        # 정책 존재 확인
        policies = es_client.client.ilm.get_lifecycle()
        
        if policy_name not in policies:
            print(f"❌ 정책 '{policy_name}'이 존재하지 않습니다")
            return False
        
        # 정책 정보 출력
        policy = policies[policy_name]
        print(f"\n📊 ILM 정책 '{policy_name}' 상태:")
        print(f"   - Version: {policy.get('version', 'N/A')}")
        print(f"   - Modified Date: {policy.get('modified_date', 'N/A')}")
        
        # 단계별 정보
        phases = policy['policy']['phases']
        print(f"\n   단계 정보:")
        
        if 'hot' in phases:
            hot = phases['hot']
            print(f"   - Hot: {hot.get('min_age', '0ms')}")
            if 'actions' in hot and 'rollover' in hot['actions']:
                rollover = hot['actions']['rollover']
                print(f"     · Rollover: {rollover.get('max_age', 'N/A')} / {rollover.get('max_size', 'N/A')}")
        
        if 'warm' in phases:
            warm = phases['warm']
            print(f"   - Warm: {warm.get('min_age', 'N/A')}")
        
        if 'delete' in phases:
            delete_phase = phases['delete']
            print(f"   - Delete: {delete_phase.get('min_age', 'N/A')}")
        
        # 인덱스 적용 상태
        index_name = Config.ELASTICSEARCH_INDEX
        if es_client.client.indices.exists(index=index_name):
            settings = es_client.client.indices.get_settings(index=index_name)
            lifecycle = settings[index_name]['settings']['index'].get('lifecycle', {})
            
            print(f"\n   인덱스 '{index_name}' 적용 상태:")
            print(f"   - Applied: {'Yes' if lifecycle.get('name') == policy_name else 'No'}")
            if lifecycle.get('name') == policy_name:
                print(f"   - Rollover Alias: {lifecycle.get('rollover_alias', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ILM 상태 조회 실패: {e}")
        return False


def delete_ilm_policy():
    """
    ILM 정책 삭제
    """
    es_client = get_es_client()
    
    if not es_client.is_connected():
        print("❌ ElasticSearch 연결 실패!")
        return False
    
    policy_name = "news_retention_policy"
    
    try:
        es_client.client.ilm.delete_lifecycle(policy=policy_name)
        print(f"✓ 정책 '{policy_name}' 삭제 완료")
        return True
    except Exception as e:
        print(f"❌ 정책 삭제 실패: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ElasticSearch ILM 정책 관리')
    parser.add_argument('action',
                       choices=['create', 'apply', 'status', 'delete', 'setup'],
                       help='수행할 작업')
    args = parser.parse_args()
    
    if args.action == 'create':
        create_ilm_policy()
    
    elif args.action == 'apply':
        apply_ilm_to_index()
    
    elif args.action == 'status':
        show_ilm_status()
    
    elif args.action == 'delete':
        confirm = input("⚠️  정말로 ILM 정책을 삭제하시겠습니까? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_ilm_policy()
        else:
            print("취소되었습니다")
    
    elif args.action == 'setup':
        # 정책 생성 + 인덱스 적용 한번에
        print("📦 ILM 정책 전체 설정 시작\n")
        if create_ilm_policy():
            print()
            apply_ilm_to_index()
