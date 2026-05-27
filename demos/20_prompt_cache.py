# -*- coding: utf-8 -*-
"""
20_prompt_cache.py — Prompt 缓存：相同前缀复用，降本提速
========================================================

【概念】
每次 LLM API 调用都要把整个 messages 发送过去，服务端对所有 token 做
自注意力计算。但大多数客服对话中，system prompt 是完全相同的——每次都
重新计算一遍是巨大浪费。

Prompt 缓存机制：API 自动缓存最近请求中已经计算过的"前缀部分"（prefix），
后续请求如果前缀相同 → 跳过这部分计算 → 延迟更低、成本更便宜。

DeepSeek 支持自动前缀缓存，命中时：
  - 输入 token 费用优惠（缓存命中部分通常免费或大幅折扣）
  - 首 token 延迟降低 50%+

【在智能客服中解决什么问题】
客服 System Prompt（包含人设、政策速查、工具说明）通常 500-2000 token，
每次对话都重复发送。缓存命中后，这些 token 不再计费——
每天 10 万次调用，省 90% 输入成本。

【核心流程】
1. 将不变内容（system prompt + 工具定义）放在 messages 最前面
2. 将变化内容（对话历史 + 用户新消息）放在最后面
3. API 检测到前缀与之前请求相同 → 命中缓存
4. 如果中途修改了 system prompt → 缓存失效 → 全量重算

【pip install】
pip install openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │                  Prompt 缓存原理                      │
  │                                                       │
  │  请求 1:                                               │
  │  ┌──────────────────────┐ ┌──────────────────────┐   │
  │  │ System Prompt (固定)  │ │ user: "查订单001"     │   │
  │  │ 800 tokens           │ │ (变化部分)            │   │
  │  │           ← 缓存 ──→  │ │                      │   │
  │  └──────────────────────┘ └──────────────────────┘   │
  │                                                       │
  │  请求 2:                                               │
  │  ┌──────────────────────┐ ┌──────────────────────┐   │
  │  │ System Prompt (相同!) │ │ user: "退货政策?"     │   │
  │  │ ✅ 缓存命中，跳过计算  │ │ 重新计算              │   │
  │  │ 输入成本: 0 (免费)     │ │ 输入成本: 10 tokens   │   │
  │  └──────────────────────┘ └──────────────────────┘   │
  │                                                       │
  │  关键原则:                                             │
  │  - 固定内容在前 → 最大化缓存命中                       │
  │  - 变化内容在后 → 缓存断点之后的才重新计算              │
  │  - 不要在固定内容前插入变化内容 → 缓存失效             │
  └──────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import time, hashlib
from shared.llm_client import chat


# ══════════════════════════════════════════════════════════════
# 本地缓存模拟 —— 演示缓存命中的逻辑
# WHY: API 端的缓存是自动的，但我们可以在本地也做一层缓存，
#      对完全相同的请求直接返回缓存结果，连 API 都不调用。
#      这里用简单的 hash 模拟缓存键匹配。
# ══════════════════════════════════════════════════════════════

class LocalPromptCache:
    """
    本地 Prompt 缓存模拟。
    WHY: 不是替代 API 端的缓存，而是演示缓存命中的逻辑——
         相同的 prompt 前缀 → 命中 → 直接返回，不调用 API。
    """
    def __init__(self):
        self._store = {}  # cache_key → (reply, timestamp)
        self.hits = 0
        self.misses = 0

    def get_key(self, messages: list[dict]) -> str:
        """生成缓存键（基于完整消息的 hash，完全相同的请求才命中）"""
        full = json_dumps(messages)
        return hashlib.md5(full.encode()).hexdigest()

    def get(self, key: str) -> str | None:
        """尝试命中缓存"""
        if key in self._store:
            self.hits += 1
            return self._store[key][0]
        self.misses += 1
        return None

    def set(self, key: str, reply: str):
        self._store[key] = (reply, time.time())


_cache = LocalPromptCache()


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


# ══════════════════════════════════════════════════════════════
# 缓存感知的消息构建
# WHY: 把消息分为"静态前缀"和"动态后缀"两部分——
#      messages[:static_len] = system prompt + 工具定义（不变）
#      messages[static_len:] = 对话历史 + 用户新输入（每次变化）
#      这样 API（和本地缓存）可以缓存静态前缀的计算结果。
# ══════════════════════════════════════════════════════════════

# ─── 静态前缀：不随每次对话改变 ──────────────────────
# WHY: 这段内容在所有客服对话中都一样，
#      放在 messages 最前面 → API 每次都缓存这部分计算
STATIC_PREFIX = [
    {"role": "system",
     "content": """你是"小选"，好买电商平台的智能客服助手。

