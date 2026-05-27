# -*- coding: utf-8 -*-
"""
RAG 知识库 —— Demo 05 (文档切块 + 向量嵌入 + 语义检索 + 多文档融合)
"""

import sys, os, chromadb
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from demos_all.config import RAG_CONFIG

BGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bge-large-zh-v1.5")
_bge = None

def _get_bge():
    global _bge
    if _bge is None:
        from sentence_transformers import SentenceTransformer
        _bge = SentenceTransformer(BGE_PATH)
    return _bge

class BGEEmbedding(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return _get_bge().encode(input, normalize_embeddings=True).tolist()


class RAGKnowledgeBase:
    """
    RAG 知识库。
    知识点:
      Demo 05 — 文档切块(chunking) + 向量嵌入 + 语义检索 + 多文档融合
    """

    def __init__(self):
        self._collection = None
        self._splitter = None

    @property
    def collection(self):
        if self._collection is None:
            client = chromadb.PersistentClient(
                path=os.path.join(os.path.dirname(__file__), "..",
                                  RAG_CONFIG["chroma_path"]))
            try:
                self._collection = client.get_collection("knowledge_base")
            except Exception:
                self._collection = client.create_collection(
                    "knowledge_base", embedding_function=BGEEmbedding())
        return self._collection

    @property
    def splitter(self):
        if self._splitter is None:
            self._splitter = RecursiveCharacterTextSplitter(
                chunk_size=RAG_CONFIG["chunk_size"],
                chunk_overlap=RAG_CONFIG["chunk_overlap"],
                separators=["\n\n", "\n", "。", "；", "，", " ", ""],
            )
        return self._splitter

    def add_documents(self, documents: list[dict]):
        """添加文档（含 title + content）"""
        doc_id = self.collection.count()
        for doc in documents:
            chunks = self.splitter.split_text(doc["content"])
            for i, chunk in enumerate(chunks):
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{"source": doc["title"], "chunk_index": i}],
                    ids=[f"doc_{doc_id}"],
                )
                doc_id += 1

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """语义检索，返回 [{source, content, distance}]"""
        k = top_k or RAG_CONFIG["top_k"]
        results = self.collection.query(query_texts=[query], n_results=k)
        if not results["documents"] or not results["documents"][0]:
            return []
        return [
            {"source": results["metadatas"][0][i].get("source", ""),
             "content": results["documents"][0][i],
             "distance": results["distances"][0][i] if results.get("distances") else 0}
            for i in range(len(results["documents"][0]))
        ]

    def inject_context(self, messages: list[dict], query: str,
                       top_k: int = None) -> list[dict]:
        """检索相关文档并注入到 system prompt（多文档融合）"""
        docs = self.search(query, top_k)
        if not docs:
            return messages
        context_parts = [
            f"[参考{i+1} | {d['source']}]\n{d['content']}"
            for i, d in enumerate(docs)
        ]
        context_text = "\n\n---\n\n".join(context_parts)
        result = list(messages)
        result.insert(-1, {"role": "system",
                           "content": f"【参考资料】\n{context_text}"})
        return result
