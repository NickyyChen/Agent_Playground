# -*- coding: utf-8 -*-
"""
03_tool_calling.py — Function Calling：让 LLM 学会"动手"
========================================================

【概念】
普通的 LLM 调用只能"说"——输入文本，输出文本。
Function Calling（工具调用）让 LLM 能"动手"——当它判断自己不知道答案时，
会返回一个"函数调用请求"，由外部代码执行函数，把结果再喂给 LLM 生成最终回答。

这是 Agent 的核心能力：**LLM 作为大脑做决策，外部工具作为手脚执行操作**。

【在智能客服中解决什么问题】
智能客服不能全靠"背课文"——它需要实时查询订单、物流这些外部数据。
这些数据不在模型的训练集里，必须通过工具调用实时获取。
Function Calling 就是 LLM 和外部系统的"插头"。

【核心流程】
1. 构建 tools 定义列表（JSON Schema 描述每个工具的参数和用途）
2. 把 tools 和用户消息一起发给 LLM
3. LLM 返回 tool_calls（想调哪个函数、传什么参数）
4. 我们执行函数，把结果以 tool role 消息追加到对话
5. LLM 阅读结果，生成最终的自然语言回答

【pip install】
pip install openai

【ASCII 架构图】

                         ┌─────────────┐
  用户说 "查订单XXX"  ──▶│   LLM 大脑   │
                         │             │
                         │ 判断: 我不知道 │
                         │ 订单数据 → 需要 │
                         │ 调用外部函数!  │
                         └──────┬──────┘
                                │
                   返回 tool_call 请求
                 {"name":"query_order","arguments":{"order_id":"XXX"}}
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │ query_order  │    │query_logistics│   │check_policy  │
   │ 查订单状态    │    │ 查物流轨迹    │    │ 查退换货政策  │
   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                    返回工具执行结果
                              │
                              ▼
                         ┌─────────────┐
                         │   LLM 大脑   │
                         │ 阅读结果,     │
                         │ 组织自然语言   │
                         │ 回答用户      │
                         └─────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
from shared.llm_client import create_completion
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


SYSTEM_PROMPT = """你是"小选"，好买电商平台的智能客服。
你可以通过工具查询用户的订单状态、物流轨迹和退换货政策。
当需要查询具体数据时，务必调用工具获取最新信息，不要凭空编造。"""


# ══════════════════════════════════════════════════════════════
# 工具函数：LLM 可调用的"手脚"
# ══════════════════════════════════════════════════════════════

def query_order(order_id: str) -> str:
    """根据订单号查询订单状态"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在，请核实订单号"
    return json.dumps(order, ensure_ascii=False, indent=2)


def query_logistics(tracking_no: str) -> str:
    """根据快递单号查询物流轨迹"""
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递单号 {tracking_no} 暂无记录"
    return json.dumps(info, ensure_ascii=False, indent=2)


def check_return_policy(category: str = "") -> str:
    """查询退换货政策，可选按品类筛选"""
    if category:
        return f"关于'{category}'品类：\n{RETURN_POLICY}"
    return RETURN_POLICY


# WHY: 工具注册表 —— 把函数名字符串映射到实际 Python 函数，
#      这样 LLM 返回的 tool_call.name 可以直接查到对应函数并执行
TOOL_FUNCTIONS = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "check_return_policy": check_return_policy,
}


# ══════════════════════════════════════════════════════════════
# 工具定义（JSON Schema）：告诉 LLM 有哪些工具可用
# WHY: tools 是一份 JSON Schema 列表，定义了每个工具的"签名"——
#      name → 工具名, description → 什么时候该用,
#      parameters → 需要什么参数、参数类型和含义
#      LLM 根据这份描述判断何时该调哪个工具、传什么参数。
# ══════════════════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单的当前状态、商品信息、金额、下单时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号，格式如 ORD20240001"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "根据快递单号查询物流轨迹、当前位置和预计送达时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_no": {
                        "type": "string",
                        "description": "快递单号，如 SF1234567890"
                    }
                },
                "required": ["tracking_no"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "查询退换货政策，可选传入品类名称做筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "商品品类，如'耳机'、'手机壳'"
                    }
                },
                "required": []
            }
        }
    },
]


