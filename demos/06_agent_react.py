# -*- coding: utf-8 -*-
"""
06_agent_react.py — ReAct Agent：思考→行动→观察 循环
====================================================

【概念】
ReAct = Reasoning（推理）+ Acting（行动），是 Agent 的核心工作模式。
它不是"一轮工具调用就结束"，而是自主循环：

  思考(Thought) → 行动(Action/调工具) → 观察(Observation/看结果)
       ↑                                              │
       └──────────────────────────────────────────────┘
           如果信息还不够 → 继续思考 → 再行动 → 再观察
           如果信息足够了 → 输出 Final Answer

类比：Demo 03 的 Function Calling 是"一问一答"，
      ReAct Agent 则是"自主多步推理"——像人类解决问题那样
      "先做A，看结果，再决定做B还是C，直到解决问题"。

【在智能客服中解决什么问题】
真实客服问题通常需要多步操作：
- "我的耳机坏了能退钱吗？" → 需要先查订单状态 → 再查是否在保修期
  → 再按政策计算应退金额 → 这是一个链式推理过程
- 用户可能有多个问题、模糊描述，Agent 需要自主规划步骤去探索

【核心流程】
1. LLM 收到用户问题 + 可用工具列表
2. LLM 输出 Thought（分析现状）+ Action（调用哪个工具、传什么参数）
3. 外部执行工具，返回 Observation
4. 把 Thought/Action/Observation 追加到对话历史
5. LLM 重新审视：信息够了吗？
   - 不够 → 回到步骤 2
   - 够了 → 输出 Final Answer

【pip install】
pip install openai

【ASCII 架构图】

 用户: "我的耳机坏了能退吗？"
        │
        ▼
  ┌─────────────────────────────────────────────────────┐
  │                  ReAct Agent 循环                     │
  │                                                      │
  │  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
  │  │ Thought  │───▶│  Action  │───▶│ Observation  │   │
  │  │          │    │          │    │              │   │
  │  │ "先查订单"│    │query_order│   │ "订单ORD001, │   │
  │  │          │    │(ORD001)  │    │  已签收5天"   │   │
  │  └──────────┘    └──────────┘    └──────┬───────┘   │
  │                                         │           │
  │     ┌───────────────────────────────────┘           │
  │     ▼                                               │
  │  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
  │  │ Thought  │───▶│  Action  │───▶│ Observation  │   │
  │  │          │    │          │    │              │   │
  │  │ "5天在7天  │   │check_    │    │ "7天内可退货,│   │
  │  │ 内，查政策"│   │policy()  │    │  拆封不支持"  │   │
  │  └──────────┘    └──────────┘    └──────┬───────┘   │
  │                                         │           │
  │     ┌───────────────────────────────────┘           │
  │     ▼                                               │
  │  ┌──────────────────────────┐                       │
  │  │      Final Answer        │                       │
  │  │  "您的订单签收5天，仍在   │                       │
  │  │   7天退货期内，但耳机属   │                       │
  │  │   特殊商品拆封后不支持..." │                       │
  │  └──────────────────────────┘                       │
  └─────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
from shared.llm_client import create_completion
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 工具集：Agent 的"手脚"
# ══════════════════════════════════════════════════════════════

def query_order(order_id: str) -> str:
    """查询订单详情"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    return json.dumps(order, ensure_ascii=False, indent=2)


def query_logistics(tracking_no: str) -> str:
    """查询物流轨迹"""
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递 {tracking_no} 暂无物流记录"
    return json.dumps(info, ensure_ascii=False, indent=2)


def check_return_policy(category: str = "") -> str:
    """查询退换货政策"""
    if category:
        return f"关于'{category}'：{RETURN_POLICY}"
    return RETURN_POLICY


def calculate_refund(order_id: str) -> str:
    """
    计算应退款金额。
    WHY: 这是典型的"依赖型工具"——必须先调到 query_order 拿到订单金额
         才能计算退款。ReAct Agent 能自主完成这个"先A后B"的链式调用。
    """
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    price = order["price"]
    return json.dumps({
        "order_id": order_id,
        "product": order["product"],
        "paid_amount": price,
        "refund_amount": price,
        "refund_method": "原路退回",
        "estimated_days": "3个工作日",
    }, ensure_ascii=False, indent=2)


TOOL_FUNCTIONS = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "check_return_policy": check_return_policy,
    "calculate_refund": calculate_refund,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单状态、商品、金额、下单时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string",
                                 "description": "订单号，如 ORD20240001"}
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "根据快递单号查询物流轨迹和当前位置",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_no": {"type": "string",
                                    "description": "快递单号"}
                },
                "required": ["tracking_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "查询退换货政策，可选按品类筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "品类名"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_refund",
            "description": "根据订单ID计算应退款金额和退款方式",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"}
                },
                "required": ["order_id"]
            }
        }
    },
]


# ══════════════════════════════════════════════════════════════
# ReAct 循环引擎
# WHY: 这是整个 demo 的核心——一个 while 循环实现了 Agent 的
#      "思考→行动→观察→再思考..." 的自主推理过程。
#      max_rounds 是安全阀，防止模型陷入无限循环。
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是"小选"，好买电商平台的智能客服，具备多步推理能力。

