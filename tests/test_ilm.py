"""
ILM 정책 검증 테스트
Phase 2.2 - ILM Policy
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from app.utils.elasticsearch_client import get_es_client
from app.utils.config import Config


class TestILMPolicy:
    """ILM 정책 테스트"""
    
    @pytest.fixture
    def es_client(self):
        """ES 클라이언트 픽스처"""
        return get_es_client()
    
    def test_ilm_policy_creation(self, es_client):
        """ILM 정책 생성 테스트"""
        policy_name = "news_retention_policy"
        
        # 정책 정의
        policy_body = {
            "phases": {
                "hot": {
                    "min_age": "0ms",
                    "actions": {
                        "rollover": {
                            "max_age": "30d",
                            "max_size": "50gb"
                        },
                        "set_priority": {
                            "priority": 100
                        }
                    }
                },
                "warm": {
                    "min_age": "90d",
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
                    "min_age": "730d",
                    "actions": {
                        "delete": {}
                    }
                }
            }
        }
        
        # 정책 생성
        es_client.client.ilm.put_lifecycle(
            policy=policy_name,
            body={"policy": policy_body}
        )
        
        # 정책 존재 확인
        policies = es_client.client.ilm.get_lifecycle()
        assert policy_name in policies, f"정책 '{policy_name}'이 생성되지 않음"
        print(f"✓ ILM 정책 '{policy_name}' 생성 성공")
    
    def test_ilm_policy_phases(self, es_client):
        """ILM 정책 단계 검증 (SRS 3.5.3)"""
        policy_name = "news_retention_policy"
        
        # 정책 조회
        policies = es_client.client.ilm.get_lifecycle()
        assert policy_name in policies
        
        policy = policies[policy_name]['policy']
        phases = policy['phases']
        
        # Hot 단계 검증
        assert 'hot' in phases, "Hot 단계 누락"
        assert phases['hot']['min_age'] == '0ms'
        assert 'rollover' in phases['hot']['actions']
        rollover = phases['hot']['actions']['rollover']
        assert rollover['max_age'] == '30d'
        assert rollover['max_size'] == '50gb'
        print("✓ Hot 단계: 30일 또는 50GB 롤오버 설정 확인")
        
        # Warm 단계 검증
        assert 'warm' in phases, "Warm 단계 누락"
        assert phases['warm']['min_age'] == '90d'
        assert 'shrink' in phases['warm']['actions']
        print("✓ Warm 단계: 90일 후 샤드 축소 설정 확인")
        
        # Delete 단계 검증 (2년 = 730일)
        assert 'delete' in phases, "Delete 단계 누락"
        assert phases['delete']['min_age'] == '730d'
        assert 'delete' in phases['delete']['actions']
        print("✓ Delete 단계: 730일(2년) 후 삭제 설정 확인")
    
    def test_ilm_apply_to_index(self, es_client):
        """인덱스에 ILM 정책 적용 테스트"""
        index_name = Config.ELASTICSEARCH_INDEX
        policy_name = "news_retention_policy"
        
        # 인덱스 존재 확인
        if not es_client.client.indices.exists(index=index_name):
            # 인덱스 생성
            es_client.create_index()
        
        # ILM 정책 적용
        es_client.client.indices.put_settings(
            index=index_name,
            body={
                "index.lifecycle.name": policy_name,
                "index.lifecycle.rollover_alias": f"{index_name}_alias"
            }
        )
        
        # 적용 확인
        settings = es_client.client.indices.get_settings(index=index_name)
        lifecycle = settings[index_name]['settings']['index'].get('lifecycle', {})
        
        assert lifecycle.get('name') == policy_name, "ILM 정책이 적용되지 않음"
        assert lifecycle.get('rollover_alias') == f"{index_name}_alias"
        print(f"✓ 인덱스 '{index_name}'에 ILM 정책 적용 완료")
        print(f"  - Policy: {lifecycle['name']}")
        print(f"  - Rollover Alias: {lifecycle['rollover_alias']}")
    
    def test_ilm_explain(self, es_client):
        """ILM 설명 API 테스트"""
        index_name = Config.ELASTICSEARCH_INDEX
        
        # ILM 설명 조회
        explain = es_client.client.ilm.explain_lifecycle(index=index_name)
        
        assert index_name in explain['indices']
        index_info = explain['indices'][index_name]
        
        # 정책 적용 확인
        assert 'policy' in index_info or 'managed' in index_info
        print(f"✓ ILM Explain API 응답:")
        print(f"  - Index: {index_name}")
        if 'policy' in index_info:
            print(f"  - Policy: {index_info['policy']}")
        if 'phase' in index_info:
            print(f"  - Current Phase: {index_info['phase']}")
    
    def test_retention_period(self, es_client):
        """보관 기간 설정 검증"""
        policy_name = "news_retention_policy"
        
        policies = es_client.client.ilm.get_lifecycle()
        policy = policies[policy_name]['policy']
        
        # Delete 단계 보관 기간 확인 (SRS: 2년)
        delete_phase = policy['phases']['delete']
        min_age = delete_phase['min_age']
        
        # 730d = 2년
        assert min_age == '730d', f"보관 기간이 2년(730d)이 아님: {min_age}"
        print(f"✓ 데이터 보관 기간: {min_age} (2년)")
        
        # 일수로 변환 검증
        days = int(min_age.replace('d', ''))
        assert days == 730, f"보관 일수가 730일이 아님: {days}"
        years = days / 365
        print(f"  - {days}일 = {years:.1f}년")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
