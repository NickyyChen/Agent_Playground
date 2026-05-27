# -*- coding: utf-8 -*-
"""
14_observability.py — Agent 可观测性：全链路追踪
=================================================

【概念】
生产环境的 Agent 不只是"能跑就行"——需要知道：
- 每个步骤花了多少时间？（延迟分析）
- 每次 LLM 调用消耗了多少 token？（成本分析）
- 检索召回了哪些文档？命中率如何？（质量分析）
- 工具调用了几次？哪一步是瓶颈？（性能分析）

这就是"可观测性"（Observability）——让你的 Agent 从黑盒变成白盒。

LangFuse / LangSmith 是外部 SaaS 追踪平台，本 Demo 手写一个本地追踪器，
核心概念完全相同：Span（跨度）、Trace（链路）、Metadata（元数据）。

【在智能客服中解决什么问题】
客服系统出问题时（回答太慢、检索不准、工具没调对），
没有追踪只能靠猜；有了追踪可以精确定位到"第三步的 LLM 调用
耗时 3.2s，是整体延迟的 80%"。

【核心流程】
1. Tracer 在每一步开始前记录时间戳和输入
2. 步骤结束后记录输出、耗时、token 消耗
3. 整个对话结束后生成追踪报告
4. 通过报告快速定位瓶颈

【pip install】
pip install openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────┐
  │               Agent 可观测性追踪                   │
  │                                                   │
  │  Trace: "用户: 退货咨询"                            │
  │  ┌─────────────────────────────────────────────┐  │
  │  │ Span 1: intent_classify   0.8s  120 tokens │  │
  │  │ Span 2: query_order       0.3s    -       │  │
  │  │ Span 3: llm_reasoning     2.1s  450 tokens │  │  ← 瓶颈!
  │  │ Span 4: final_answer      1.2s  300 tokens │  │
  │  └─────────────────────────────────────────────┘  │
  │  总耗时: 4.4s  总token: 870                        │
  │                                                   │
  │  → 报告: llm_reasoning 耗时占比 48%, 建议优化       │
  └──────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, time, functools
from datetime import datetime
from typing import Callable
from shared.llm_client import chat, create_completion
from shared.config import LLM_CONFIG


# ══════════════════════════════════════════════════════════════
# Trace 追踪系统
# WHY: 用 Span（跨度）记录每一步的耗时和元数据，
#      整个对话的 Span 组成一条 Trace（链路），
#      支持树形嵌套（一个 Span 内可以包含子 Span）
# ══════════════════════════════════════════════════════════════

class Span:
    """
    一个追踪跨度：记录单次操作的输入/输出/耗时/元数据。
    WHY: 每个 Span 有 start_time 和 end_time，
         duration 自动计算，metadata 按需附加任意信息。
    """
    def __init__(self, name: str, parent: "Span" = None):
        self.name = name
        self.parent = parent
        self.children = []
        self.start_time = time.time()
        self.end_time = None
        self.metadata = {}
        self.input_summary = ""
        self.output_summary = ""

    def finish(self, **metadata):
        self.end_time = time.time()
        self.metadata.update(metadata)
        if self.parent:
            self.parent.children.append(self)

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 1),
            "input": self.input_summary,
            "output": self.output_summary,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class Tracer:
    """
    追踪器：收集一次对话中的所有 Span，生成追踪报告。
    WHY: 全局单例，方便在任何函数中创建 Span。
    """
    def __init__(self, trace_name: str):
        self.trace_name = trace_name
        self.root_spans = []
        self._stack: list[Span] = []

    def start_span(self, name: str, input_summary: str = "") -> Span:
        parent = self._stack[-1] if self._stack else None
        span = Span(name, parent)
        span.input_summary = input_summary
        self._stack.append(span)
        if not parent:
            self.root_spans.append(span)
        return span

    def end_span(self, span: Span, output_summary: str = "", **metadata):
        span.output_summary = output_summary
        span.finish(**metadata)
        if self._stack and self._stack[-1] == span:
            self._stack.pop()

    def report(self) -> str:
        """生成人类可读的追踪报告"""
        lines = []
        total_ms = sum(s.duration_ms for s in self.root_spans)
        total_tokens = 0
        tool_calls = 0

        def collect_stats(spans):
            nonlocal total_tokens, tool_calls
            for s in spans:
                total_tokens += s.metadata.get("tokens", 0)
                if s.metadata.get("type") == "tool_call":
                    tool_calls += 1
                collect_stats(s.children)

        collect_stats(self.root_spans)

        lines.append(f"╔══════════════════════════════════════════╗")
        lines.append(f"║  Trace: {self.trace_name}")
        lines.append(f"╠══════════════════════════════════════════╣")
        lines.append(f"║  总耗时: {total_ms:.0f}ms | Token: {total_tokens} "
                     f"| 工具调用: {tool_calls}次")
        lines.append(f"╠══════════════════════════════════════════╣")

        def render(spans, indent=0):
            prefix = "  " * indent
            for s in spans:
                bar = _bar(s.duration_ms, total_ms, width=20)
                meta_parts = []
                if s.metadata.get("tokens"):
                    meta_parts.append(f"token:{s.metadata['tokens']}")
                if s.metadata.get("type"):
                    meta_parts.append(s.metadata["type"])
                meta = f" | {', '.join(meta_parts)}" if meta_parts else ""

                lines.append(
                    f"{prefix}├─ {s.name:<25s} {s.duration_ms:>7.0f}ms "
                    f"{bar}{meta}"
                )
                render(s.children, indent + 1)

        render(self.root_spans)

        # 瓶颈分析
        lines.append(f"╠══════════════════════════════════════════╣")
        all_spans = []

        def flatten(spans):
            for s in spans:
                all_spans.append(s)
                flatten(s.children)
        flatten(self.root_spans)

        llm_spans = [s for s in all_spans if s.metadata.get("type") == "llm_call"]
        if llm_spans:
            slowest = max(llm_spans, key=lambda s: s.duration_ms)
            lines.append(f"║  ⚠ 瓶颈分析:")
            lines.append(f"║  最慢 LLM 调用: {slowest.name} "
                         f"({slowest.duration_ms:.0f}ms)")
            lines.append(f"║  LLM 总耗时占比: "
                         f"{sum(s.duration_ms for s in llm_spans) / total_ms * 100:.0f}%")
            lines.append(f"║  平均 LLM 延迟: "
                         f"{sum(s.duration_ms for s in llm_spans) / len(llm_spans):.0f}ms")

        lines.append(f"╚══════════════════════════════════════════╝")
        return "\n".join(lines)


def _bar(value: float, total: float, width: int = 20) -> str:
    """画耗时占比条"""
    if total == 0:
        return ""
    ratio = value / total
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


# ─── 全局追踪器实例 ────────────────────────────
_tracer: Tracer = None


def get_tracer() -> Tracer:
    return _tracer


# ══════════════════════════════════════════════════════════════
# 带追踪的 LLM 调用封装
# WHY: 包装 shared/llm_client.py 的 chat()，在每次 LLM 调用
#      前后自动创建 Span 和记录耗时/输入/输出摘要。
#      对业务代码透明——原本调 chat() 的地方只需要换这个函数。
# ══════════════════════════════════════════════════════════════

def traced_chat(messages: list[dict], span_name: str = "llm_call",
                **kwargs) -> str:
    """带追踪的 LLM 调用"""
    tracer = get_tracer()
    user_msg = next((m["content"][:50] for m in messages
                     if m["role"] == "user"), "")
    span = tracer.start_span(span_name, user_msg)

    result = chat(messages, **kwargs)

    tracer.end_span(span,
                    output_summary=result[:60],
                    type="llm_call",
                    tokens=_estimate_tokens(messages, result),
                    model=LLM_CONFIG["model"])
    return result


def traced_tool_call(tool_name: str, args: dict, fn: Callable) -> str:
    """带追踪的工具调用"""
    tracer = get_tracer()
    span = tracer.start_span(f"tool:{tool_name}",
                             f"{tool_name}({json.dumps(args, ensure_ascii=False)})")

    t0 = time.time()
    result = fn(**args)
    t1 = time.time()

    tracer.end_span(span,
                    output_summary=str(result)[:80],
                    type="tool_call",
                    tool_name=tool_name,
                    args=args)
    return result


def _estimate_tokens(messages: list, result: str) -> int:
    """
    估算 token 消耗。
    WHY: 用字符数粗略估算。中文约 2 字符/token，英文约 4 字符/token。
    """
    total_chars = 0
    for m in messages:
        content = getattr(m, "content", "") if hasattr(m, "content") else \
                  m.get("content", "") if isinstance(m, dict) else ""
        total_chars += len(str(content))
    total_chars += len(result)
    return total_chars // 2  # 粗略估算


# ══════════════════════════════════════════════════════════════
# 演示：用追踪器跑一次多步 Agent 对话
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是小选，好买电商智能客服。回答简洁专业。
你可以使用工具查询订单和物流。"""


