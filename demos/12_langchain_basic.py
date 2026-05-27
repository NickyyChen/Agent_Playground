# -*- coding: utf-8 -*-
"""
12_langchain_basic.py — LangChain 链式调用：PromptTemplate → LLM → Parser
=========================================================================

【概念】
前面 11 个 Demo 都在用 `shared/llm_client.py` 封装的 chat() 函数——
这是我们自己写的简单封装。LangChain 提供了一套标准化的"链式调用"抽象：

  PromptTemplate → ChatModel → OutputParser

每一个环节是一个"可运行单元（Runnable）"，用 `|`（管道符）串起来，
数据从左流到右，像 Unix 管道一样直观。这就是 LCEL（LangChain Expression Language）。

【在智能客服中解决什么问题】
客服系统需要稳定、结构化的输出——LangChain 的链式抽象能保证：
- Prompt 模板化（避免每次手写拼字符串）
- 输出格式化（保证 LLM 返回可解析的 JSON，而不是自由文本）
- 步骤可复用（同一个 prompt 模板可以用于不同场景）

【核心流程】
1. PromptTemplate：定义带 {变量} 的模板
2. ChatOpenAI：LLM 调用（配置指向 DeepSeek）
3. OutputParser：解析输出（纯文本 or JSON）
4. LCEL `|`：把它们串成一条流水线

【pip install】
pip install langchain langchain-core langchain-openai

【ASCII 架构图】

  ┌────────────────────────────────────────────────────────────┐
  │                  LangChain 链式调用                         │
  │                                                            │
  │   ┌──────────────┐      ┌──────────┐      ┌─────────────┐ │
  │   │ PromptTemplate│  →  │ ChatModel │  →  │ OutputParser│ │
  │   │              │      │          │      │             │ │
  │   │ "你是{role}"  │      │ DeepSeek │      │ StrOutput   │ │
  │   │ "用户说{msg}" │      │          │      │ JsonOutput  │ │
  │   └──────────────┘      └──────────┘      └─────────────┘ │
  │                                                            │
  │   LCEL 写法:                                                │
  │   chain = prompt | model | parser                          │
  │   result = chain.invoke({"role": "客服", "msg": "..."})     │
  │                                                            │
  │   对比 shared/llm_client.py:                                 │
  │   reply = chat([{"role":"system",...}, {"role":"user",...}])│
  │   → 手工拼接 messages，无模板、无自动解析                       │
  └────────────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from shared.config import LLM_CONFIG


# ─── LLM 实例（指向 DeepSeek-v4-pro）──────────────────────────
# WHY: ChatOpenAI 是 LangChain 的标准 LLM 接口，
#      通过 openai_api_base 指向 DeepSeek 的兼容端点，
#      后续所有 Chain 共用这一个实例
llm = ChatOpenAI(
    model=LLM_CONFIG["model"],
    openai_api_key=LLM_CONFIG["api_key"],
    openai_api_base=LLM_CONFIG["base_url"],
    temperature=0.1,
)


# ══════════════════════════════════════════════════════════════
# 演示1：最简单的 Chain —— Prompt → LLM → 纯文本输出
# ══════════════════════════════════════════════════════════════

def demo_simple_chain():
    """
    演示1：LangChain 最基础的链式调用。
    WHY: PromptTemplate 把"模板结构"和"具体数据"分离——
         {role} 和 {user_input} 是占位符，invoke() 时才填入。
         对比手工 f-string 拼接：模板可以复用、可以序列化、
         可以版本管理，而且 LCEL 管道写法一行搞定。
    """
    print("=" * 60)
    print(" 演示1：PromptTemplate → LLM → StrOutputParser")
    print("=" * 60)

    # WHY: ChatPromptTemplate.from_messages 定义对话模板，
    #      ("system", ...) 是 system role，("user", ...) 是 user role，
    #      变量用 {var_name} 占位
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是{role}，回答简洁专业，不超过3句话。"),
        ("user", "{user_input}"),
    ])

    # WHY: LCEL 管道 `|` —— 从左到右，数据依次流经每个组件
    #      prompt | llm → 生成 ChatMessage
    #      ChatMessage | StrOutputParser → 提取纯文本 content
    chain = prompt | llm | StrOutputParser()

    # WHY: invoke() 传入 dict，key 对应模板中的 {变量名}
    result = chain.invoke({
        "role": "好买电商售后客服小选",
        "user_input": "我的蓝牙耳机能退货吗？已经用了3天了",
    })

    print(f"  输入: role=售后客服, user_input=蓝牙耳机退货")
    print(f"  输出: {result}")
    print()

    # ─── 证明模板可复用：换一个 role 和 user_input ─────
    result2 = chain.invoke({
        "role": "好买电商售前导购小选",
        "user_input": "推荐一款300以内的耳机给我",
    })
    print(f"  复用同一模板，换 role 和输入:")
    print(f"  输出: {result2}")
    print()


# ══════════════════════════════════════════════════════════════
# 演示2：LCEL 多步骤管道 —— 串联多个处理步骤
# ══════════════════════════════════════════════════════════════

def demo_lcel_pipeline():
    """
    演示2：LCEL 管道串联多个步骤。
    WHY: LCEL 的真正威力在于可以串联多个 Runnable——
         生成回答 → 提取摘要 → 翻译 → ... 每一步都可以复用。
         这里展示：关键词提取 → 意图分类，两条独立管道。
    """
    print("=" * 60)
    print(" 演示2：LCEL 多步骤管道")
    print("=" * 60)

    # ─── 管道A: 关键词提取 ──────────────────────────
    keyword_prompt = ChatPromptTemplate.from_messages([
        ("system", "从用户输入中提取 3-5 个关键词，用逗号分隔，只输出关键词。"),
        ("user", "{user_input}"),
    ])
    keyword_chain = keyword_prompt | llm | StrOutputParser()

    # ─── 管道B: 意图分类 ────────────────────────────
    intent_prompt = ChatPromptTemplate.from_messages([
        ("system",
         "分析用户意图，输出以下类别之一: "
         "售前咨询、售后服务、投诉、闲聊。只输出类别名。"),
        ("user", "{user_input}"),
    ])
    intent_chain = intent_prompt | llm | StrOutputParser()

    # WHY: 两条管道独立定义、独立调用，各自处理同一输入的不同维度
    test_inputs = [
        "我想买个降噪耳机，能推荐一下吗？",
        "我买的耳机左边没声音了，怎么退货？",
        "你们客服态度太差了，我要投诉！",
    ]

    for user_input in test_inputs:
        keywords = keyword_chain.invoke({"user_input": user_input})
        intent = intent_chain.invoke({"user_input": user_input})
        print(f"  用户: {user_input}")
        print(f"    关键词: {keywords}")
        print(f"    意图: {intent}")
        print()


# ══════════════════════════════════════════════════════════════
# 演示3：JsonOutputParser —— 从 LLM 回复中提取结构化 JSON
# ══════════════════════════════════════════════════════════════

# WHY: Pydantic 模型定义了期望的输出结构——
#      JsonOutputParser 根据这个结构自动生成 format_instructions，
#      告诉 LLM "请按这个 JSON Schema 输出"，然后解析返回的 JSON。
#      这比手工 json.loads(reply) 可靠得多——parser 会重试、会纠错。
class ServiceTicket(BaseModel):
    category: str = Field(description="问题分类: 售前咨询/售后服务/投诉/其他")
    urgency: str = Field(description="紧急程度: low/medium/high")
    summary: str = Field(description="30字以内的问题摘要")
    needs_human: bool = Field(description="是否需要转人工处理")


def demo_json_parser():
    """
    演示3：JsonOutputParser —— 结构化输出。
    WHY: 客服工单必须结构化才能入库、统计、路由。
         手工让 LLM "输出 JSON" 不可靠——可能多输出解释文字、
         可能字段嵌套错误。JsonOutputParser 自动：
         ① 生成 format_instructions 注入 prompt
         ② 解析 LLM 返回的 JSON
         ③ 校验字段是否符合 Pydantic 模型
         生产环境中这一步决定了"LLM 输出"能否直接入库。
    """
    print("=" * 60)
    print(" 演示3：JsonOutputParser —— 结构化工单输出")
    print("=" * 60)

    parser = JsonOutputParser(pydantic_object=ServiceTicket)

    # WHY: parser.get_format_instructions() 自动生成 JSON Schema 指令，
    #      不用手写 "请输出以下JSON格式..." —— 格式与代码绑定，改了字段自动更新
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "你是客服工单系统。根据对话内容生成工单摘要。\n"
         "{format_instructions}"),
        ("user", "客服对话:\n{dialogue}"),
    ]).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    # WHY: 三个场景覆盖了不同的分类、紧急程度和人工处理判断
    test_cases = [
        ("场景1: 正常咨询",
         "用户: 请问蓝牙耳机一般能用几年？\n客服: 一般2-3年..."),
        ("场景2: 质量投诉",
         "用户: 我的耳机用了3天左耳就没声音了！你们卖假货吧？"
         "马上给我退款不然我去消协投诉！"),
        ("场景3: 多轮对话",
         "用户: 我的订单怎么还没发货？\n客服: 请问订单号是？\n"
         "用户: ORD20240001\n客服: 查到您的订单预计明天发货"),
    ]

    for label, dialogue in test_cases:
        print(f"  {label}")
        try:
            result = chain.invoke({"dialogue": dialogue})
            print(f"    分类: {result['category']}")
            print(f"    紧急度: {result['urgency']}")
            print(f"    摘要: {result['summary']}")
            print(f"    需人工: {result['needs_human']}")
        except Exception as e:
            print(f"    解析失败: {e}")
        print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 12: LangChain 链式调用      ║")
    print("║  PromptTemplate → LLM → OutputParser              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_simple_chain()
    demo_lcel_pipeline()
    demo_json_parser()

    print("=" * 60)
    print(" Demo 12 完成！Chain = 把 LLM 调用变成流水线")
    print("=" * 60)


if __name__ == "__main__":
    main()
