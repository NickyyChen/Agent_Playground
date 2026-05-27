# -*- coding: utf-8 -*-
"""
17_context_window.py — Context Window 管理：超额防护
=====================================================

【概念】
LLM 有上下文窗口限制（如 DeepSeek 支持 128K tokens）。多轮对话中
messages 越来越长，超出窗口时 API 直接报错。Context Window 管理
就是一套"长对话不爆窗口"的策略。

三种策略：
  1. Token 计数：在发送前估算当前消息的 token 数，预警是否接近上限
  2. 滑动窗口：只保留最近 N 轮对话 + System Prompt，旧消息丢弃
  3. 摘要压缩：将早期对话压缩成摘要文本，释放空间但保留关键信息

【在智能客服中解决什么问题】
客服对话可能很长（用户来回确认细节、多次追问），不做窗口管理
到第 N 轮突然报错 → 用户体验断崖式下跌。

摘要策略特别适合客服：把前 5 轮对话压缩成 "用户咨询耳机退货，
已确认订单ORD001在7天退货期内" → 新消息有完整上下文但 token 极少。

【核心流程】
1. 每次调用前用 TokenCounter 估算当前 token 数
2. 接近窗口上限时触发策略:
   - 轻度超出 → 滑动窗口（丢最早的几轮）
   - 重度超出 → 摘要压缩（LLM 自动总结早期对话）
3. 压缩后继续对话

【pip install】
pip install openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │              Context Window 管理                      │
  │                                                       │
  │  messages 列表增长中...                                │
  │  ┌──────────────────────────────────────────────┐    │
  │  │ [system] [user1][asst1][user2][asst2]...[userN]│   │
  │  └──────────────────────────────────────────────┘    │
  │                    │                                  │
  │                    ▼ tokens > 阈值?                   │
  │               ┌─────────┐                            │
  │               │ 策略选择 │                            │
  │               └────┬────┘                            │
  │          ┌─────────┼─────────┐                       │
  │          ▼         ▼         ▼                       │
  │   ┌──────────┐ ┌────────┐ ┌──────────┐              │
  │   │ 滑动窗口  │ │ 摘要   │ │ 混合模式  │              │
  │   │ 保留最近  │ │ LLM压缩 │ │ 摘要+保留 │              │
  │   │ N条消息   │ │ 旧消息  │ │ 最近消息   │              │
  │   └──────────┘ └────────┘ └──────────┘              │
  └──────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm_client import chat


# ══════════════════════════════════════════════════════════════
# Token 计数器
# WHY: 不做精确 tokenize（需要 tokenizer 库），用字符数估算。
#      中文 ~2 字符/token，英文 ~4 字符/token，混合取 2.5。
#      生产环境应用 tiktoken 做精确计数。
# ══════════════════════════════════════════════════════════════

class TokenCounter:
    """Token 估算器"""
    def __init__(self, max_tokens: int = 8000, warning_ratio: float = 0.7):
        self.max_tokens = max_tokens
        self.warning_ratio = warning_ratio

    def count(self, messages: list[dict]) -> int:
        """估算 messages 的总 token 数"""
        total = 0
        for m in messages:
            content = m.get("content", "")
            # 中文 ~2 chars/token, 混合场景取 2.5
            total += len(content) / 2.5
        return int(total)

    def status(self, messages: list[dict]) -> str:
        """返回当前状态: ok / warning / critical"""
        tokens = self.count(messages)
        ratio = tokens / self.max_tokens
        if ratio < self.warning_ratio:
            return "ok"
        elif ratio < 0.95:
            return "warning"
        else:
            return "critical"


# ══════════════════════════════════════════════════════════════
# 策略1：滑动窗口
# WHY: 最简单直接——保留 system prompt + 最近 N 轮对话。
#      优点：实现简单、不会丢失细节
#      缺点：早期关键信息（如用户一开始说的订单号）可能被丢弃
# ══════════════════════════════════════════════════════════════

def sliding_window(messages: list[dict], keep_last: int = 6) -> list[dict]:
    """
    滑动窗口：保留 system 消息 + 最近 keep_last 条消息。
    """
    system_msgs = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]
    kept = rest[-keep_last:] if len(rest) > keep_last else rest
    result = system_msgs + kept
    removed = len(messages) - len(result)
    if removed > 0:
        print(f"    [滑动窗口] 丢弃了最早的 {removed} 条消息")
    return result


# ══════════════════════════════════════════════════════════════
# 策略2：摘要压缩
# WHY: 用 LLM 把早期对话压缩成摘要文本，替换原始消息。
#      优点：保留关键语义，释放大量 token 空间
#      缺点：LLM 摘要本身消耗 token（但远少于保留原始消息）
# ══════════════════════════════════════════════════════════════

def summarize_messages(messages: list[dict], keep_recent: int = 4) -> list[dict]:
    """
    摘要压缩：把早期消息压缩为摘要，保留最近几条原始消息。
    """
    system_msgs = [m for m in messages if m["role"] == "system"]
    rest = [m for m in messages if m["role"] != "system"]

    if len(rest) <= keep_recent:
        return messages  # 还没到需要压缩的长度

    old = rest[:-keep_recent]
    recent = rest[-keep_recent:]

    # WHY: 让 LLM 自己总结早期对话——比规则提取更完整
    old_text = "\n".join(
        f"{'用户' if m['role']=='user' else '客服'}: {m['content'][:200]}"
        for m in old
    )
    summary = chat([
        {"role": "system",
         "content": "将以下客服对话压缩为一段 100 字以内的摘要，保留关键信息"
                     "（订单号、商品名、用户需求、已确认的事实）。"},
        {"role": "user", "content": old_text},
    ], temperature=0.1)

    print(f"    [摘要压缩] 将 {len(old)} 条消息压缩为摘要 ({len(summary)} 字)")

    summary_msg = {
        "role": "system",
        "content": f"[对话历史摘要] {summary}"
    }
    return system_msgs + [summary_msg] + recent


# ══════════════════════════════════════════════════════════════
# Context Window Manager —— 自动选择策略
# ══════════════════════════════════════════════════════════════

class ContextWindowManager:
    """
    上下文窗口管理器。
    WHY: 集成计数 + 策略选择，一次 manage() 调用自动处理。
    """

    def __init__(self, max_tokens: int = 2000, keep_recent: int = 6):
        self.counter = TokenCounter(max_tokens)
        self.keep_recent = keep_recent

    def manage(self, messages: list[dict]) -> list[dict]:
        """
        检查并管理上下文窗口。返回（可能被压缩后的）消息列表。
        """
        tokens = self.counter.count(messages)
        status = self.counter.status(messages)

        print(f"    [Token: {tokens}/{self.counter.max_tokens} — {status}]")

        if status == "ok":
            return messages
        elif status == "warning":
            print(f"    ⚠ 接近窗口上限，启用滑动窗口")
            return sliding_window(messages, self.keep_recent)
        else:  # critical
            print(f"    🔴 即将超出窗口！启用摘要压缩")
            return summarize_messages(messages, self.keep_recent)


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

def demo_growing_conversation():
    """
    演示1：模拟长对话的增长 → 触发管理策略。
    """
    print("=" * 60)
    print(" 演示1：对话增长 → 触发 Context Window 管理")
    print("=" * 60)

    messages = [
        {"role": "system",
         "content": "你是小选，好买电商客服。回答简洁，不超过2句话。"},
    ]

    # WHY: 模拟一段较长的客服对话——用户多次追问，message 越积越多。
    #      用较短的 max_tokens 模拟"窗口很小"的场景，加速触发压缩。
    manager = ContextWindowManager(max_tokens=500, keep_recent=4)

    conversation = [
        ("user", "你好，我想咨询退货的事"),
        ("assistant", "您好！请提供订单号，我帮您查询退货条件。"),
        ("user", "订单号是 ORD20240001，买了漫步者降噪耳机"),
        ("assistant", "查到您的订单：漫步者 W820NB，签收于5月26日，"
         "目前仍在7天退货期内。"),
        ("user", "耳机包装我还没拆，能退吗？"),
        ("assistant", "未拆封的话完全符合无理由退货条件。"
         "您需要在App内提交退货申请。"),
        ("user", "退货流程大概多久？"),
        ("assistant", "提交申请后1-2天审核，审核通过后3-5天退款到账。"),
        ("user", "运费谁出？"),
        ("assistant", "无理由退货的运费由平台承担，您不需要付费。"),
        ("user", "那我能换货吗？如果耳机有质量问题的话"),
        ("assistant", "签收15天内出现质量问题可以免费换新。"
         "您的订单目前仍在15天换货期内。"),
    ]

    print("\n  模拟对话逐步增长:\n")

    for i, (role, content) in enumerate(conversation):
        messages.append({"role": role, "content": content})

        if role == "user" and i > 2:  # 每两轮检查一次
            print(f"  ── 第 {i//2 + 1} 轮后 ──")
            messages = manager.manage(messages)
            print()


def demo_sliding_vs_summary():
    """
    演示2：滑动窗口 vs 摘要压缩的效果对比。
    """
    print("=" * 60)
    print(" 演示2：两种策略的效果对比")
    print("=" * 60)

    # 构造一段长对话
    long_messages = [
        {"role": "system", "content": "你是小选，客服助手。"},
    ] + [
        m for pair in [
            ({"role": "user",
              "content": f"第{i}个问题，关于我的耳机订单ORD20240001"},
             {"role": "assistant",
              "content": f"第{i}个回答，您的订单状态正常。"})
            for i in range(1, 11)
        ] for m in pair
    ]

    original_tokens = TokenCounter(8000).count(long_messages)
    print(f"\n  原始消息: {len(long_messages)} 条, ~{original_tokens} tokens\n")

    # 滑动窗口
    print("  [滑动窗口 keep_last=4]:")
    sw = sliding_window(list(long_messages), keep_last=4)
    print(f"    结果: {len(sw)} 条消息")
    print(f"    内容: {[m['role'] for m in sw]}")

    # 摘要压缩
    print("\n  [摘要压缩 keep_recent=4]:")
    sm = summarize_messages(list(long_messages), keep_recent=4)
    print(f"    结果: {len(sm)} 条消息")
    print(f"    内容: {[m['role'] for m in sm]}")
    # 显示摘要内容
    for m in sm:
        if "摘要" in m.get("content", ""):
            print(f"    摘要: {m['content'][:120]}...")

    print("\n  ┌────────────────────┬───────────────────┐")
    print("  │ 策略               │ 适用场景            │")
    print("  ├────────────────────┼───────────────────┤")
    print("  │ 滑动窗口            │ 近期信息最重要      │")
    print("  │ 摘要压缩            │ 早期关键信息不能丢   │")
    print("  │ 混合 (摘要+保留)    │ 生产环境推荐        │")
    print("  └────────────────────┴───────────────────┘")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 17: Context Window 管理    ║")
    print("║  计数 → 预警 → 滑动窗口/摘要压缩                   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_growing_conversation()
    demo_sliding_vs_summary()

    print("=" * 60)
    print(" Demo 17 完成！窗口管理 = 长对话不爆 token")
    print("=" * 60)


if __name__ == "__main__":
    main()
