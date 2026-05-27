# -*- coding: utf-8 -*-
"""
10_multi_agent.py — 多 Agent 协作：分工、路由与接力
====================================================

【概念】
前面的 Demo 都是一个 Agent 包办所有事。但在真实客服系统中，售前咨询
（商品推荐、参数对比）和售后服务（订单、退货、投诉）需要的知识和工具
完全不同——让一个 Agent 同时掌握所有技能会导致 prompt 过长、判断混乱。

多 Agent 协作的思路：每个 Agent 只精通一个领域，通过**路由分发**、
**接力传递**、**并行汇总**三种模式协同完成用户请求。

【在智能客服中解决什么问题】
- 售前问题（推荐耳机）→ 售前 Agent（懂产品、懂参数、懂促销）
- 售后问题（退货退款）→ 售后 Agent（懂订单、懂政策、懂流程）
- 复合问题（推荐+查订单）→ 路由拆解 → 并行分发给两个 Agent → 汇总

【核心流程】
1. Router Agent 分析用户意图，决定调动哪个/哪些 Specialist Agent
2. Specialist Agent 执行自己的领域任务
3. 如果执行中发现需要其他 Agent 介入 → Handoff（接力）
4. 如果多 Agent 并行 → Merger 汇总结果

【pip install】
pip install openai

【ASCII 架构图】

                         ┌─────────────────┐
      用户: "推荐耳机      │  Router Agent   │ 分析意图
        + 查我的订单"      │  (调度中心)      │
                         └───┬───────┬─────┘
                             │       │
              ┌──────────────┘       └──────────────┐
              │ 路由到售前              路由到售后    │
              ▼                                     ▼
     ┌────────────────┐                  ┌────────────────┐
     │ 售前 Agent      │                  │ 售后 Agent      │
     │                 │                  │                 │
     │ 懂: 产品参数     │                  │ 懂: 订单/物流    │
     │     促销活动     │                  │     退换货政策   │
     │     选购建议     │                  │     退款流程     │
     │                 │                  │                 │
     │ 工具:            │                  │ 工具:            │
     │ product_search  │                  │ query_order     │
     │ check_promotion │                  │ query_logistics │
     │                 │                  │ check_policy    │
     └────────┬───────┘                  └────────┬────────┘
              │                                   │
              └─────────────┬─────────────────────┘
                            │
                            ▼
                   ┌────────────────┐
                   │  Merger 汇总    │
                   │  综合回答        │
                   └────────────────┘

  【三种协作模式】

  Mode 1 - 路由分发:         Mode 2 - 接力传递:       Mode 3 - 并行汇总:
  ┌──────┐                 ┌──────┐                ┌──────┐
  │Router│──▶ 单个Agent     │ Agent│──▶ 换个Agent    │Router│──▶ Agent A ┐
  └──────┘                 └──────┘                └──────┘   Agent B ├─▶ Merge
                                                                       Agent C ┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import json
from shared.llm_client import chat, create_completion
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# Agent 定义 —— 每个 Agent = system_prompt + 专属工具
# WHY: 每个 Agent 的 system prompt 描述自己的专业领域和能力边界，
#      tools 只包含该领域需要的函数——
#      售前不需要查订单，售后不需要做推荐，各司其职
# ══════════════════════════════════════════════════════════════

# ─── 通用工具 ────────────────────────────────────────

def query_order(order_id: str) -> str:
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return f"订单 {order_id} 不存在"
    return json.dumps(order, ensure_ascii=False, indent=2)


def query_logistics(tracking_no: str) -> str:
    info = MOCK_LOGISTICS.get(tracking_no)
    if not info:
        return f"快递 {tracking_no} 暂无记录"
    return json.dumps(info, ensure_ascii=False, indent=2)


def check_return_policy(category: str = "") -> str:
    if category:
        return f"'{category}'：{RETURN_POLICY}"
    return RETURN_POLICY


def product_search(keyword: str = "") -> str:
    """售前专用：搜索商品信息"""
    products = {
        "降噪耳机": [
            {"name": "漫步者 W820NB", "price": 299, "type": "头戴式",
             "anc": "-43dB", "battery": "50h", "waterproof": "IPX4",
             "适合": "学生党、通勤、预算有限"},
            {"name": "Sony WH-1000XM5", "price": 2299, "type": "头戴式",
             "anc": "AI自适应", "battery": "30h", "waterproof": "无",
             "适合": "商务人士、发烧友"},
            {"name": "小米 Buds 4 Pro", "price": 899, "type": "入耳式",
             "anc": "-48dB", "battery": "38h(含充电盒)", "waterproof": "IP54",
             "适合": "运动、通勤、安卓用户"},
            {"name": "QCY T13", "price": 79, "type": "入耳式",
             "anc": "无(物理隔音)", "battery": "40h(含充电盒)", "waterproof": "IPX5",
             "适合": "学生党、极致性价比"},
        ]
    }
    result = products.get(keyword, [])
    if not result:
        return f"未找到'{keyword}'相关商品"
    return json.dumps(result, ensure_ascii=False, indent=2)


def check_promotions() -> str:
    """售前专用：查询当前促销活动"""
    return json.dumps([
        {"name": "618耳机节", "desc": "全场耳机满200减30，满500减80",
         "expire": "2026-06-20"},
        {"name": "学生专享", "desc": "学生认证后额外9.5折，可叠加满减",
         "expire": "2026-12-31"},
        {"name": "以旧换新", "desc": "旧耳机最高抵300元，不限品牌",
         "expire": "2026-07-31"},
    ], ensure_ascii=False, indent=2)


TOOL_REGISTRY = {
    "query_order": query_order,
    "query_logistics": query_logistics,
    "check_return_policy": check_return_policy,
    "product_search": product_search,
    "check_promotions": check_promotions,
}

TOOLS_OPENAI = {
    "query_order": {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "查订单：参数 order_id",
            "parameters": {"type": "object",
                           "properties": {"order_id": {"type": "string"}},
                           "required": ["order_id"]}
        }
    },
    "query_logistics": {
        "type": "function",
        "function": {
            "name": "query_logistics",
            "description": "查物流：参数 tracking_no",
            "parameters": {"type": "object",
                           "properties": {"tracking_no": {"type": "string"}},
                           "required": ["tracking_no"]}
        }
    },
    "check_return_policy": {
        "type": "function",
        "function": {
            "name": "check_return_policy",
            "description": "查退换货政策：可选参数 category",
            "parameters": {"type": "object",
                           "properties": {"category": {"type": "string"}},
                           "required": []}
        }
    },
    "product_search": {
        "type": "function",
        "function": {
            "name": "product_search",
            "description": "搜索商品信息：参数 keyword（如'降噪耳机'）",
            "parameters": {"type": "object",
                           "properties": {"keyword": {"type": "string"}},
                           "required": ["keyword"]}
        }
    },
    "check_promotions": {
        "type": "function",
        "function": {
            "name": "check_promotions",
            "description": "查询当前促销活动，无需参数",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
}

# ─── Agent 定义 ─────────────────────────────────────

# WHY: 每个 Agent 的 prompt 精确描述了它的"专业领域"和"能力边界"——
#      售前只管推荐、不管退换；售后只管订单、不做推荐。
#      能力边界清晰才能让 Router 做出正确的分发决策。

PRE_SALES_AGENT = {
    "name": "售前Agent（小选·推荐官）",
    "system": """你是"小选·推荐官"，好买电商的售前咨询专家。
