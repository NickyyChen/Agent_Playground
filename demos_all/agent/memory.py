# -*- coding: utf-8 -*-
"""
记忆系统 —— 短期记忆(Demo 04) + 长期记忆(Demo 04) + 窗口管理(Demo 17)
"""

import sys, os, json, chromadb
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from chromadb import Documents, EmbeddingFunction, Embeddings
from demos_all.config import MEMORY_CONFIG, CONTEXT_WINDOW

BGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "bge-large-zh-v1.5")
_bge_mem = None

def _get_bge():
    global _bge_mem
    if _bge_mem is None:
        from sentence_transformers import SentenceTransformer
        _bge_mem = SentenceTransformer(BGE_PATH)
    return _bge_mem

class BGEEmbedding(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        return _get_bge().encode(input, normalize_embeddings=True).tolist()


class MemoryManager:
    """
    统一记忆管理。
    知识点:
      Demo 04 — 短期记忆(messages[]) + 长期记忆(ChromaDB)
      Demo 17 — Context Window 管理 (滑动窗口 / 摘要压缩)
    """

    def __init__(self):
        self.short_term: list[dict] = []
        self._long_term = None  # 懒加载 ChromaDB
        self.max_tokens = CONTEXT_WINDOW["max_tokens"]
        self.keep_recent = CONTEXT_WINDOW["keep_recent"]
        self.llm = None

    @property
    def long_term(self):
        if self._long_term is None:
            client = chromadb.PersistentClient(
                path=os.path.join(os.path.dirname(__file__), "..",
                                  MEMORY_CONFIG["chroma_path"]))
            try:
                self._long_term = client.get_collection("memory_v1")
            except Exception:
                self._long_term = client.create_collection(
                    "memory_v1", embedding_function=BGEEmbedding())
        return self._long_term

    # ─── 短期记忆 ─────────────────────────────────
    def add_message(self, role: str, content: str):
        self.short_term.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        """获取 messages，必要时自动管理窗口"""
        return self._manage_window(list(self.short_term))

    # ─── 长期记忆 ─────────────────────────────────
    def remember(self, user_id: str, content: str):
        """存入长期记忆"""
        count = self.long_term.count()
        self.long_term.add(documents=[content], ids=[f"mem_{count}"])

    def recall(self, query: str, n: int = 3) -> list[str]:
        """语义检索相关历史"""
        results = self.long_term.query(query_texts=[query], n_results=n)
        if results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []

    def inject_recall(self, messages: list[dict], query: str) -> list[dict]:
        """将长期记忆召回结果注入 system prompt"""
        recalled = self.recall(query)
        if not recalled:
            return messages
        context = "\n".join(f"- {r}" for r in recalled)
        injection = {"role": "system",
                     "content": f"[用户历史记录]\n{context}"}
        result = list(messages)
        result.insert(1, injection)  # system 之后，user 之前
        return result

    # ─── 窗口管理 (Demo 17) ──────────────────────
    def _count_tokens(self, messages: list[dict]) -> int:
        total = 0
        for m in messages:
            total += len(str(m.get("content", ""))) // 2
        return total

    def _manage_window(self, messages: list[dict]) -> list[dict]:
        """根据 token 数自动选择滑动窗口或摘要压缩"""
        tokens = self._count_tokens(messages)
        if tokens < self.max_tokens * CONTEXT_WINDOW["warning_ratio"]:
            return messages
        if tokens < self.max_tokens * 0.95:
            return self._sliding_window(messages)
        return self._summarize(messages)

    def _sliding_window(self, messages: list[dict]) -> list[dict]:
        system = [m for m in messages if m["role"] == "system"]
        rest = [m for m in messages if m["role"] != "system"]
        return system + rest[-self.keep_recent:]

    def _summarize(self, messages: list[dict]) -> list[dict]:
        system = [m for m in messages if m["role"] == "system"]
        rest = [m for m in messages if m["role"] != "system"]
        if len(rest) <= self.keep_recent:
            return messages
        old, recent = rest[:-self.keep_recent], rest[-self.keep_recent:]
        if self.llm:
            old_text = "\n".join(
                f"{'用户' if m['role']=='user' else '客服'}: {m['content'][:100]}"
                for m in old)
            summary = self.llm.chat([
                {"role": "system",
                 "content": "压缩以下对话为100字摘要，保留关键信息。"},
                {"role": "user", "content": old_text},
            ], profile="fast")
            return system + [{"role": "system",
                              "content": f"[历史摘要] {summary}"}] + recent
        return self._sliding_window(messages)
