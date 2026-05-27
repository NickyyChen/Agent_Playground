# -*- coding: utf-8 -*-
"""
18_error_handling.py — Agent 错误处理与重试
===========================================

【概念】
Agent 不是运行在真空里——LLM 可能超时、工具可能故障、回复格式可能
乱掉。生产环境的 Agent 必须处理三类错误：

  1. LLM 调用异常：超时、限流、服务不可用 → 重试 + 降级
  2. 工具执行异常：函数报错、网络不通 → 捕获 + 兜底
  3. 输出格式异常：JSON 解析失败、字段缺失 → 修复 + 重试

每一类错误有对应的恢复策略，组合起来就是 Agent 的"韧性（Resilience）"。

【在智能客服中解决什么问题】
用户问"我的订单到哪了"，Agent 调 query_order 但 Mock 数据挂了
→ 不能直接崩溃返回 "500 Error"，而应该说 "系统繁忙，请稍后再试"。

【核心流程】
1. 每次 LLM 调用包装 try/except + 指数退避重试
2. 工具调用包装 try/except + 降级兜底
3. JSON 解析失败 → 提示 LLM 修正格式 → 重试
4. 熔断器：连续失败 N 次后不再尝试，直接降级

【pip install】
pip install openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │                Agent 错误处理三层防护                  │
  │                                                       │
  │  Layer 1: LLM 调用                                     │
  │  ┌──────────┐  失败  ┌──────────┐ 3次都失败 ┌───────┐ │
  │  │ 调用LLM   │──────▶│ 指数退避  │─────────▶│ 降级  │ │
  │  │          │       │ 重试 3次  │          │ 兜底  │ │
  │  └──────────┘       └──────────┘          └───────┘ │
  │                                                       │
  │  Layer 2: 工具执行                                     │
  │  ┌──────────┐  异常  ┌──────────┐                    │
  │  │ 调用工具  │──────▶│ 捕获异常  │→ 友好错误提示        │
  │  └──────────┘       └──────────┘                    │
  │                                                       │
  │  Layer 3: 输出解析                                     │
  │  ┌──────────┐  失败  ┌──────────┐                   │
  │  │ 解析JSON  │──────▶│ 修正重试  │→ 实在不行 → 降级   │
  │  └──────────┘       └──────────┘    用原始文本        │
  └──────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json, time, random, functools
from typing import Callable
from shared.llm_client import chat
from shared.mock_data import MOCK_ORDERS


# ══════════════════════════════════════════════════════════════
# Layer 1: LLM 调用重试 —— 指数退避
# WHY: LLM API 可能因网络抖动/限流/服务过载而失败，
#      指数退避（1s → 2s → 4s）给服务恢复时间，
#      max_retries=3 防止无限等待。
# ══════════════════════════════════════════════════════════════

def with_llm_retry(max_retries: int = 3, base_delay: float = 1.0):
    """
    装饰器：给 LLM 调用加指数退避重试。
    WHY: 不是简单 while 循环——指数退避 + 随机抖动(jitter)
         避免"惊群效应"（大量请求同时重试压垮服务）。
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        # WHY: 指数退避 + 随机抖动——
                        #      第1次等1s, 第2次等2s, 第3次等4s,
                        #      加 0~25% 随机抖动避免同时重试
                        delay = base_delay * (2 ** (attempt - 1))
                        jitter = random.uniform(0, delay * 0.25)
                        total_delay = delay + jitter
                        print(f"    ⚠ LLM 调用失败 (尝试 {attempt}/{max_retries}): "
                              f"{e}, {total_delay:.1f}s 后重试...")
                        time.sleep(total_delay)
            # 所有重试都失败 → 返回降级消息
            print(f"    🔴 LLM 调用全部 {max_retries} 次失败: {last_error}")
            return f"抱歉，AI 服务暂时不可用，请稍后再试或拨打客服热线 400-800-8888。"
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════
# Layer 2: 工具调用保护 —— 异常捕获 + 兜底
# WHY: 工具函数可能因为数据问题、网络问题抛异常，
#      不能让它直接崩到用户面前——必须 catch 并返回可读信息。
# ══════════════════════════════════════════════════════════════

def safe_tool_call(func: Callable, tool_name: str,
                   fallback_msg: str = None, **kwargs) -> str:
    """
    安全工具调用：捕获所有异常，返回兜底消息。
    """
    try:
        return func(**kwargs)
    except Exception as e:
        print(f"    ⚠ 工具 [{tool_name}] 异常: {e}")
        if fallback_msg:
            return fallback_msg
        return f"工具 [{tool_name}] 暂时不可用，请稍后重试。错误: {str(e)[:100]}"


# ══════════════════════════════════════════════════════════════
# Layer 3: JSON 解析修复 —— 重试 + 降级
# WHY: LLM 生成的 JSON 偶尔多一个逗号、少一个引号，
#      直接 json.loads 失败。策略：让 LLM 自己修正一次 →
#      还不行就降级，用原始文本代替结构化数据。
# ══════════════════════════════════════════════════════════════

def parse_json_with_repair(llm_response: str, max_attempts: int = 2) -> dict:
    """
    尝试解析 LLM 返回的 JSON，失败则请求 LLM 修正。
    """
    # 尝试1: 直接解析
    try:
        return json.loads(llm_response)
    except json.JSONDecodeError as e:
        print(f"    ⚠ JSON 解析失败 (第1次): {e}")

    if max_attempts <= 1:
        return {"error": "parse_failed", "raw": llm_response[:200]}

    # 尝试2: 让 LLM 修正格式
    print(f"    → 请求 LLM 修正 JSON 格式...")
    fix_prompt = f"""以下 JSON 格式有误，请修正后输出正确的 JSON（只输出 JSON）：

原始内容:
{llm_response}

解析错误: 格式不正确

修正后的 JSON:"""

    try:
        fixed = chat([
            {"role": "system",
             "content": "你是 JSON 修复器。只输出修正后的合法 JSON，无其他文字。"},
            {"role": "user", "content": fix_prompt},
        ], temperature=0)
        return json.loads(fixed)
    except Exception:
        print(f"    🔴 JSON 修正也失败了，降级返回原始文本")
        return {"error": "repair_failed", "raw": llm_response[:200]}


