# AI-Document-Search-System
AI 智能文档搜索问答系统
核心技术栈 : Python 3.10 + LLM + RAG 
⼯具链 : PyPDF2 + embedding + Elasticsearch 9.3.1 + DashScope + Gradio
系统功能 : 
   - 文档处理与索引 ：使⽤PyPDF2解析PDF文档，提取文本内容并自动分块，通过
  Elasticsearch构建分布式索引，支持增量更新
   - 向量检索实现 ：基于text-embedding-v4模型生成文档向量，实现余弦相似度计算
  进行语义匹配，构建混合检索策略（Elasticsearch + 向量检索）
   - 智能问答流程 ：设计RAG架构，将检索结果与⽤户查询结合，通过DashScope
  API调⽤大模型生成准确回答

