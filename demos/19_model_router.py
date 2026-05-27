# -*- coding: utf-8 -*-
"""
19_model_router.py — 模型路由：简单问题用快模型，复杂问题用强模型
================================================================

【概念】
不是所有客服问题都需要最强的模型。"你好在吗"和"对比三款耳机的频响曲线
并推荐一款适合古典乐的"——前者用快模型 0.5 秒搞定，后者才需要深度推理。

模型路由（Model Router）的核心思路：
  1. 用一个轻量的"路由 LLM"分析用户问题的复杂度
  2. 简单问题 → 调快模型（低成本、低延迟）
  3. 复杂问题 → 调强模型（高准确、完整推理）
  4. 结果：省成本的同时保证体验

【在智能客服中解决什么问题】
客服系统 80% 的问题是简单 FAQ（"退货几天""客服电话多少"），
只有 20% 需要深度推理（多工具调用、政策对比）。
路由后，80% 的请求成本降到原来的 1/10——省大钱。

【核心流程】
1. Router 分析用户输入 → 输出 complexity: "simple" | "medium" | "complex"
2. simple → FastProfile（低temperature, 简 prompt）
3. medium → StandardProfile（常规处理）
4. complex → PremiumProfile（完整prompt, 多工具, 深度推理）

【pip install】
pip install openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │                    Model Router                       │
  │                                                       │
  │   用户输入                                             │
  │      │                                                │
  │      ▼                                                │
  │  ┌──────────┐  复杂度评分                              │
  │  │  Router   │───┬──── simple ────▶ Fast 模型          │
  │  │  (分类)   │   │                 (0.3s, ~0.01元)     │
  │  └──────────┘   ├──── medium ───▶ Standard 模型        │
  │                 │                 (0.8s, ~0.05元)      │
  │                 └──── complex ──▶ Premium 模型          │
  │                                   (2.0s, ~0.15元)      │
  │                                                       │
  │  成本节省: 80% simple × (0.05-0.01)/0.05 = 节省约 64%  │
  └──────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json, time
from dataclasses import dataclass
from shared.llm_client import chat


# ══════════════════════════════════════════════════════════════
# 模型画像 —— 模拟三档"虚拟模型"
# WHY: 真实部署中有多个模型可选（如 DeepSeek-V3 vs R1 vs 蒸馏版），
#      这里用参数配置模拟不同模型的能力/成本/延迟画像。
#      temperature 低 → 更确定（快模型），
#      max_tokens 高 → 更适合复杂推理（强模型）。
# ══════════════════════════════════════════════════════════════

@dataclass
class ModelProfile:
    """虚拟模型画像"""
    name: str
    description: str
    temperature: float
    max_tokens: int
    # WHY: 模拟成本和延迟——虽然同一个 API，但不同参数配置
    #      模拟了"廉价模型"和"贵模型"的差异
    estimated_cost_per_call: float  # 模拟成本（元）
    estimated_latency_ms: int       # 模拟延迟

    def call(self, messages: list[dict], **kwargs) -> tuple[str, float, float]:
        """调用并返回 (回答, 耗时, 成本)"""
        t0 = time.time()
        params = {"temperature": self.temperature, "max_tokens": self.max_tokens}
        params.update(kwargs)
        reply = chat(messages, **params)
        elapsed = (time.time() - t0) * 1000
        return reply, elapsed, self.estimated_cost_per_call


# ─── 三档模型 ───────────────────────────────────────

FAST_MODEL = ModelProfile(
    name="Fast (模拟轻量模型)",
    description="简单问答：问候、FAQ、单步查询",
    temperature=0.0,        # 零温度，输出最确定
    max_tokens=150,         # 短回答
    estimated_cost_per_call=0.005,
    estimated_latency_ms=300,
)

STANDARD_MODEL = ModelProfile(
    name="Standard (模拟标准模型)",
    description="常规处理：订单+政策查询，1-2步推理",
    temperature=0.3,
    max_tokens=400,
    estimated_cost_per_call=0.03,
    estimated_latency_ms=800,
)

PREMIUM_MODEL = ModelProfile(
    name="Premium (模拟强推理模型)",
    description="复杂推理：多工具调用、对比分析、长文本理解",
    temperature=0.5,
    max_tokens=800,
    estimated_cost_per_call=0.10,
    estimated_latency_ms=2000,
)


# ══════════════════════════════════════════════════════════════
# Router —— 复杂度分类器
# WHY: Router 本身也是一个 LLM 调用，但它用的是最简单的 prompt
#      （只输出一个词），token 消耗极低（~10 tokens），
#      路由开销几乎可以忽略。
# ══════════════════════════════════════════════════════════════

ROUTER_PROMPT = """分析以下用户消息的复杂度，只输出一个词：

- simple: 简单问候、FAQ（退货几天、电话多少）、无需工具
- medium: 需要查一个工具或一步推理（查订单、查物流）
- complex: 多步推理、多工具、对比分析、投诉处理

