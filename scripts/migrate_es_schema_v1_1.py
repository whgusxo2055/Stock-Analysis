#!/usr/bin/env python3
"""
ElasticSearch 스키마 마이그레이션 스크립트 (SRS v1.1)

기존 데이터의 필드명을 업데이트:
- url → source_url
- source → source_name (이미 source가 있는 경우)
- sentiment.classification → lowercase 변환
- analyzed_date, metadata 필드 추가
"""

import sys
import os
from datetime import datetime, timezone

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch


def migrate_documents():
    """기존 문서를 SRS v1.1 스키마로 마이그레이션"""
    
    es = Elasticsearch(['http://localhost:9200'])
    index_name = 'news_analysis'
    
    # 연결 확인
    if not es.ping():
        print("❌ ElasticSearch 연결 실패")
        return False
    
    print("✓ ElasticSearch 연결 성공")
    
    # 모든 문서 조회
    try:
        result = es.search(
            index=index_name,
            query={'match_all': {}},
            size=1000
        )
    except Exception as e:
        print(f"❌ 문서 조회 실패: {e}")
        return False
    
    total = result['hits']['total']['value']
    print(f"\n📊 총 {total}개 문서 발견")
    
    if total == 0:
        print("마이그레이션할 문서가 없습니다.")
        return True
    
    updated_count = 0
    error_count = 0
    
    for hit in result['hits']['hits']:
        doc_id = hit['_id']
        doc = hit['_source']
        
        try:
            updates = {}
            
            # 1. url → source_url 변환
            if 'url' in doc and 'source_url' not in doc:
                updates['source_url'] = doc['url']
            
            # 2. source → source_name 변환
            if 'source' in doc and 'source_name' not in doc:
                # source가 URL인지 이름인지 확인
                source_val = doc['source']
                if source_val.startswith('http'):
                    # URL인 경우 source_url로 이동
                    if 'source_url' not in updates:
                        updates['source_url'] = source_val
                    updates['source_name'] = 'Investing.com'
                else:
                    updates['source_name'] = source_val.title()  # 'investing.com' → 'Investing.Com'
            
            # source_name 기본값 설정
            if 'source_name' not in doc and 'source_name' not in updates:
                updates['source_name'] = 'Investing.com'
            
            # 3. sentiment.classification lowercase 변환
            sentiment = doc.get('sentiment', {})
            if sentiment:
                classification = sentiment.get('classification', '')
                if classification and classification != classification.lower():
                    updates['sentiment'] = {
                        'classification': classification.lower(),
                        'score': sentiment.get('score', 0)
                    }
            
            # 4. analyzed_date 추가 (없는 경우)
            if 'analyzed_date' not in doc:
                # crawled_date 기반으로 추정
                crawled = doc.get('crawled_date')
                if crawled:
                    updates['analyzed_date'] = crawled
                else:
                    updates['analyzed_date'] = datetime.now(timezone.utc).isoformat()
            
            # 5. metadata 추가 (없는 경우)
            if 'metadata' not in doc:
                content = doc.get('content', '')
                updates['metadata'] = {
                    'word_count': len(content.split()) if content else 0,
                    'language': 'en',
                    'gpt_model': 'gpt-4'
                }
            
            # 업데이트 실행
            if updates:
                es.update(
                    index=index_name,
                    id=doc_id,
                    doc=updates
                )
                updated_count += 1
                print(f"  ✓ {doc_id[:8]}... 업데이트 완료 (fields: {list(updates.keys())})")
            else:
                print(f"  - {doc_id[:8]}... 변경 없음")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ {doc_id[:8]}... 오류: {e}")
    
    # 오래된 필드 삭제 (painless script 사용)
    print("\n🧹 오래된 필드 정리 중...")
    
    try:
        # url, source 필드 삭제
        es.update_by_query(
            index=index_name,
            body={
                "script": {
                    "source": """
                        if (ctx._source.containsKey('url')) {
                            ctx._source.remove('url');
                        }
                        if (ctx._source.containsKey('source')) {
                            ctx._source.remove('source');
                        }
                    """,
                    "lang": "painless"
                },
                "query": {
                    "bool": {
                        "should": [
                            {"exists": {"field": "url"}},
                            {"exists": {"field": "source"}}
                        ]
                    }
                }
            }
        )
        print("  ✓ 오래된 필드 삭제 완료")
    except Exception as e:
        print(f"  ⚠ 필드 삭제 중 오류 (무시 가능): {e}")
    
    # 결과 요약
    print(f"\n{'='*50}")
    print(f"📋 마이그레이션 완료")
    print(f"   - 총 문서: {total}")
    print(f"   - 업데이트: {updated_count}")
    print(f"   - 오류: {error_count}")
    print(f"{'='*50}")
    
    return error_count == 0


def verify_migration():
    """마이그레이션 결과 검증"""
    
    es = Elasticsearch(['http://localhost:9200'])
    index_name = 'news_analysis'
    
    print("\n🔍 마이그레이션 결과 검증...")
    
    # 샘플 문서 조회
    result = es.search(
        index=index_name,
        query={'match_all': {}},
        size=3
    )
    
    print("\n샘플 문서 구조:")
    for i, hit in enumerate(result['hits']['hits'][:3]):
        doc = hit['_source']
        print(f"\n--- Document {i+1} ---")
        
        # 필수 필드 확인
        required_v11 = ['source_url', 'source_name', 'analyzed_date', 'metadata']
        removed = ['url', 'source']
        
        for field in required_v11:
            if field in doc:
                val = doc[field]
                if isinstance(val, dict):
                    print(f"  ✓ {field}: {list(val.keys())}")
                elif isinstance(val, str) and len(val) > 50:
                    print(f"  ✓ {field}: \"{val[:50]}...\"")
                else:
                    print(f"  ✓ {field}: {val}")
            else:
                print(f"  ❌ {field}: (누락)")
        
        for field in removed:
            if field in doc:
                print(f"  ⚠ {field}: (삭제되지 않음)")
        
        # sentiment classification 확인
        sentiment = doc.get('sentiment', {})
        classification = sentiment.get('classification', '')
        if classification:
            if classification == classification.lower():
                print(f"  ✓ sentiment.classification: {classification} (lowercase)")
            else:
                print(f"  ⚠ sentiment.classification: {classification} (대문자 포함)")


if __name__ == '__main__':
    print("=" * 50)
    print("ElasticSearch 스키마 마이그레이션 (SRS v1.1)")
    print("=" * 50)
    
    success = migrate_documents()
    
    if success:
        verify_migration()
    
    print("\n완료!")
