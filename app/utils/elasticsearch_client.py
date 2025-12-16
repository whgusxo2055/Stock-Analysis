"""
ElasticSearch 클라이언트 및 유틸리티
"""
from elasticsearch import Elasticsearch
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """ElasticSearch 클라이언트 래퍼"""
    
    def __init__(self, url: str, index_name: str = 'news_analysis'):
        """
        ElasticSearch 클라이언트 초기화
        
        Args:
            url (str): ElasticSearch URL
            index_name (str): 인덱스 이름
        """
        self.client = Elasticsearch([url])
        self.index_name = index_name
        
    def is_connected(self) -> bool:
        """
        ElasticSearch 연결 상태 확인
        
        Returns:
            bool: 연결 성공 여부
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"ElasticSearch connection error: {e}")
            return False
    
    def create_index(self) -> bool:
        """
        뉴스 분석 인덱스 생성 (SRS 7.2.1 v1.1)
        
        Returns:
            bool: 인덱스 생성 성공 여부
        """
        if self.client.indices.exists(index=self.index_name):
            logger.info(f"Index '{self.index_name}' already exists.")
            return True
        
        # 인덱스 매핑 정의 (SRS v1.1 반영)
        index_body = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "index": {
                    "max_result_window": 10000
                }
            },
            "mappings": {
                "properties": {
                    "news_id": {"type": "keyword"},
                    "ticker_symbol": {"type": "keyword"},
                    "company_name": {"type": "text"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "content": {"type": "text", "analyzer": "standard"},
                    "source_url": {"type": "keyword"},
                    "source_name": {"type": "keyword"},
                    "published_date": {"type": "date"},
                    "crawled_date": {"type": "date"},
                    "analyzed_date": {"type": "date"},
                    "summary": {
                        "properties": {
                            "ko": {"type": "text", "analyzer": "standard"},
                            "en": {"type": "text", "analyzer": "standard"},
                            "es": {"type": "text", "analyzer": "standard"},
                            "ja": {"type": "text", "analyzer": "standard"}
                        }
                    },
                    "sentiment": {
                        "properties": {
                            "classification": {"type": "keyword"},
                            "score": {"type": "integer"}
                        }
                    },
                    "metadata": {
                        "properties": {
                            "word_count": {"type": "integer"},
                            "language": {"type": "keyword"},
                            "gpt_model": {"type": "keyword"}
                        }
                    }
                }
            }
        }
        
        try:
            self.client.indices.create(
                index=self.index_name,
                settings=index_body['settings'],
                mappings=index_body['mappings']
            )
            logger.info(f"✓ Index '{self.index_name}' created successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    def index_news(self, news_data: Dict) -> bool:
        """
        뉴스 문서 색인
        
        Args:
            news_data (Dict): 뉴스 데이터
        
        Returns:
            bool: 색인 성공 여부
        """
        try:
            self.client.index(
                index=self.index_name,
                id=news_data.get('news_id'),
                document=news_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index news: {e}")
            return False
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """
        ID로 단일 문서 조회
        
        Args:
            doc_id (str): 문서 ID
        
        Returns:
            Optional[Dict]: 문서 데이터 또는 None
        """
        try:
            response = self.client.get(index=self.index_name, id=doc_id)
            if response and response.get('found'):
                return response.get('_source')
            return None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None
    
    def bulk_index_news(self, news_list: List[Dict]) -> int:
        """
        뉴스 문서 벌크 색인
        
        Args:
            news_list (List[Dict]): 뉴스 데이터 리스트
        
        Returns:
            int: 성공적으로 색인된 문서 수
        """
        from elasticsearch.helpers import bulk
        
        actions = [
            {
                "_index": self.index_name,
                "_id": news.get('news_id'),
                "_source": news
            }
            for news in news_list
        ]
        
        try:
            success, failed = bulk(self.client, actions, raise_on_error=False)
            logger.info(f"Bulk indexed {success} documents")
            if failed:
                logger.warning(f"Failed to index {len(failed)} documents")
            return success
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            return 0
    
    def search_news(
        self,
        ticker_symbol: Optional[str] = None,
        ticker_symbols: Optional[List[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sentiment: Optional[str] = None,
        size: int = 20,
        from_: int = 0
    ) -> Dict:
        """
        뉴스 검색
        
        Args:
            ticker_symbol (str, optional): 티커 심볼
            from_date (str, optional): 시작 날짜
            to_date (str, optional): 종료 날짜
            sentiment (str, optional): 감성 분류 (Positive/Negative/Neutral)
            size (int): 결과 수
            from_ (int): 시작 위치
        
        Returns:
            Dict: 검색 결과
        """
        query = {"bool": {"must": []}}
        
        if ticker_symbols:
            query["bool"]["must"].append({"terms": {"ticker_symbol": ticker_symbols}})
        elif ticker_symbol:
            query["bool"]["must"].append({"term": {"ticker_symbol": ticker_symbol}})
        
        if sentiment:
            query["bool"]["must"].append({"term": {"sentiment.classification": sentiment}})
        
        if from_date or to_date:
            date_range = {}
            if from_date:
                date_range["gte"] = from_date
            if to_date:
                date_range["lte"] = to_date
            query["bool"]["must"].append({"range": {"published_date": date_range}})
        
        # 쿼리가 없으면 match_all
        if not query["bool"]["must"]:
            query = {"match_all": {}}
        
        try:
            response = self.client.search(
                index=self.index_name,
                query=query,
                sort=[{"published_date": {"order": "desc"}}],
                size=size,
                from_=from_
            )
            return response
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"hits": {"hits": [], "total": {"value": 0}}}
    
    def get_statistics(self, ticker_symbol: str, days: int = 7) -> Dict:
        """
        종목별 통계 조회
        
        Args:
            ticker_symbol (str): 티커 심볼
            days (int): 기간 (일)
        
        Returns:
            Dict: 통계 결과
        """
        from datetime import timedelta
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        try:
            response = self.client.search(
                index=self.index_name,
                query={
                    "bool": {
                        "must": [
                            {"term": {"ticker_symbol": ticker_symbol}},
                            {"range": {"published_date": {
                                "gte": from_date.isoformat(),
                                "lte": to_date.isoformat()
                            }}}
                        ]
                    }
                },
                aggs={
                    "sentiment_distribution": {
                        "terms": {"field": "sentiment.classification"}
                    },
                    "avg_score": {
                        "avg": {"field": "sentiment.score"}
                    }
                },
                size=0
            )
            
            return {
                "total": response["hits"]["total"]["value"],
                "sentiment_distribution": response["aggregations"]["sentiment_distribution"]["buckets"],
                "avg_score": response["aggregations"]["avg_score"]["value"]
            }
        except Exception as e:
            logger.error(f"Statistics error: {e}")
            return {"total": 0, "sentiment_distribution": [], "avg_score": 0}
    
    def delete_old_news(self, days: int = 730):
        """
        오래된 뉴스 삭제 (2년 이상)
        
        Args:
            days (int): 보관 일수
        
        Returns:
            int: 삭제된 문서 수
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            response = self.client.delete_by_query(
                index=self.index_name,
                query={
                    "range": {
                        "crawled_date": {
                            "lt": cutoff_date.isoformat()
                        }
                    }
                }
            )
            deleted = response.get('deleted', 0)
            logger.info(f"Deleted {deleted} old news documents")
            return deleted
        except Exception as e:
            logger.error(f"Delete old news error: {e}")
            return 0


# 싱글톤 인스턴스
_es_client: Optional[ElasticsearchClient] = None


def get_es_client(url: str = None, index_name: str = 'news_analysis') -> ElasticsearchClient:
    """
    ElasticSearch 클라이언트 싱글톤 인스턴스 반환
    
    Args:
        url (str, optional): ElasticSearch URL
        index_name (str): 인덱스 이름
    
    Returns:
        ElasticsearchClient: ES 클라이언트 인스턴스
    """
    global _es_client
    
    if _es_client is None:
        if url is None:
            from app.utils.config import Config
            url = Config.ELASTICSEARCH_URL
        _es_client = ElasticsearchClient(url, index_name)
    
    return _es_client