你需要使用工具来回答用户问题。请遵循以下 ReAct 工作模式：

1. 分析用户问题，思考需要什么信息
2. 调用合适的工具获取数据
3. 观察工具返回的结果
4. 如果信息还不够，继续调用下一个工具
5. 当信息充足时，用自然语言给出最终回答

注意：
- 每次只调用一个工具（不要并行调用多个）
- 如果工具返回的信息不足以回答问题，必须继续调用下一个工具
- 不要凭空编造数据，所有结论必须基于工具返回的结果"""


def react_loop(user_question: str, verbose: bool = True):
    """
    ReAct 代理的核心循环。
    返回值: 最终回答文本

    verbose=True 时打印每一步的 Thought/Action/Observation，
    让 ReAct 的内部推理过程完全可视化。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]

    # WHY: max_rounds=5 —— 实践中大多数客服问题 2-3 轮即可解决，
    #      5轮是安全上限，超过说明任务太复杂或模型陷入死循环
    for round_num in range(1, 6):
        if verbose:
            print(f"  ┌─ 第 {round_num} 轮 ─────────────────────┐")

        response = create_completion(messages, tools=TOOLS, temperature=0.1)
        msg = response.choices[0].message

        # WHY: 没有 tool_calls → LLM 认为信息够了，输出最终回答
        if not msg.tool_calls:
            if verbose:
                print(f"  │ 最终回答（无需更多工具）              │")
                print(f"  └──────────────────────────────────────┘")
                print(f"  客服: {msg.content}")
                print()
            return msg.content

        # WHY: msg 包含本轮所有 tool_calls，必须先追加一次 msg，
        #      再逐个追加每个 tool_call 的 tool 结果消息。
        #      API 要求: assistant(tool_calls) 后必须紧跟对应的 tool 消息
        messages.append(msg)

        for tc in msg.tool_calls:
            func_name = tc.function.name
            args = json.loads(tc.function.arguments)
            fn = TOOL_FUNCTIONS.get(func_name)

            if verbose:
                print(f"  │ 调用: {func_name}({args})")

            result = fn(**args) if fn else f"工具 {func_name} 不存在"

            if verbose:
                short = result[:120].replace("\n", " ")
                print(f"  │ 返回: {short}...")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        if verbose:
            print(f"  └──────────────────────────────────────┘")

    # 超过最大轮次，强制结束
    final = create_completion(messages, temperature=0.1)
    final_reply = final.choices[0].message.content
    if verbose:
        print(f"  ⚠ 达到最大轮次，强制生成回答")
        print(f"  客服: {final_reply}")
        print()
    return final_reply or "抱歉，处理超时，请重试。"


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_react_basic():
    """
    演示1：ReAct 多步推理 —— 一个需要 2 步工具调用的客服问题。
    WHY: 用户问"能退多少钱"，Agent 必须：
         Step 1: 先查订单拿到交易金额
         Step 2: 再看退换货政策确认能不能退
         这是一个典型的"链式工具调用"，ReAct 自主串联了这两步。
    """
    print("=" * 60)
    print(" 演示1：ReAct 多步推理 —— 链式工具调用")
    print("=" * 60)

    question = "我的订单 ORD20240001 能退款吗？能退多少钱？"
    print(f" 用户: {question}")
    print()
    react_loop(question)


def demo_react_vs_single():
    """
    演示2：为什么需要多步 —— 比较单轮 Function Calling 的局限。
    WHY: 如果用户问题只含订单号但没有明确说要"退款"，
         单轮调用可能只查订单就结束了，不会主动继续计算退款。
         ReAct 会自主判断还需要什么信息。
    """
    print("=" * 60)
    print(" 演示2：复杂查询 —— ReAct 自主决策")
    print("=" * 60)

    question = ("订单 ORD20240001 里的耳机出问题了，"
                "帮我看看能不能处理，顺便查一下退货政策和快递信息")
    print(f" 用户: {question}")
    print(f" （这个请求涉及订单+政策+物流，Agent 需自主判断调哪些工具）")
    print()
    react_loop(question)


def demo_react_edge_case():
    """
    演示3：边界情况 —— Agent 遇到"查不到"时的处理。
    WHY: 真实场景中工具可能返回"查无此单"，
         Agent 不能就此卡住，而应该引导用户提供正确信息。
         这展示了 ReAct 的容错能力。
    """
    print("=" * 60)
    print(" 演示3：边界处理 —— 查不到时引导用户")
    print("=" * 60)

    question = "帮我查一下订单 ABC99999 的状态"
    print(f" 用户: {question}")
    print()
    react_loop(question)


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 06: ReAct Agent           ║")
    print("║  Thought → Action → Observation → ... → Answer    ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_react_basic()
    demo_react_vs_single()
    demo_react_edge_case()

    print("=" * 60)
    print(" Demo 06 完成！ReAct 是 Agent 的'思考引擎'")
    print("=" * 60)


if __name__ == "__main__":
    main()