你的职责：
- 回答简洁专业，不超过3句话
- 涉及退换货/退款时，必须引用平台政策
- 对价格、库存等实时信息，诚实说明无法查询
- 态度友好，对投诉用户优先安抚情绪

平台核心政策速查：
- 退货：签收后7天内，商品完好、配件齐全可申请退货，运费平台承担
- 换货：签收后15天内，质量问题免费换新，人为损坏不换
- 退款：退货签收后3个工作日内原路退回
- 耳机等个人卫生用品拆封后不支持无理由退货"""  # ~350 tokens
     },
]

STATIC_PREFIX_LEN = len(STATIC_PREFIX)


def build_messages(user_input: str,
                   history: list[dict] = None) -> tuple[list[dict], int]:
    """
    构建缓存友好的 messages 列表。
    返回 (messages, static_len)，static_len 是静态前缀的长度。
    """
    messages = list(STATIC_PREFIX)  # 静态前缀（可缓存）
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    
    # WHY: 静态前缀长度 = 1 (system prompt)，后续对话历史是动态的
    return messages, STATIC_PREFIX_LEN


# ══════════════════════════════════════════════════════════════
# 带缓存的客服调用
# ══════════════════════════════════════════════════════════════

def cached_chat(user_input: str, history: list[dict] = None,
                use_cache: bool = True) -> tuple[str, dict]:
    """
    带缓存的客服调用。两层缓存语义：
    - 本地缓存：完全相同的问题+历史 → 直接返回（不调 API）
    - API 前缀缓存：system prompt 相同 → API 端自动跳过前缀计算
    """
    messages, static_len = build_messages(user_input, history)
    stats = {
        "input_tokens": _estimate(messages),
        "cached_tokens": 0,     # API 端前缀缓存节省的 token
        "cache_hit": False,     # 本地缓存命中
        "latency_ms": 0,
    }

    # ── 本地缓存：完全相同才命中 ──
    if use_cache:
        full_key = _cache.get_key(messages)
        cached = _cache.get(full_key)
        if cached:
            stats["cache_hit"] = True
            stats["cached_tokens"] = _estimate(messages[:static_len])
            stats["latency_ms"] = 1
            return cached, stats

    # ── API 调用：system prompt 前缀相同 → API 端自动缓存前缀计算 ──
    # 即使本地缓存没命中，API 端的前缀缓存也会生效（节省 system prompt 的计算）
    t0 = time.time()
    reply = chat(messages)
    stats["latency_ms"] = (time.time() - t0) * 1000
    # WHY: 每次调用都受益于 API 前缀缓存（system prompt 每次都相同）
    stats["cached_tokens"] = _estimate(messages[:static_len])

    if use_cache:
        _cache.set(full_key, reply)

    return reply, stats


def _estimate(messages: list[dict]) -> int:
    return sum(len(m.get("content", "")) for m in messages) // 2


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

def demo_cache_basics():
    """
    演示1：缓存基础 —— 相同 system prompt 的多次调用。
    """
    print("=" * 60)
    print(" 演示1：缓存命中 vs 未命中")
    print("=" * 60)

    print(f"\n  静态前缀大小: ~{_estimate(STATIC_PREFIX)} tokens")
    print(f"  (这段内容在所有请求中相同 → 可以被缓存)")
    print()

    questions = [
        "退货需要什么条件？",
        "退货需要什么条件？",  # 重复 → 缓存命中
        "耳机能退货吗？",
        "耳机能退货吗？",      # 重复 → 缓存命中
    ]

    total_saved = 0
    for i, q in enumerate(questions):
        reply, stats = cached_chat(q)
        status = "✅ 缓存命中" if stats["cache_hit"] else "🆕 API 调用"
        saved = stats["cached_tokens"]
        total_saved += saved

        print(f"  [{i+1}] 用户: {q}")
        print(f"      {status} | 延迟: {stats['latency_ms']:.0f}ms | "
              f"缓存节省: ~{saved} tokens")
        print(f"      回答: {reply[:80]}...")
        print()

    print(f"  总计缓存节省: ~{total_saved} tokens")
    print(f"  缓存命中率: {_cache.hits}/{_cache.hits + _cache.misses}")


def demo_cache_aware_ordering():
    """
    演示2：消息顺序对缓存的影响。
    WHY: 缓存基于"前缀"——messages 的前缀变化时缓存失效。
         所以必须把变化的消息放在后面。
    """
    print("\n" + "=" * 60)
    print(" 演示2：消息顺序决定缓存效率")
    print("=" * 60)

    print("""
  ✅ 缓存友好（固定在前，变化在后）:
     messages = [
       system_prompt,     ← 缓存命中！
       user_msg_1,        ← 重新计算
     ]

  ❌ 缓存不友好（变化在前，固定在后）:
     messages = [
       user_msg_1,        ← 前缀变了
       system_prompt,     ← 全部重算！
     ]
     → 每次 user_msg 不同，整个 messages 前缀都不同 → 永远不命中

  ┌───────────────────────┬──────────────────────┐
  │ 缓存友好模式           │ 缓存不友好模式         │
  ├───────────────────────┼──────────────────────┤
  │ 1. system (固定)      │ 1. user (变化)        │
  │ 2. 工具定义 (固定)     │ 2. system (固定)      │
  │ 3. 历史对话 (变化)     │ 3. 工具定义 (固定)     │
  │ 4. 用户新输入 (变化)   │ 4. 历史对话 (变化)     │
  │                       │ 5. 用户新输入 (变化)   │
  │ → 缓存前缀 = 1+2      │ → 缓存前缀 = 0        │
  │ → 命中率 ≈ 100%       │ → 命中率 ≈ 0%         │
  └───────────────────────┴──────────────────────┘