# ══════════════════════════════════════════════════════════════
# 核心循环：一次完整的 "判断→调工具→回传结果→回答"
# WHY: 这个循环是 Agent 的最小工作单元。每一步都打印中间状态，
#      帮助理解 LLM 的决策过程。
# ══════════════════════════════════════════════════════════════

def run_tool_call_round(user_question: str):
    """
    发送用户问题 → 收到 tool_call → 执行工具 → 回传结果 → 得到最终回答。
    每一步都打印出来，让 Function Calling 的完整链路可视化。
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]

    # Step 1: 第一次请求，告诉 LLM 有哪些工具可用
    print(f"  [Step 1] 发送用户问题 + 工具列表 → LLM")
    response = create_completion(messages, tools=TOOLS, temperature=0.1)
    msg = response.choices[0].message

    # Step 2: 检查 LLM 是否想调用工具
    if not msg.tool_calls:
        # LLM 觉得不需要工具，直接文本回复
        print(f"  [结果] LLM 未调用工具，直接回答: {msg.content}")
        return

    print(f"  [Step 2] LLM 决定调用 {len(msg.tool_calls)} 个工具:")
    for tc in msg.tool_calls:
        print(f"           → {tc.function.name}({tc.function.arguments})")

    # Step 3: 将 LLM 的 tool_call 请求追加到消息历史
    messages.append(msg)

    # Step 4: 执行每个工具，把结果以 tool role 追加
    for tc in msg.tool_calls:
        func_name = tc.function.name
        # WHY: json.loads 把 LLM 返回的 JSON 参数字符串解析为 Python dict
        args = json.loads(tc.function.arguments)
        fn = TOOL_FUNCTIONS.get(func_name)

        if fn:
            # WHY: **args 把 {"order_id":"ORD001"} 变成 order_id="ORD001" 传参
            result = fn(**args)
            print(f"  [Step 3] 执行 {func_name}({args}) →")
            print(f"           {result[:100]}...")
        else:
            result = f"错误：工具 {func_name} 不存在"

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    # Step 5: 把工具结果回传给 LLM，生成最终自然语言回答
    print(f"  [Step 4] 工具结果回传 LLM，生成最终回答 →")
    response2 = create_completion(messages, temperature=0.1)
    final_reply = response2.choices[0].message.content
    print(f"           「{final_reply}」")
    print()


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_single_tool():
    """
    演示1：单一工具调用 —— 查订单。
    WHY: 用户问订单状态，LLM 知道自己不知道 → 主动调用 query_order
         → 拿到数据后组织成自然语言回复。
         这是 Function Calling 最基础的"一问一查一答"模式。
    """
    print("=" * 60)
    print(" 演示1：单一工具调用 —— 查订单")
    print("=" * 60)
    run_tool_call_round("帮我查一下订单 ORD20240001 的状态")


def demo_multi_tool_routing():
    """
    演示2：多工具路由 —— LLM 根据意图自动选工具。
    WHY: 三个工具同时可用，LLM 根据用户问题的语义判断该调哪个：
         "订单" → query_order
         "快递/物流" → query_logistics
         "退换货/政策" → check_return_policy
         这证明 Function Calling 不是关键词匹配，而是语义理解。
    """
    print("=" * 60)
    print(" 演示2：多工具路由 —— 不同意图触发不同工具")
    print("=" * 60)

    test_cases = [
        "我的快递 YT9876543210 到哪了？",
        "蓝牙耳机能退货吗？",
        "订单 ORD20240002 的发货了没有？",
    ]

    for question in test_cases:
        print(f" 用户: {question}")
        run_tool_call_round(question)


def demo_unknown_intent():
    """
    演示3：LLM 判断不需要调工具的边界情况。
    WHY: 不是所有问题都需要工具——当用户闲聊或问常识性问题时，
         LLM 应该用自己的知识直接回答，而不是强行调工具。
         这展示了 Function Calling 的"克制"：不该调时别乱调。
    """
    print("=" * 60)
    print(" 演示3：边界判断 —— 什么时候不需要调工具")
    print("=" * 60)

    test_cases = [
        "你好，在吗？",
        "蓝牙耳机一般能用几年？",
    ]

    for question in test_cases:
        print(f" 用户: {question}")
        run_tool_call_round(question)


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 03: Function Calling       ║")
    print("║  LLM 判断→调工具→拿结果→回答                       ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_single_tool()
    demo_multi_tool_routing()
    demo_unknown_intent()

    print("=" * 60)
    print(" Demo 03 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