输出格式（只输出一个词，无其他内容）：
simple|medium|complex"""


def route(user_input: str) -> tuple[str, ModelProfile]:
    """
    分析用户输入复杂度，返回 (complexity, model_profile)。
    """
    reply = chat([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": user_input},
    ], temperature=0, max_tokens=10)

    complexity = reply.strip().lower()
    if "complex" in complexity:
        return "complex", PREMIUM_MODEL
    elif "medium" in complexity:
        return "medium", STANDARD_MODEL
    else:
        return "simple", FAST_MODEL


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPTS = {
    "simple": "你是小选，客服助手。一句话回答。",
    "medium": "你是小选，好买电商客服。回答简洁专业，不超过3句话。",
    "complex": """你是小选，好买电商资深客服专家。请仔细分析用户问题，做出完整推理。
需要时可以用工具查询数据。回答结构化、有依据、覆盖所有用户关注点。""",
}


def demo_router_decisions():
    """
    演示1：Router 对不同问题的分流决策。
    """
    print("=" * 60)
    print(" 演示1：Router 分流决策 —— 不同复杂度 → 不同模型")
    print("=" * 60)

    test_cases = [
        "你好，在吗？",
        "退货几天能办好？",
        "帮我查一下订单 ORD20240001 的状态",
        "我买了耳机左耳有杂音，这是质量问题吗？能退款还是只能换？"
        "另外马上618了我再买一款有没有优惠？",
        "对比一下漫步者W820NB和Sony XM5，我是学生预算有限，"
        "主要用来看网课和听古典乐，推荐哪个？",
    ]

    total_cost_no_route = 0
    total_cost_with_route = 0

    print(f"\n  {'问题':<40s} {'复杂度':<10s} {'模型':<12s} {'成本':>8s}")
    print(f"  {'─'*40} {'─'*10} {'─'*12} {'─'*8}")

    for q in test_cases:
        complexity, model = route(q)

        # 无路由: 全部用 premium
        cost_no = PREMIUM_MODEL.estimated_cost_per_call
        # 有路由: 按复杂度选模型
        cost_with = model.estimated_cost_per_call

        total_cost_no_route += cost_no
        total_cost_with_route += cost_with

        print(f"  {q[:38]:<40s} {complexity:<10s} "
              f"{'[' + model.name.split('(')[0].strip() + ']':<12s} "
              f"¥{cost_with:>.3f}")

    print(f"\n  ┌──────────────────────────────────────┐")
    print(f"  │ 无路由 (全部用 Premium):             ¥{total_cost_no_route:.3f}")
    print(f"  │ 有路由 (按需分级):                   ¥{total_cost_with_route:.3f}")
    print(f"  │ 成本节省:                            "
          f"{(1 - total_cost_with_route / total_cost_no_route) * 100:.0f}%")
    print(f"  └──────────────────────────────────────┘")


def demo_simple_vs_premium():
    """
    演示2：同一个问题，三档模型回答风格对比。
    """
    print("\n" + "=" * 60)
    print(" 演示2：三档模型对比 —— 同问题不同深度")
    print("=" * 60)

    question = "耳机退货政策是什么？"

    for complexity, model in [("simple", FAST_MODEL),
                                ("medium", STANDARD_MODEL),
                                ("complex", PREMIUM_MODEL)]:
        system = SYSTEM_PROMPTS[complexity]
        reply, elapsed, cost = model.call([
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ])
        print(f"\n  [{model.name.split('(')[0].strip()}] "
              f"(t={elapsed:.0f}ms, ¥{cost:.3f})")
        print(f"  → {reply[:150]}")


def demo_routing_strategy():
    """
    演示3：路由策略设计指南。
    """
    print("\n" + "=" * 60)
    print(" 演示3：路由策略设计原则")
    print("=" * 60)

    print("""
  路由判断维度：

  ┌──────────────────┬──────────────┬──────────────┐
  │ 维度              │ → 简单模型    │ → 强模型      │
  ├──────────────────┼──────────────┼──────────────┤
  │ 输入长度          │ < 100 字符    │ > 500 字符    │
  │ 是否需要工具       │ 否           │ 是 (多步)     │
  │ 是否涉及投诉/情绪   │ 否           │ 是 (安抚+处理) │
  │ 历史消息轮次       │ < 3 轮       │ > 10 轮      │
  │ 是否需要结构化输出  │ 否           │ 是 (JSON等)  │
  │ 置信度阈值         │ > 0.9        │ < 0.7        │
  └──────────────────┴──────────────┴──────────────┘

  进阶模式：
  - 级联路由: 先用简单模型 → 如果回答质量不够 → 升级到强模型
  - 用户分层: VIP 用户始终用强模型（体验优先）
  - 时段策略: 高峰期优先快模型（保吞吐），低峰用强模型（保质量）
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 19: 模型路由               ║")
    print("║  simple→fast  |  medium→standard  |  complex→premium ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_router_decisions()
    demo_simple_vs_premium()
    demo_routing_strategy()

    print("=" * 60)
    print(" Demo 19 完成！路由 = 好钢用在刀刃上")
    print("=" * 60)


if __name__ == "__main__":
    main()
