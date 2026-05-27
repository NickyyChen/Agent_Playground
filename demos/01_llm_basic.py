# -*- coding: utf-8 -*-
"""
01_llm_basic.py — LLM 调用与参数控制
=====================================

【概念】
大语言模型（LLM）是通过 API 调用的"文本大脑"。每次调用时，我们传入
对话消息列表（messages），模型根据上下文逐 token 生成回复。

【在智能客服中解决什么问题】
客服系统的基础能力：接收到用户消息后，调用 LLM 得到回复文本。
temperature / top_p / max_tokens 三个参数直接控制回复的
"随机性、多样性、长度"，在客服场景中调参直接影响用户体验 ——
确定性回答（如退换货政策）需要低温，创意回答（如营销文案）需要高温。

【核心流程】
1. 构建 messages: [system_prompt（客服人设）, user_msg（用户问题）]
2. 调用 DeepSeek-v4-pro API（兼容 OpenAI SDK）
3. 解析并打印回复文本
4. 对比不同参数组合的效果

【pip install】
pip install openai

【ASCII 架构图】

┌─────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│  messages[]  │───▶│ DeepSeek-v4-pro API │───▶│  回复文本(str)    │
│              │    │                     │    │                  │
│ system: 人设  │    │  ◄temperature──►    │    │ 温度低 → 稳定     │
│ user:   问题  │    │  ◄top_p────────►    │    │ 温度高 → 多样     │
│              │    │  ◄max_tokens───►    │    │ token不够 → 截断  │
└─────────────┘    └─────────────────────┘    └──────────────────┘

    三个核心参数均在 API 请求中传入，由 shared/llm_client.py 统一转发
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm_client import chat


# ─── 客服系统人设 System Prompt ─────────────────────────────────
# WHY: system role 定义了客服的行为边界，是所有智能客服对话的"宪法"
SYSTEM_PROMPT = """
你是"小选"，某电商平台的智能客服助手。

- 回答简洁专业，不超过3句话
- 涉及退换货/退款时，必须引用平台政策
- 对价格、库存等实时信息，诚实说明无法查询
- 态度友好
"""


def demo_basic_call():
    """演示：最基本的 LLM 调用 —— 一问一答"""
    print("=" * 60)
    print(" 演示1：基础客服问答")
    print("=" * 60)

    question = "我买的蓝牙耳机能退货吗？"

    # WHY: messages 列表是 LLM 的唯一输入通道，每条消息的 role 决定了
    #      模型如何理解该条内容 —— system=设定行为, user=用户提问
    reply = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ])

    print(f" 用户: {question}")
    print(f" 客服: {reply}")
    print()


def demo_temperature():
    """
    演示：temperature 参数对回答的影响。
    WHY: temperature（0~2）控制输出的"随机性"——
         - 趋近 0 → 每次回答几乎相同（适合政策查询、订单处理）
         - 趋近 2 → 每次回答可能不同（适合营销文案、话术变体）
    智能客服中，政策类问题用低温（保准确），闲聊类用高温（保亲和）
    """
    print("=" * 60)
    print(" 演示2：temperature 参数对比")
    print("=" * 60)

    question = "推荐一款适合学生党的耳机，说说理由"

    for temp in [0.1, 2]:
        reply = chat(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": question}],
            temperature=temp,
        )
        print(f" temperature={temp}:")
        print(f"   回答: {reply}")
        print(f"   解读: {'稳定确定型' if temp < 0.5 else '随机多样型'}回答")
        print()


def demo_max_tokens():
    """
    演示：max_tokens 参数对回答长度的影响。
    WHY: max_tokens 是生成 token 数的"天花板"，不是"目标值"——
         max_tokens=1000 → 模型最多输出 1000 token，但如果它觉得三句话就够了，
                           它仍然只会输出三句话（天花板没压到它）；
         max_tokens=10  → 天花板极低，模型话没说完就被硬截断。
         所以演示效果的关键是小值要足够小，让截断"肉眼可见"。
         客服场景中，简短确认信息用低 max_tokens 省钱，复杂政策解释需要留足空间。
    """
    print("=" * 60)
    print(" 演示3：max_tokens 参数对比（天花板效应）")
    print("=" * 60)

    question = "详细介绍一下你们平台的退换货政策"

    for max_tok in [10, 1000]:
        reply = chat(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": question}],
            max_tokens=max_tok,
        )
        print(f" max_tokens={max_tok}:")
        print(f"   回答: {reply}")
        print(f"   字数: {len(reply)} 字")
        if max_tok == 10:
            print(f"   说明: 上限极低 → 被硬截断，话没说完")
        else:
            print(f"   说明: 上限充足 → 模型说完想说的就停，不会硬凑到1000")
        print()


def demo_top_p():
    """
    演示：top_p 参数（核采样）控制候选词的多样性。
    WHY: 模型生成每个 token 时，按概率从高到低累加，只保留累计概率 ≤ top_p 的词。
         top_p=0.1 → 只考虑概率最高的那几个词 → 答案保守
         top_p=0.9 → 候选池大 → 措辞更多变
         一般建议 temperature 和 top_p 只调一个，另一个保持默认
    """
    print("=" * 60)
    print(" 演示4：top_p 参数对比")
    print("=" * 60)

    question = "用一句话夸一下我们的耳机产品"

    for top_p_val in [0.1, 0.9]:
        reply = chat(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": question}],
            top_p=top_p_val,
        )
        print(f" top_p={top_p_val}:")
        print(f"   回答: {reply}")
        print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║   Agent-Playground Demo 01: LLM 调用与参数控制   ║")
    print("║   模型: DeepSeek-v4-pro                          ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_basic_call()
    demo_temperature()
    demo_max_tokens()
    demo_top_p()

    print("=" * 60)
    print(" Demo 01 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
