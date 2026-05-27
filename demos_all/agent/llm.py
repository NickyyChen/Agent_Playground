# -*- coding: utf-8 -*-
"""
LLM 客户端 —— 集成 重试(Demo 18) + 路由(Demo 19) + 缓存(Demo 20) + 参数控制(Demo 01)
"""

import sys, os, time, json, random, functools, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from openai import OpenAI
from demos_all.config import LLM_CONFIG, MODEL_PROFILES, RETRY_CONFIG


class LLMClient:
    """
    统一 LLM 客户端。
    知识点覆盖:
      Demo 01 — temperature/top_p/max_tokens 参数透传
      Demo 18 — 指数退避重试 + 熔断器
      Demo 19 — 模型路由 (fast/standard/premium)
      Demo 20 — 本地 Prompt 缓存
    """

    def __init__(self):
        self.client = OpenAI(api_key=LLM_CONFIG["api_key"],
                             base_url=LLM_CONFIG["base_url"])
        # ─── 熔断器状态 ───
        self._failure_count = 0
        self._circuit_open = False
        # ─── 本地缓存 ───
        self._cache: dict[str, tuple[str, float]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    # ─── 模型路由 (Demo 19) ──────────────────────
    def route(self, user_input: str) -> str:
        """根据问题复杂度选择模型画像: fast / standard / premium"""
        length = len(user_input)
        has_complex = any(kw in user_input for kw in
                          ["对比", "推荐", "为什么", "怎么处理", "投诉"])
        if length > 200 or has_complex:
            return "premium"
        elif length > 50:
            return "standard"
        return "fast"

    # ─── 指数退避重试 (Demo 18) ──────────────────
    def _retry_call(self, fn, max_retries=None, base_delay=None):
        """指数退避 + 随机抖动 + 熔断"""
        max_retries = max_retries or RETRY_CONFIG["max_retries"]
        base_delay = base_delay or RETRY_CONFIG["base_delay"]

        if self._circuit_open:
            return "服务暂不可用（熔断保护），请稍后重试。"

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                result = fn()
                self._failure_count = 0
                return result
            except Exception as e:
                last_error = e
                self._failure_count += 1
                if self._failure_count >= RETRY_CONFIG["circuit_threshold"]:
                    self._circuit_open = True
                if attempt < max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    delay += random.uniform(0, delay * 0.25)
                    time.sleep(delay)
        return f"AI服务暂时不可用: {last_error}"

    # ─── Prompt 缓存 (Demo 20) ──────────────────
    def _cache_key(self, messages: list[dict]) -> str:
        def _serialize(m):
            if isinstance(m, dict):
                return m.get("content", "")
            return str(getattr(m, "content", "")) if hasattr(m, "content") else str(m)
        raw = json.dumps([_serialize(m) for m in messages],
                         ensure_ascii=False, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()

    # ─── 核心调用 ────────────────────────────────
    def chat(self, messages: list[dict], profile: str = "standard",
             use_cache: bool = True, **params) -> str:
        """
        发送对话请求。
        profile: fast / standard / premium
        params: temperature, max_tokens, top_p 等 (Demo 01)
        """
        # 本地缓存
        if use_cache:
            key = self._cache_key(messages)
            if key in self._cache:
                self._cache_hits += 1
                return self._cache[key][0]
            self._cache_misses += 1

        # 获取模型画像
        p = MODEL_PROFILES.get(profile, MODEL_PROFILES["standard"])

        def _call():
            resp = self.client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=messages,
                temperature=params.get("temperature", p["temperature"]),
                max_tokens=params.get("max_tokens", p["max_tokens"]),
            )
            return resp.choices[0].message.content

        result = self._retry_call(_call)

        if use_cache and "不可用" not in str(result):
            self._cache[self._cache_key(messages)] = (result, time.time())

        return result

    @property
    def cache_stats(self) -> dict:
        total = self._cache_hits + self._cache_misses
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": f"{self._cache_hits / max(total, 1) * 100:.0f}%",
        }