""")


def demo_multiround_cache():
    """
    演示3：多轮对话的缓存效率。
    """
    print("=" * 60)
    print(" 演示3：多轮对话 —— 缓存效果累积")
    print("=" * 60)

    history = []
    dialogue = [
        "我想退货",
        "订单 ORD20240001",
        "包装没拆，用了3天",
        "有什么注意事项吗？",
    ]

    total_input = 0
    total_cached = 0

    for i, q in enumerate(dialogue):
        reply, stats = cached_chat(q, history)
        total_input += stats["input_tokens"]
        total_cached += stats["cached_tokens"]

        print(f"  [轮次{i+1}] 用户: {q}")
        print(f"      输入: ~{stats['input_tokens']}t | "
              f"缓存: ~{stats['cached_tokens']}t | "
              f"{'命中' if stats['cache_hit'] else '未命中'}")

        history.append({"role": "user", "content": q})
        history.append({"role": "assistant", "content": reply})

    print(f"\n  总计: 输入 {total_input}t → 缓存节省 {total_cached}t "
          f"({total_cached / max(total_input, 1) * 100:.0f}%)")
    print(f"  说明: system prompt 在每轮都命中缓存，"
          f"只有对话历史是新增消耗")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 20: Prompt 缓存            ║")
    print("║  固定前缀缓存 → 降本提速                           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_cache_basics()
    demo_cache_aware_ordering()
    demo_multiround_cache()

    print("=" * 60)
    print(" Demo 20 完成！缓存 = 同样的前缀不算第二遍")
    print("=" * 60)


if __name__ == "__main__":
    main()
