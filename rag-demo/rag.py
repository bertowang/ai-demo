#!/usr/bin/env python3
"""
RAG Demo - 检索增强生成（Retrieval-Augmented Generation）

核心思路：
  1. 把文档切成小块，转成向量存入向量库
  2. 用户提问时，先从向量库检索最相关的文档块
  3. 把检索结果 + 用户问题一起发给 LLM，让 LLM 基于文档回答

为什么需要 RAG？
  - LLM 的知识有截止日期，不知道最新信息
  - LLM 不知道你的私有文档（公司内部资料、个人笔记等）
  - RAG 让 LLM 能"查资料"再回答，而不是凭空编造

使用方法：
  ./venv/bin/python rag.py
"""

import os
from typing import List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_chroma import Chroma

# ============================================================
# 配置
# ============================================================

API_KEY: str = "teWS8OdeWJ4dfaVBTGjkbTje@4186"
BASE_URL: str = "http://v2.open.venus.oa.com/llmproxy"
MODEL: str = "gpt-4o-mini"


# ============================================================
# 第一步：准备"知识库"文档
# ============================================================

# 这里模拟一批公司内部文档（真实项目中可以从文件、数据库读取）
DOCUMENTS = [
    Document(
        page_content="LangChain 是一个用于构建 LLM 应用的 Python 框架，提供了链式调用、工具绑定、记忆管理等功能。它的核心抽象是 Chain（链），可以把多个 LLM 调用串联起来。",
        metadata={"source": "langchain_intro.txt", "topic": "LangChain"}
    ),
    Document(
        page_content="LangGraph 是 LangChain 团队开发的图状态机框架，专门用于构建有状态的多步骤 Agent。它把 Agent 的执行流程建模为一个有向图，每个节点是一个处理步骤，边决定流转方向。",
        metadata={"source": "langgraph_intro.txt", "topic": "LangGraph"}
    ),
    Document(
        page_content="RAG（Retrieval-Augmented Generation，检索增强生成）是一种让 LLM 能够访问外部知识库的技术。流程是：先用向量检索找到相关文档，再把文档内容和用户问题一起发给 LLM。",
        metadata={"source": "rag_intro.txt", "topic": "RAG"}
    ),
    Document(
        page_content="向量数据库（Vector Database）是专门存储和检索向量的数据库。常见的有 Chroma（本地轻量）、Faiss（Meta开源）、Milvus（分布式）、Pinecone（云服务）。RAG 系统通常用向量数据库存储文档的 Embedding。",
        metadata={"source": "vector_db.txt", "topic": "向量数据库"}
    ),
    Document(
        page_content="Embedding（嵌入）是把文本转换成数字向量的技术。语义相似的文本，其向量在空间中距离更近。OpenAI 提供了 text-embedding-ada-002 等 Embedding 模型，可以把任意文本转成 1536 维的向量。",
        metadata={"source": "embedding.txt", "topic": "Embedding"}
    ),
    Document(
        page_content="MCP（Model Context Protocol）是 Anthropic 提出的开放协议，让 LLM 能够标准化地调用外部工具和资源。MCP Server 提供工具，MCP Client（通常是 LLM 应用）调用工具。",
        metadata={"source": "mcp_intro.txt", "topic": "MCP"}
    ),
    Document(
        page_content="Agent（智能体）是一种能够自主决策和行动的 AI 系统。它的核心循环是：感知环境 → LLM 决策 → 执行工具 → 观察结果 → 继续决策，直到完成任务。",
        metadata={"source": "agent_intro.txt", "topic": "Agent"}
    ),
    Document(
        page_content="Function Calling（函数调用）是 OpenAI 提供的能力，让 LLM 在回复中声明要调用哪个函数、传什么参数。应用程序检测到 tool_calls 后，执行对应函数，再把结果返回给 LLM。",
        metadata={"source": "function_calling.txt", "topic": "Function Calling"}
    ),
]


# ============================================================
# 第二步：构建向量库
# ============================================================

