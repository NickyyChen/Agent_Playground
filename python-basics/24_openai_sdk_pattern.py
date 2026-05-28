# -*- coding: utf-8 -*-
"""
24_openai_sdk_pattern.py — OpenAI SDK 调用范式
==============================================

【概念】
OpenAI SDK 是调用 LLM API 的标准方式——虽然你用的是 DeepSeek 等模型，
但它们的 API 兼容 OpenAI 的接口规范。

核心调用链：
  OpenAI(api_key, base_url)  → 客户端实例
  client.chat.completions.create(**params) → 发起请求
  response.choices[0].message.content → 提取回复文本
  response.choices[0].message.tool_calls → 提取工具调用

Chat Completions API 是最常用的接口——一次 HTTP 请求返回 LLM 回复。
Streaming Completions 是流式版本——逐 token 返回，适合打字机效果。

【在智能客服中的应用】
- 所有 demo 都通过 shared/llm_client.py 调用 LLM
- Function Calling：tools 参数定义可用工具，tool_calls 获取调用意图
- Streaming：客服消息逐字显示，提升用户体验

【pip install】
pip install openai

【ASCII 架构图】

  client.chat.completions.create(
      model="deepseek-v4-pro",
      messages=[                            ← 对话历史
          {"role":"system","content":"你是客服"},
          {"role":"user","content":"查订单"}
      ],
      temperature=0.1,                      ← 可选参数
      max_tokens=200,
      tools=[{...}]                         ← 可选：工具定义
  )
       │
       ▼
  response.choices[0].message
       │
       ├── .content      → "好的，正在查询..."  (纯文本回复)
       └── .tool_calls   → [{function:...}]      (工具调用意图)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.llm_client import chat, create_completion
from shared.config import LLM_CONFIG


# ══════════════════════════════════════════════════════════════
# 1. 基本调用 —— 一问一答
# WHY: chat() 封装了 OpenAI SDK 的完整调用流程——
#      构建 messages → 调用 API → 提取 content → 返回 str。
#      这就是所有 LLM 应用的最基础单元。
# ══════════════════════════════════════════════════════════════

def demo_basic_call():
    print("=" * 50)
    print(" 1. 基本 LLM 调用 —— 一问一答")
    print("=" * 50)

    print(f" 模型: {LLM_CONFIG['model']}")

    reply = chat([
        {"role": "system",
         "content": "你是小选，电商客服。回答不超过2句话。"},
        {"role": "user",
         "content": "我买的蓝牙耳机能退货吗？"},
    ], temperature=0.1)

    print(f" 客服: {reply}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. Function Calling —— 工具调用
# WHY: tools 参数让 LLM 知道有哪些工具可用——
#      LLM 有需要时返回 tool_calls 而非纯文本，
#      开发者解析 tool_calls 后执行对应函数，再把结果返回给 LLM。
# ══════════════════════════════════════════════════════════════

def demo_function_calling():
    print("=" * 50)
    print(" 2. Function Calling —— 工具调用")
    print("=" * 50)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_order_status",
                "description": "根据订单号查询订单状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "订单号，如 ORD001"
                        }
                    },
                    "required": ["order_id"]
                }
            }
        }
    ]

    response = create_completion(
        [{"role": "user", "content": "帮我查一下订单 ORD001 的状态"}],
        tools=tools,
        temperature=0.1,
    )

    msg = response.choices[0].message

    # WHY: tool_calls 为 None → LLM 不需要调工具，直接返回文本
    if msg.tool_calls:
        tc = msg.tool_calls[0]
        print(f" LLM 想调工具: {tc.function.name}")
        import json
        args = json.loads(tc.function.arguments)
        print(f" 参数: {args}")
    elif msg.content:
        print(f" LLM 直接回复: {msg.content}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 参数说明 —— temperature / max_tokens / top_p
# WHY: 三个核心参数直接控制回复的风格和质量——
#      客服系统不同场景需要不同参数组合。
# ══════════════════════════════════════════════════════════════

def demo_parameters():
    print("=" * 50)
    print(" 3. 核心参数说明")
    print("=" * 50)

    print("""
  temperature (0~2):
    0.0 → 每次回答几乎相同（政策查询、订单确认）
    1.0 → 有一定变化（日常对话）
    2.0 → 最大随机性（营销文案创意）

  max_tokens (上限):
    50  → 简短确认（"好的"、"没问题"）
    200 → 标准回答（介绍退换货政策）
    1000→ 长回复（详细使用教程）

  top_p (0~1):
    0.1 → 只选概率最高的词 → 保守
    0.9 → 候选词多 → 多样

  建议: temperature 和 top_p 只调一个，另一个保持默认
  """)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 24: OpenAI SDK 调用范式          ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_basic_call()
    demo_function_calling()
    demo_parameters()


if __name__ == "__main__":
    main()