def demo_traced_agent():
    """
    演示1：多步 Agent 全链路追踪。
    WHY: 用追踪器跑一次"先查订单→再查物流→综合回答→追问"的
         完整对话，展示每个步骤的耗时和 token 消耗。
    """
    print("=" * 60)
    print(" 演示1：全链路追踪 —— 多步对话每步耗时可见")
    print("=" * 60)

    global _tracer
    _tracer = Tracer("客服对话: 订单咨询+物流查询+追问")

    from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY

    def query_order(order_id: str) -> str:
        return json.dumps(MOCK_ORDERS.get(order_id, {}),
                          ensure_ascii=False)

    def query_logistics(tracking_no: str) -> str:
        return json.dumps(MOCK_LOGISTICS.get(tracking_no, {}),
                          ensure_ascii=False)

    TOOLS = [
        {"type": "function", "function": {
            "name": "query_order",
            "description": "查订单",
            "parameters": {"type": "object",
                           "properties": {"order_id": {"type": "string"}},
                           "required": ["order_id"]}
        }},
        {"type": "function", "function": {
            "name": "query_logistics",
            "description": "查物流",
            "parameters": {"type": "object",
                           "properties": {"tracking_no": {"type": "string"}},
                           "required": ["tracking_no"]}
        }},
    ]

    TOOL_FNS = {"query_order": query_order,
                "query_logistics": query_logistics}

    # ─── 第 1 轮：用户问订单+物流 ─────────────────
    print(" 用户: 订单ORD20240001发货了吗？物流到哪了？\n")

    main_span = _tracer.start_span("round1_agent_loop",
                                   "用户问订单+物流")

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",
                 "content": "订单ORD20240001发货了吗？快递号SF1234567890到哪了？"}]

    # Step 1: LLM 推理
    llm_span = _tracer.start_span("llm_reasoning", "分析用户需求")

    response = create_completion(messages, tools=TOOLS, temperature=0.1)
    msg = response.choices[0].message

    _tracer.end_span(llm_span, "决定调 query_order + query_logistics",
                     type="llm_call",
                     tokens=_estimate_tokens(messages, str(msg)))

    # Step 2: 执行工具
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            args = json.loads(tc.function.arguments)
            result = traced_tool_call(fn_name, args, TOOL_FNS[fn_name])
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": result})

        # Step 3: LLM 综合回答
        final = traced_chat(messages, span_name="llm_final_answer")
        print(f"  客服: {final}\n")

    _tracer.end_span(main_span, "完成第1轮", type="agent_round")

    # ─── 第 2 轮：追问 ──────────────────────────
    print(" 用户: 那耳机质量有问题能换吗？\n")

    span2 = _tracer.start_span("round2_followup", "追问换货政策")

    messages.append({"role": "assistant", "content": final})
    messages.append({"role": "user", "content": "那耳机质量有问题能换吗？"})

    follow_up_reply = traced_chat(messages, span_name="llm_followup_answer")
    print(f"  客服: {follow_up_reply}")

    _tracer.end_span(span2, "完成追问", type="agent_round")

    # ─── 生成报告 ───────────────────────────────
    print()
    print(_tracer.report())