def build_vector_store(documents: List[Document]) -> Chroma:
    """
    把文档转成向量，存入 Chroma 向量库

    流程：
      文档文本 → Embedding 模型 → 向量 → 存入 Chroma
    """
    print("📚 正在构建向量库...")
    print(f"   文档数量：{len(documents)} 篇")

    # 创建 Embedding 模型（把文本转成向量）
    embeddings = OpenAIEmbeddings(
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        model="text-embedding-ada-002",
    )

    # 把文档存入 Chroma（内存模式，程序退出后数据消失）
    # 如果想持久化，可以加 persist_directory="./chroma_db"
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
    )

    print(f"   ✅ 向量库构建完成，共 {vector_store._collection.count()} 条向量\n")
    return vector_store


# ============================================================
# 第三步：RAG 问答
# ============================================================

def rag_query(question: str, vector_store: Chroma, top_k: int = 3) -> str:
    """
    RAG 核心流程：检索 + 生成

    Args:
        question: 用户问题
        vector_store: 向量库
        top_k: 检索最相关的前 k 篇文档

    Returns:
        LLM 基于检索结果生成的回答
    """
    print(f"❓ 问题：{question}")

    # --- 步骤 1：检索相关文档 ---
    print(f"\n🔍 步骤1：从向量库检索最相关的 {top_k} 篇文档...")
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
    relevant_docs = retriever.invoke(question)

    print("   检索到的文档：")
    for i, doc in enumerate(relevant_docs, 1):
        source = doc.metadata.get("source", "未知来源")
        # 只打印前 60 个字符，避免输出太长
        preview = doc.page_content[:60] + "..."
        print(f"   [{i}] {source}: {preview}")

    # --- 步骤 2：把检索结果拼成上下文 ---
    context = "\n\n".join([
        f"【文档{i+1}】{doc.page_content}"
        for i, doc in enumerate(relevant_docs)
    ])

    # --- 步骤 3：构建 Prompt，让 LLM 基于文档回答 ---
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """你是一个知识库助手。请严格根据下面提供的文档内容来回答用户的问题。
如果文档中没有相关信息，请直接说"文档中没有相关信息"，不要编造答案。

【参考文档】
{context}"""),
        ("human", "{question}"),
    ])

    # --- 步骤 4：调用 LLM 生成回答 ---
    print("\n🤖 步骤2：将检索结果发给 LLM 生成回答...")
    llm = ChatOpenAI(
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        model=MODEL,
        temperature=0.1,  # 低温度，让回答更稳定
    )

    # 组合 prompt + llm，形成一个简单的 RAG 链
    chain = prompt_template | llm

    response = chain.invoke({
        "context": context,
        "question": question,
    })

    answer = response.content
    print(f"\n💬 回答：{answer}")
    return answer


# ============================================================
# 主程序：演示三种典型场景
# ============================================================

def main():
    print("=" * 60)
    print("  RAG Demo - 检索增强生成")
    print("=" * 60)
    print()

    # 构建向量库（只需构建一次）
    vector_store = build_vector_store(DOCUMENTS)

    # ---- 测试 1：正常检索（文档中有答案）----
    print("-" * 60)
    print("【测试1】文档中有答案的问题")
    print("-" * 60)
    rag_query("LangGraph 是什么？有什么特点？", vector_store)

    print("\n")

    # ---- 测试 2：跨文档综合（需要结合多篇文档）----
    print("-" * 60)
    print("【测试2】需要综合多篇文档的问题")
    print("-" * 60)
    rag_query("RAG 系统中，Embedding 和向量数据库分别起什么作用？", vector_store)

    print("\n")

    # ---- 测试 3：文档中没有答案（验证不编造）----
    print("-" * 60)
    print("【测试3】文档中没有答案的问题（验证不编造）")
    print("-" * 60)
    rag_query("Python 的 asyncio 库怎么使用？", vector_store)

    print("\n")
    print("=" * 60)
    print("  演示完成！")
    print("=" * 60)
    print()
    print("💡 RAG 核心流程回顾：")
    print("   1. 文档 → Embedding → 向量库（构建阶段）")
    print("   2. 用户问题 → 向量检索 → 相关文档（检索阶段）")
    print("   3. 相关文档 + 问题 → LLM → 回答（生成阶段）")


if __name__ == "__main__":
    main()
