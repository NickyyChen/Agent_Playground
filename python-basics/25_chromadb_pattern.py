# -*- coding: utf-8 -*-
"""
25_chromadb_pattern.py — ChromaDB 向量存储模式
==============================================

【概念】
ChromaDB 是轻量级向量数据库——把文本转为向量（embedding），
存起来，再通过语义相似度检索。

与普通数据库的区别：
  普通: SELECT * WHERE keyword = '退货'  → 精确匹配
  向量: 查询 "怎么退款"  →  语义匹配 "退换货流程说明"

核心流程：
  1. 加载嵌入模型（如 BGE-large-zh）
  2. 创建 ChromaDB Collection + 自定义 EmbeddingFunction
  3. add() 存入文档 + 元数据
  4. query() 语义检索，返回最相关的 N 条

【在智能客服中的应用】
- RAG（检索增强生成）：从知识库检索相关政策，嵌入 prompt
- 长期记忆：跨会话召回用户历史交互
- FAQ 自动匹配：用户问题 → 最相似的预设回答

【pip install】
pip install chromadb sentence_transformers

【ASCII 架构图】

  文档入库:
  "退换货政策..." ──▶ embedding_fn() ──▶ [0.12, 0.34, ...] ──▶ ChromaDB

  语义检索:
  "怎么退款" ──▶ embedding_fn() ──▶ [0.11, 0.33, ...]
                                          │
                                          ▼ 余弦相似度匹配
                                    ┌──────────────────┐
                                    │ 1. 退换货政策 0.95│
                                    │ 2. 退款流程  0.82 │
                                    │ 3. 常见问题  0.61 │
                                    └──────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


# ══════════════════════════════════════════════════════════════
# 1. ChromaDB 基本操作
# WHY: ChromaDB 是 Python 原生的向量数据库——
#      不需要独立服务进程，数据存本地文件，开箱即用。
#      适合 Agent 的学习和原型阶段。
# ══════════════════════════════════════════════════════════════

def demo_basic_chromadb():
    print("=" * 50)
    print(" 1. ChromaDB 基本操作")
    print("=" * 50)

    # WHY: PersistentClient 写入磁盘，重启不丢失数据
    chroma_path = os.path.join(os.path.dirname(__file__),
                                "..", ".chroma_basics")
    client = chromadb.PersistentClient(path=chroma_path)

    # WHY: Collection 类似 SQL 中的"表"——
    #      每个 Collection 独立存储和检索
    collection = client.get_or_create_collection(
        name="customer_service_faq",
        metadata={"description": "客服常见问题库"},
    )

    # 添加文档
    docs = [
        "退换货政策：签收7天内未拆封可全额退款，拆封后不支持无理由退货。",
        "物流查询：登录App→我的订单→查看物流，或输入快递单号查询。",
        "优惠活动：新用户首单9折，老用户每月18日会员日享8折。",
        "售后保修：电子产品享1年质保，非人为损坏免费维修。",
    ]
    ids = [f"doc_{i}" for i in range(len(docs))]

    collection.add(
        documents=docs,
        ids=ids,
    )
    print(f" 已存入 {len(docs)} 条文档")

    # 语义检索——关键词不必完全匹配
    results = collection.query(
        query_texts=["耳机坏了怎么办"],
        n_results=2,
    )
    print(f"\n 查询: '耳机坏了怎么办'")
    print(f" 匹配文档数: {len(results['documents'][0])}")
    for i, (doc_id, doc, dist) in enumerate(zip(
        results["ids"][0],
        results["documents"][0],
        results["distances"][0],
    )):
        print(f"   {i+1}. [{doc_id}] 相似度={1-dist:.2f}: {doc[:50]}...")

    # 清理——删除测试 collection
    client.delete_collection("customer_service_faq")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 自定义 EmbeddingFunction
# WHY: ChromaDB 默认的嵌入模型是英文的（all-MiniLM-L6-v2），
#      中文场景需要自定义嵌入函数。
#      必须继承 EmbeddingFunction 并实现 __call__。
# ══════════════════════════════════════════════════════════════

def demo_custom_embedding():
    print("=" * 50)
    print(" 2. 自定义 EmbeddingFunction")
    print("=" * 50)

    # WHY: 实现 EmbeddingFunction 接口——
    #      __call__ 接收 Documents 类型，返回 Embeddings 类型。
    #      ChromaDB 在 add/query 时自动调用这个方法。
    class SimpleChineseEmbedding(EmbeddingFunction):
        """
        简化的中文嵌入函数（演示用）。
        实际项目用 BGE/M3E 等中文模型。
        """
        def __call__(self, input: Documents) -> Embeddings:
            """
            WHY: 必须叫 __call__——ChromaDB 源码调用的是 fn(docs)，
                 不是 fn.encode(docs)。
            """
            import hashlib
            # 用哈希模拟向量——实际场景用 SentenceTransformer
            vectors = []
            for text in input:
                h = hashlib.md5(text.encode()).digest()
                # 取前 8 字节转成 8 维向量
                vec = [b / 255.0 for b in h[:8]]
                vectors.append(vec)
            return vectors

    # 使用自定义嵌入函数
    chroma_path = os.path.join(os.path.dirname(__file__),
                                "..", ".chroma_basics")
    client = chromadb.PersistentClient(path=chroma_path)

    embedding_fn = SimpleChineseEmbedding()
    collection = client.get_or_create_collection(
        name="chinese_test",
        embedding_function=embedding_fn,  # WHY: 传入自定义嵌入函数
    )

    collection.add(
        documents=["退换货政策说明", "物流查询方法", "优惠活动介绍"],
        ids=["d1", "d2", "d3"],
    )

    results = collection.query(query_texts=["我要退货"], n_results=2)
    print(f" 查询: '我要退货'")
    for doc_id, doc in zip(results["ids"][0], results["documents"][0]):
        print(f"   → {doc}")

    client.delete_collection("chinese_test")
    print()


# ══════════════════════════════════════════════════════════════
# 3. RAG 模式 —— ChromaDB + LLM
# WHY: 这是 Agent 最经典的组合模式——
#      用户问题 → ChromaDB 检索相关知识 → 知识嵌入 prompt → LLM 回答。
#      解决 LLM 的"幻觉"和"知识截止日期"问题。
# ══════════════════════════════════════════════════════════════

def demo_rag_pattern():
    print("=" * 50)
    print(" 3. RAG 模式 —— 检索 + 生成")
    print("=" * 50)

    print("""
  RAG (Retrieval-Augmented Generation) 流程:

  用户: "耳机能退货吗？"
     │
     ▼
  ① 检索 (Retrieve):
     ChromaDB.query("耳机能退货吗") → "退换货政策: 7天内未拆封可退..."
     │
     ▼
  ② 增强 (Augment):
     prompt = f"根据以下政策回答问题: {政策} \\n\\n 用户问题: {用户问题}"
     │
     ▼
  ③ 生成 (Generate):
     LLM(prompt) → "您好！根据平台政策，签收7天内且未拆封的商品可全额退款..."

  关键点:
  - 知识存储在 ChromaDB 中，而非硬编码在 prompt 里
  - 新增政策只需 add() 到 ChromaDB，无需改代码
  - LLM 的回答有了"事实依据"而非凭空编造
  """)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 25: ChromaDB 向量存储模式        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_chromadb()
    demo_custom_embedding()
    demo_rag_pattern()


if __name__ == "__main__":
    main()