职责：商品推荐、参数对比、促销活动介绍、选购建议。
能力边界：只管售前咨询，不处理订单/物流/退换货/投诉。
可用工具：product_search（查商品）、check_promotions（查促销）
风格：热情专业，像导购一样帮用户找到最适合的商品。""",
    "tools": ["product_search", "check_promotions"],
}

AFTER_SALES_AGENT = {
    "name": "售后Agent（小选·服务官）",
    "system": """你是"小选·服务官"，好买电商的售后处理专家。
职责：订单查询、物流追踪、退换货处理、投诉受理。
能力边界：只管售后事务，不做商品推荐。
可用工具：query_order（查订单）、query_logistics（查物流）、
           check_return_policy（查政策）
风格：专业高效，以解决问题为导向，对情绪激动的用户优先安抚。""",
    "tools": ["query_order", "query_logistics", "check_return_policy"],
}


# ══════════════════════════════════════════════════════════════
# Agent 执行引擎
# ══════════════════════════════════════════════════════════════

def run_specialist(agent: dict, user_input: str,
                   extra_context: str = "") -> str:
    """
    运行一个 Specialist Agent，支持自动工具调用。
    WHY: 每个 Agent 有自己的 system prompt + 工具子集，
         执行引擎是通用的（类似 Demo 06 的 ReAct 循环），
         但每次只暴露该 Agent 专属的工具。
    """
    messages = [
        {"role": "system", "content": agent["system"]},
    ]
    if extra_context:
        messages.append({"role": "system", "content": extra_context})
    messages.append({"role": "user", "content": user_input})

    agent_tools = [TOOLS_OPENAI[t] for t in agent["tools"]]

    for _ in range(4):  # 最多 4 轮工具调用
        response = create_completion(messages, tools=agent_tools,
                                     temperature=0.1)
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content or ""

        messages.append(msg)
        for tc in msg.tool_calls:
            fn = TOOL_REGISTRY.get(tc.function.name)
            args = json.loads(tc.function.arguments)
            result = fn(**args) if fn else f"未知工具"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    final = chat(messages, temperature=0.1)
    return final


# ══════════════════════════════════════════════════════════════
# Router —— 多 Agent 协作的调度中心
# ══════════════════════════════════════════════════════════════

ROUTER_PROMPT = """你是客服调度中心，负责分析用户问题并将任务分发给最合适的专家。