# ══════════════════════════════════════════════════════════════
# Layer 4: 熔断器（Circuit Breaker）
# WHY: 连续失败 N 次后，不再重试（快速失败），给下游恢复时间。
#      避免"明知服务挂了还不断打请求"的雪崩效应。
# ══════════════════════════════════════════════════════════════

class CircuitBreaker:
    """
    简单熔断器：连续失败 threshold 次后进入 OPEN 状态，直接拒绝请求。
    """
    def __init__(self, threshold: int = 3, recovery_seconds: float = 30.0):
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED / OPEN / HALF_OPEN

    def call(self, func: Callable, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_seconds:
                self.state = "HALF_OPEN"
                print(f"    [熔断器] OPEN→HALF_OPEN，尝试恢复...")
            else:
                return f"服务暂时不可用（熔断保护中），请稍后再试。"

        try:
            result = func(*args, **kwargs)
            # 成功 → 重置
            if self.state == "HALF_OPEN":
                print(f"    [熔断器] HALF_OPEN→CLOSED，服务已恢复")
            self.state = "CLOSED"
            self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.threshold:
                self.state = "OPEN"
                print(f"    [熔断器] 连续 {self.failure_count} 次失败 → OPEN")
            raise e


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

def demo_llm_retry():
    """
    演示1：LLM 重试——模拟超时/失败场景。
    """
    print("=" * 60)
    print(" 演示1：LLM 调用重试 + 指数退避")
    print("=" * 60)

    call_count = [0]  # 用列表闭包模拟状态

    @with_llm_retry(max_retries=3, base_delay=0.3)
    def unreliable_llm(prompt: str) -> str:
        call_count[0] += 1
        # WHY: 模拟前 2 次失败、第 3 次成功
        if call_count[0] <= 2:
            raise ConnectionError(f"模拟网络错误 (第{call_count[0]}次)")
        return chat([
            {"role": "system", "content": "用一句话回复"},
            {"role": "user", "content": prompt},
        ])

    print("\n  调用可能失败的 LLM 函数...\n")
    result = unreliable_llm("耳机退货几天内可以申请？")
    print(f"\n  最终结果: {result}")
    print(f"  共调用 {call_count[0]} 次 (失败2次 + 成功1次)")


def demo_safe_tool():
    """
    演示2：工具异常保护。
    """
    print("\n" + "=" * 60)
    print(" 演示2：工具调用异常防护 + 降级")
    print("=" * 60)

    def buggy_query_order(order_id: str) -> str:
        if order_id == "ERROR001":
            raise RuntimeError("数据库连接超时")
        return json.dumps(MOCK_ORDERS.get(order_id, {}), ensure_ascii=False)

    print("\n  正常调用:")
    r1 = safe_tool_call(buggy_query_order, "query_order",
                        fallback_msg="订单系统繁忙，请稍后查询",
                        order_id="ORD20240001")
    print(f"    结果: {r1[:80]}...")

    print("\n  异常调用 (模拟数据库超时):")
    r2 = safe_tool_call(buggy_query_order, "query_order",
                        fallback_msg="订单系统繁忙，请稍后查询",
                        order_id="ERROR001")
    print(f"    结果: {r2}")


def demo_json_repair():
    """
    演示3：JSON 解析修复。
    """
    print("\n" + "=" * 60)
    print(" 演示3：JSON 解析失败 → 自动修复")
    print("=" * 60)

    # 模拟 LLM 返回的"坏 JSON"
    bad_json = """{
  "category": "退货申请",
  "urgency": "high",
  "summary": "用户购买耳机5天后左耳无声，要求退款",
  "action": "核实订单+联系用户确认故障情况"
  "note": "缺少逗号导致解析失败"
}"""  # ← 注意 action 后面少了逗号

    print(f"\n  原始输出 (缺少逗号的 JSON):\n{bad_json[:120]}...")
    print()

    result = parse_json_with_repair(bad_json)
    if "error" not in result:
        print(f"  ✓ 修复成功: category={result.get('category')}, "
              f"urgency={result.get('urgency')}")
    else:
        print(f"  ✗ 修复失败: {result['error']}")


def demo_circuit_breaker():
    """
    演示4：熔断器保护。
    """
    print("\n" + "=" * 60)
    print(" 演示4：熔断器 —— 连续失败 → 自动熔断")
    print("=" * 60)

    cb = CircuitBreaker(threshold=3, recovery_seconds=999)  # recovery 很长便于演示

    fail_count = [0]

    def flaky_service():
        fail_count[0] += 1
        raise ConnectionError(f"服务异常 #{fail_count[0]}")

    print()
    for i in range(5):
        try:
            result = cb.call(flaky_service)
            print(f"  请求{i+1}: {result}")
        except Exception as e:
            print(f"  请求{i+1}: 失败 ({e})")
        print(f"    熔断器状态: {cb.state}, 失败计数: {cb.failure_count}")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 18: 错误处理与重试         ║")
    print("║  重试退避 · 工具防护 · JSON修复 · 熔断器          ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_llm_retry()
    demo_safe_tool()
    demo_json_repair()
    demo_circuit_breaker()

    print("\n" + "=" * 60)
    print(" Demo 18 完成！韧性 = 优雅降级而非崩溃")
    print("=" * 60)


if __name__ == "__main__":
    main()
