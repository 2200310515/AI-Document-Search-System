from typing import Dict, List, Optional, Tuple, Union

from elasticsearch import Elasticsearch

from qwen_agent.log import logger
from qwen_agent.tools.base import register_tool
from qwen_agent.tools.search_tools.base_search import BaseSearch, Record


@register_tool('elasticsearch_search')
class ElasticsearchSearch(BaseSearch):
    """基于Elasticsearch的文档检索工具"""
    
    description = '使用Elasticsearch从文档中检索相关内容'
    
    def __init__(self, cfg: Optional[Dict] = None):
        super().__init__(cfg)
        self.es_host = self.cfg.get('es_host', 'http://localhost:9200')
        self.es_index = self.cfg.get('es_index', 'qwen_agent_docs')
        self.es_username = self.cfg.get('es_username')
        self.es_password = self.cfg.get('es_password')
        self.batch_size = self.cfg.get('batch_size', 100)
        
        # 连接Elasticsearch
        self.es = self._connect_elasticsearch()
        if not self.es:
            raise Exception(f"无法连接到Elasticsearch: {self.es_host}")
        # 创建索引
        self._create_index()
    
    def _connect_elasticsearch(self):
        """连接到Elasticsearch"""
        try:
            es_kwargs = {
                'verify_certs': False
            }
            
            if self.es_username and self.es_password:
                es_kwargs['basic_auth'] = (self.es_username, self.es_password)
            
            es = Elasticsearch(
                self.es_host,
                **es_kwargs
            )
            
            if es.ping():
                logger.info(f"成功连接到Elasticsearch: {self.es_host}")
                return es
            else:
                logger.error("无法连接到Elasticsearch")
                return None
        except Exception as e:
            logger.error(f"连接Elasticsearch失败: {str(e)}")
            return None
    
    def _create_index(self):
        """创建Elasticsearch索引"""
        if not self.es:
            return
        
        if self.es.indices.exists(index=self.es_index):
            logger.info(f"索引已存在: {self.es_index}")
            return
        
        try:
            index_settings = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "ik_analyzer": {
                                "type": "standard"
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "doc_url": {"type": "keyword"},
                        "chunk_id": {"type": "integer"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "token": {"type": "integer"}
                    }
                }
            }
            
            self.es.indices.create(index=self.es_index, body=index_settings)
            logger.info(f"索引创建成功: {self.es_index}")
        except Exception as e:
            logger.error(f"创建索引失败: {str(e)}")
    
    def _index_document(self, doc: Record):
        """索引单个文档"""
        if not self.es:
            return
        
        try:
            for i, page in enumerate(doc.raw):
                doc_body = {
                    "doc_url": doc.url,
                    "chunk_id": i,
                    "content": page.content,
                    "token": page.token
                }
                # 使用doc_url和chunk_id作为唯一ID
                doc_id = f"{doc.url}_{i}"
                self.es.index(
                    index=self.es_index,
                    id=doc_id,
                    document=doc_body
                )
            logger.info(f"文档索引成功: {doc.url}")
        except Exception as e:
            logger.error(f"索引文档失败 {doc.url}: {str(e)}")
    
    def _index_documents(self, docs: List[Record]):
        """批量索引文档"""
        if not self.es:
            return
        
        for doc in docs:
            self._index_document(doc)
        
        # 刷新索引
        try:
            self.es.indices.refresh(index=self.es_index)
            logger.info("索引刷新成功")
        except Exception as e:
            logger.error(f"刷新索引失败: {str(e)}")
    
    def sort_by_scores(self, query: str, docs: List[Record], **kwargs) -> List[Tuple[str, int, float]]:
        """使用Elasticsearch搜索并排序"""
        # 确保ES连接正常
        if not self.es:
            raise Exception("Elasticsearch连接不可用")
        
        # 先索引文档
        self._index_documents(docs)
        
        # 构建搜索查询
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": 100,  # 返回前100个结果
            "sort": [
                {"_score": {"order": "desc"}}
            ]
        }
        
        response = self.es.search(index=self.es_index, body=search_body)
        
        # 处理搜索结果
        results = []
        for hit in response.get('hits', {}).get('hits', []):
            source = hit['_source']
            score = hit['_score']
            doc_url = source['doc_url']
            chunk_id = source['chunk_id']
            results.append((doc_url, chunk_id, score))
        
        logger.info(f"ES搜索完成，找到 {len(results)} 个结果")
        return results