def demo_trace_report():
    """
    演示2：追踪报告解读 —— 如何从 Trace 中找到瓶颈。
    """
    print("\n" + "=" * 60)
    print(" 演示2：如何读懂追踪报告")
    print("=" * 60)

    print("""
  追踪报告关键指标解读：

  ┌─────────────────┬──────────────────────────────┐
  │ 指标             │ 优化方向                       │
  ├─────────────────┼──────────────────────────────┤
  │ LLM调用耗时 > 3s  │ 换更快的模型 or 减少 prompt 长度│
  │ Token消耗 > 2000  │ 缩短上下文 or 增加工具调用      │
  │ 工具调用次数 > 5   │ 合并查询 or 减少串行依赖        │
  │ LLM耗时占比 > 70% │ 本地缓存常用回答               │
  │ 检索耗时占比 > 50% │ 换更小的嵌入模型 or 增加索引     │
  └─────────────────┴──────────────────────────────┘

  生产环境建议接入 LangFuse / LangSmith 实现持久化存储和可视化看板。
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 14: 可观测性追踪           ║")
    print("║  Span → Trace → 瓶颈分析                         ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_traced_agent()
    demo_trace_report()

    print("=" * 60)
    print(" Demo 14 完成！可观测性 = 让 Agent 不再黑盒")
    print("=" * 60)


if __name__ == "__main__":
    main()