可用专家：
- pre_sales：售前专家，负责商品推荐、参数对比、促销咨询、选购建议
- after_sales：售后专家，负责订单查询、物流追踪、退换货、投诉处理
- both：问题同时涉及售前和售后，需要两个专家协同处理

输出格式（严格 JSON，无其他文字）：
{"route": "pre_sales"|"after_sales"|"both", "reason": "一句话理由"}"""


def route(user_input: str) -> dict:
    """Router Agent：分析用户意图，返回路由决策"""
    reply = chat([
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": user_input},
    ], temperature=0.1)
    try:
        return json.loads(reply)
    except json.JSONDecodeError:
        return {"route": "both", "reason": "无法确定，双专家处理"}


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_routing():
    """
    演示1：路由分发 —— Router 判断意图，分发给对应专家。
    WHY: 单 Agent 的 prompt 要同时覆盖售前和售后会很臃肿，
         Router 根据意图精准分发，每个专家只处理自己擅长的。
    """
    print("=" * 60)
    print(" 演示1：路由分发 —— 不同问题分给不同专家")
    print("=" * 60)

    queries = [
        "推荐一款300块以内的降噪耳机",
        "我的订单 ORD20240001 到哪了？能退货吗？",
        "最近有什么耳机促销活动？我上次买的耳机有质量问题想换货",
    ]

    for q in queries:
        decision = route(q)
        print(f"\n 用户: {q}")
        print(f" Router: → {decision['route']} ({decision['reason']})")

        if decision["route"] == "pre_sales":
            result = run_specialist(PRE_SALES_AGENT, q)
        elif decision["route"] == "after_sales":
            result = run_specialist(AFTER_SALES_AGENT, q)
        else:
            result = f"[需要双专家协同，见演示3]"

        print(f" 回答: {result[:150]}...")
    print()


def demo_handoff():
    """
    演示2：Agent 接力（Handoff）—— 一个 Agent 处理时发现需要
           另一个 Agent 的专长，将上下文传递过去。
    WHY: 真实对话中，用户可能从咨询转向投诉——
         先让售前推荐，用户说到"上次买的耳机有杂音"，
         售前识别到这是售后问题，将对话上下文接力给售后专家。
    """
    print("=" * 60)
    print(" 演示2：Agent 接力 —— 售前 → 售后的上下文传递")
    print("=" * 60)

    print("""
  模拟对话场景：
  Round 1: 用户 "我想买一款降噪耳机，300以内有什么推荐？"
  Round 2: 用户 "等等，我上次买的耳机还在保修期，有杂音能换吗？"
  Round 3: 售前 Agent 说 "这超出我的范围了，让我请售后同事来帮你"
