#!/usr/bin/env python
# coding: utf-8

"""
Elasticsearch 保险文档索引与搜索示例
功能：
1. 连接到Elasticsearch
2. 创建索引
3. 索引文档（将docs文件夹下的txt文件内容添加到ES）
4. 执行搜索
5. 显示搜索结果
"""

import os
import json
from elasticsearch import Elasticsearch
from datetime import datetime


# ============================================
# Elasticsearch 配置 - 请根据实际情况修改
# ============================================
ES_HOST = 'http://localhost:9200'  # ES地址
ES_INDEX = 'insurance_docs'        # 索引名称
USERNAME = 'elastic'               # 用户名（如果不需要认证则删除）
PASSWORD = '6sWnn3nKHN9A5rIvEc+E'         # 密码

# docs文件夹路径
DOCS_DIR = './docs'


def get_es_client():
    """连接到Elasticsearch"""
    try:
        es = Elasticsearch(
            ES_HOST,
            basic_auth=(USERNAME, PASSWORD) if PASSWORD != 'your_password' else None,
            verify_certs=False
        )
        if es.ping():
            print(f"✓ 成功连接到 Elasticsearch: {ES_HOST}")
            return es
        else:
            print("✗ 无法连接到 Elasticsearch")
            return None
    except Exception as e:
        print(f"✗ 连接 Elasticsearch 失败: {str(e)}")
        return None


def create_index(es):
    """创建索引"""
    if es is None:
        return False
    
    # 删除已存在的索引
    if es.indices.exists(index=ES_INDEX):
        print(f"删除已存在的索引: {ES_INDEX}")
        es.indices.delete(index=ES_INDEX)
    
    # 创建索引配置
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
                "title": {"type": "text", "analyzer": "standard"},
                "content": {"type": "text", "analyzer": "standard"},
                "file_name": {"type": "keyword"},
                "file_path": {"type": "keyword"},
                "indexed_at": {"type": "date"}
            }
        }
    }
    
    try:
        es.indices.create(index=ES_INDEX, body=index_settings)
        print(f"✓ 索引创建成功: {ES_INDEX}")
        return True
    except Exception as e:
        print(f"✗ 创建索引失败: {str(e)}")
        return False


def read_txt_files():
    """读取docs文件夹下的所有txt文件"""
    docs = []
    if not os.path.exists(DOCS_DIR):
        print(f"✗ 目录不存在: {DOCS_DIR}")
        return docs
    
    for file_name in os.listdir(DOCS_DIR):
        if file_name.endswith('.txt'):
            file_path = os.path.join(DOCS_DIR, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                docs.append({
                    "title": file_name.replace('.txt', ''),
                    "content": content,
                    "file_name": file_name,
                    "file_path": file_path
                })
                print(f"✓ 读取文件: {file_name} ({len(content)} 字符)")
            except Exception as e:
                print(f"✗ 读取文件失败 {file_name}: {str(e)}")
    
    return docs


def index_documents(es, docs):
    """索引文档到Elasticsearch"""
    if es is None or not docs:
        return 0
    
    indexed_count = 0
    for i, doc in enumerate(docs):
        try:
            doc["indexed_at"] = datetime.now().isoformat()
            es.index(index=ES_INDEX, id=i+1, document=doc)
            indexed_count += 1
        except Exception as e:
            print(f"✗ 索引文档失败: {str(e)}")
    
    # 刷新索引
    es.indices.refresh(index=ES_INDEX)
    print(f"✓ 成功索引 {indexed_count} 个文档")
    return indexed_count


def search_documents(es, query):
    """搜索文档"""
    if es is None:
        return []
    
    try:
        # 使用multi_match进行全文搜索
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^2", "content"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "highlight": {
                "fields": {
                    "content": {"fragment_size": 150, "number_of_fragments": 3},
                    "title": {}
                },
                "pre_tags": ["<em>", "<em>"],
                "post_tags": ["</em>", "</em>"]
            },
            "size": 10
        }
        
        response = es.search(index=ES_INDEX, body=search_body)
        return response
    except Exception as e:
        print(f"✗ 搜索失败: {str(e)}")
        return []


def display_search_results(response, query):
    """显示搜索结果"""
    if not response:
        print("没有搜索结果")
        return
    
    total = response.get('hits', {}).get('total', {}).get('value', 0)
    print(f"\n{'='*60}")
    print(f"搜索查询: {query}")
    print(f"找到 {total} 条相关结果")
    print(f"{'='*60}\n")
    
    hits = response.get('hits', {}).get('hits', [])
    for i, hit in enumerate(hits, 1):
        source = hit['_source']
        score = hit['_score']
        highlight = hit.get('highlight', {})
        
        print(f"【结果 {i}】 相似度: {score:.2f}")
        print(f"标题: {source.get('title', 'N/A')}")
        print(f"文件: {source.get('file_name', 'N/A')}")
        
        # 显示高亮内容
        if 'content' in highlight:
            print("相关内容:")
            for fragment in highlight['content']:
                print(f"  {fragment}")
        elif 'title' in highlight:
            print(f"标题匹配: {highlight['title'][0]}")
        
        print("-" * 60)


def main():
    """主函数"""
    print("="*60)
    print("Elasticsearch 保险文档索引与搜索")
    print("="*60)
    
    # 1. 连接到Elasticsearch
    print("\n[1/5] 连接到 Elasticsearch...")
    es = get_es_client()
    if not es:
        print("请检查ES配置后重试")
        return
    
    # 2. 创建索引
    print("\n[2/5] 创建索引...")
    if not create_index(es):
        print("创建索引失败")
        return
    
    # 3. 读取文档
    print("\n[3/5] 读取文档...")
    docs = read_txt_files()
    if not docs:
        print("没有找到可索引的文档")
        return
    
    # 4. 索引文档
    print("\n[4/5] 索引文档...")
    index_documents(es, docs)
    
    # 5. 执行搜索
    search_query = "工伤保险和雇主险有什么区别？"
    print(f"\n[5/5] 执行搜索: {search_query}")
    response = search_documents(es, search_query)
    
    # 显示搜索结果
    display_search_results(response, search_query)
    
    print("\n✓ 完成!")


if __name__ == '__main__':
    main()
