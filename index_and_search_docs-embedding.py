import os
from pypdf import PdfReader
import warnings
from openai import OpenAI
import numpy as np
from typing import List, Tuple
import json

# 忽略来自 pypdf 的特定用户警告
warnings.filterwarnings("ignore", category=UserWarning, module='pypdf')


def get_embedding_client():
    """获取embedding客户端"""
    return OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def get_text_embedding(text: str, client: OpenAI) -> list:
    """获取文本的embedding向量"""
    try:
        completion = client.embeddings.create(
            model="text-embedding-v4",
            input=text,
            dimensions=1024,
            encoding_format="float"
        )
        return completion.data[0].embedding
    except Exception as e:
        print(f"生成embedding失败: {e}")
        return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """计算两个向量的余弦相似度"""
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def read_documents(docs_folder: str) -> List[Tuple[str, str]]:
    """读取docs文件夹中的所有文档"""
    documents = []
    
    if not os.path.exists(docs_folder):
        print(f"错误：未找到 '{docs_folder}' 文件夹。")
        return documents
    
    print(f"\n正在从 '{docs_folder}' 文件夹读取文档...")
    
    for filename in os.listdir(docs_folder):
        file_path = os.path.join(docs_folder, filename)
        if os.path.isfile(file_path):
            try:
                content = ""
                if filename.lower().endswith('.pdf'):
                    # 使用 pypdf 读取 PDF
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        content += page.extract_text() or ""
                elif filename.lower().endswith('.txt'):
                    # 读取文本文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    print(f"  - 跳过不支持的文件类型: {filename}")
                    continue
                
                if content.strip():
                    documents.append((filename, content))
                    print(f"  - 成功读取文档: {filename}")
                else:
                    print(f"  - 跳过空文件: {filename}")
            
            except Exception as e:
                print(f"  - 读取文件时出错 '{filename}': {e}")
    
    return documents


def index_documents(documents: List[Tuple[str, str]], client: OpenAI) -> List[Tuple[str, str, np.ndarray]]:
    """为文档生成embedding向量"""
    indexed_docs = []
    
    print(f"\n正在为 {len(documents)} 个文档生成embedding向量...")
    print("注意：这需要一些时间，因为需要为每个文档生成embedding向量...")
    
    for i, (filename, content) in enumerate(documents, 1):
        print(f"  [{i}/{len(documents)}] 正在为 '{filename}' 生成embedding向量...")
        vector = get_text_embedding(content, client)
        
        if vector is not None:
            indexed_docs.append((filename, content, np.array(vector)))
            print(f"  [{i}/{len(documents)}] 成功索引: {filename}")
        else:
            print(f"  [{i}/{len(documents)}] 跳过文档（embedding生成失败）: {filename}")
    
    return indexed_docs


def search(query: str, indexed_docs: List[Tuple[str, str, np.ndarray]], client: OpenAI, top_k: int = 3) -> List[Tuple[str, str, float]]:
    """使用embedding向量搜索相关文档"""
    print(f"\n正在执行向量搜索，查询语句: '{query}'")
    
    # 为查询生成embedding向量
    print("正在为查询生成embedding向量...")
    query_vector = get_text_embedding(query, client)
    
    if query_vector is None:
        print("查询向量生成失败，无法执行搜索。")
        return []
    
    query_vector = np.array(query_vector)
    
    # 计算查询向量与所有文档向量的相似度
    results = []
    for filename, content, doc_vector in indexed_docs:
        similarity = cosine_similarity(query_vector, doc_vector)
        results.append((filename, content, similarity))
    
    # 按相似度排序
    results.sort(key=lambda x: x[2], reverse=True)
    
    # 返回top_k个结果
    return results[:top_k]


def index_and_search_documents():
    """
    使用embedding向量索引docs文件夹下的文档，并执行向量搜索。
    """
    # --- 1. 读取文档 ---
    docs_folder = 'docs'
    documents = read_documents(docs_folder)
    
    if not documents:
        print("\n'docs' 文件夹中没有可以索引的文档。")
        return
    
    # --- 2. 生成embedding向量 ---
    embedding_client = get_embedding_client()
    indexed_docs = index_documents(documents, embedding_client)
    
    if not indexed_docs:
        print("\n没有成功索引任何文档。")
        return
    
    print(f"\n成功索引 {len(indexed_docs)} 个文档！")
    
    # --- 3. 执行搜索 ---
    search_query = "工伤保险和雇主险有什么区别？"
    results = search(search_query, indexed_docs, embedding_client, top_k=3)
    
    # --- 4. 显示搜索结果 ---
    print("\n--- 向量搜索结果 ---")
    if not results:
        print("没有找到匹配的文档。")
    else:
        for i, (filename, content, similarity) in enumerate(results, 1):
            print(f"\n--- 结果 {i} ---")
            print(f"来源文件: {filename}")
            print(f"相似度得分: {similarity:.4f}")
            # 显示部分匹配内容片段
            content_preview = content.strip().replace('\n', ' ')
            print(f"内容预览: {content_preview[:200]}...")


if __name__ == '__main__':
    index_and_search_documents()