""")

    # Round 1: 售前处理
    q1 = "我想买一款降噪耳机，300以内有什么推荐？"
    print(f"  [售前 Agent 处理] 用户: {q1}")
    response1 = run_specialist(PRE_SALES_AGENT, q1)
    print(f"  售前: {response1[:120]}...")

    # Round 2: 用户话题转向售后
    q2 = "等等，我上次买的漫步者 W820NB 还在保修期，但左耳有杂音，能换货吗？"
    print(f"\n  [用户转向售后] 用户: {q2}")

    # WHY: Handoff 的关键——把售前对话的摘要作为"上下文"传给售后 Agent，
    #      售后知道前面在聊什么，不会让用户重复信息
    context = f"[对话历史摘要] 用户之前咨询了耳机推荐，现在转向售后问题。"
    response2 = run_specialist(AFTER_SALES_AGENT, q2, extra_context=context)
    print(f"  售后（接手上下文）: {response2[:150]}...")
    print()


def demo_parallel_merge():
    """
    演示3：并行协作 —— 复合问题同时分发给多个专家，汇总结果。
    WHY: 用户一句话包含售前+售后两个需求时，
         Router 标记为 both → 并行调两个专家 → Merger 汇总。
         对比串行（先售后再售前或反之），并行减少了一半延迟。
    """
    print("=" * 60)
    print(" 演示3：并行协作 —— 复合问题双专家并行处理")
    print("=" * 60)

    question = ("我想趁618买个降噪耳机，预算500以内，有什么推荐？"
                "顺便帮我查下订单 ORD20240001 的状态。")

    decision = route(question)
    print(f" 用户: {question}")
    print(f" Router: → {decision['route']} ({decision['reason']})\n")

    # WHY: 两个 Agent 独立执行，互不依赖 → 可以并行
    print("  [并行] 售前 Agent 正在处理推荐部分...")
    pre_result = run_specialist(PRE_SALES_AGENT, question)

    print("  [并行] 售后 Agent 正在处理订单部分...")
    after_result = run_specialist(AFTER_SALES_AGENT, question)

    # ─── Merger 汇总 ──────────────────────────────
    print("\n  [汇总] Merger 综合两个专家的结果...\n")

    merger_prompt = f"""你是客服主管，需要把两位专家的回答合并成统一回复。

售前专家说：{pre_result}

售后专家说：{after_result}

请合并为一条结构化的客服回复，用分段区分不同主题。"""
    final = chat([
        {"role": "system",
         "content": "你是客服主管，专业清晰地整合信息。"},
        {"role": "user", "content": merger_prompt},
    ])
    print(f"  最终回答:\n{final}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 10: 多 Agent 协作          ║")
    print("║  路由分发 · 接力传递 · 并行汇总                    ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_routing()
    demo_handoff()
    demo_parallel_merge()

    print("=" * 60)
    print(" Demo 10 完成！多Agent = 分工明确 + 高效协作")
    print("=" * 60)


if __name__ == "__main__":
    main()
