# -*- coding: utf-8 -*-
"""
11_langgraph_flow.py — LangGraph 编排多 Agent：退款审批工作流
=============================================================

【概念】
Demo 10 的多 Agent 协作是"手动"的——Router 调谁、Handoff 传谁，全由代码
if/else 控制。当 Agent 数量增多、流转逻辑变复杂时，手动编排变得不可维护。

LangGraph 通过**状态图（StateGraph）**解决这个问题：
  - 每个 Agent/步骤是一个**节点（Node）**
  - 流转方向由**边（Edge）**定义
  - 根据状态做分支用**条件边（Conditional Edge）**
  - 共享的 State 在节点间自动传递

类比：Demo 10 是"人工调度"，Demo 11 是"工作流引擎自动编排"。

【在智能客服中解决什么问题】
退款审批是典型的多 Agent 协作场景：
  用户申请退款 → 意图分类 → 订单核实 → 政策匹配 → 审核决策 → 执行

这个流程有固定的步骤顺序，同时又有条件分支（批准/拒绝/升级人工），
正是 LangGraph 最擅长解决的问题。

【核心流程】
1. Intent Node：解析用户输入，提取订单号、退货原因
2. Order Node：调用 query_order 获取订单状态
3. Policy Node：调用 check_return_policy 匹配政策条款
4. Decision Router：条件路由——批准/拒绝/升级
5. Result Nodes：生成最终回复

【pip install】
pip install openai langgraph

【ASCII 架构图】

                          ┌─────────────┐
      用户 "我要退款" ───▶│ ① 意图分类   │
                          │ Intent Node │
                          └──────┬──────┘
                                 │ 提取: order_id="ORD001", reason="质量问题"
                                 ▼
                          ┌─────────────┐
                          │ ② 订单核实   │
                          │ Order Node  │ ── query_order()
                          └──────┬──────┘
                                 │ order: {status:"已签收", days:5, price:299}
                                 ▼
                          ┌─────────────┐
                          │ ③ 政策匹配   │
                          │ Policy Node │ ── check_return_policy("耳机")
                          └──────┬──────┘
                                 │ 匹配: 签收7天内+未拆封→可退
                                 │       已拆封→不支持无理由退货
                                 ▼
                          ┌─────────────┐
                          │ ④ 决策路由   │
                          │   Router    │
                          └──┬──┬──┬───┘
                             │  │  │
                    ┌────────┘  │  └────────┐
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │⑤ 批准    │ │⑥ 拒绝   │ │⑦ 升级   │
              │ APPROVED │ │ REJECTED│ │ESCALATED│
              └─────────┘ └─────────┘ └─────────┘
                    │           │           │
                    └───────────┼───────────┘
                                ▼
                          ┌─────────┐
                          │   END   │
                          └─────────┘

  State 在节点间流转: {user_input, order_id, order_info, policy, decision, response}
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from shared.llm_client import chat
from shared.mock_data import MOCK_ORDERS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 状态定义 —— 在节点间流转的共享数据
# WHY: TypedDict 定义 State 的字段和类型，LangGraph 自动在
#      节点间传递和更新。每个节点函数接收 state，返回 state 的
#      增量更新（只改自己负责的字段），而非整个 state。
# ══════════════════════════════════════════════════════════════

class RefundState(TypedDict):
    user_input: str          # 用户原始输入
    order_id: str            # 提取的订单号
    order_info: str          # 订单查询结果（JSON 文本）
    policy_info: str         # 匹配的政策条款
    decision: str            # 决策: approved / rejected / escalated
    final_response: str      # 最终回复


# ══════════════════════════════════════════════════════════════
# Node 1: 意图分类 —— 解析用户输入，提取订单号和退货原因
# WHY: 第一个节点不做复杂判断，只做"信息提取"——
#      从自然语言输入中结构化为 order_id + reason，
#      为后续节点提供干净的结构化数据。
# ══════════════════════════════════════════════════════════════

INTENT_PROMPT = """你是客服意图解析器。从用户输入中提取以下信息，输出 JSON：

{"order_id": "订单号或null", "reason": "退货原因简述或null"}

只输出 JSON，不要其他文字。"""


def intent_node(state: RefundState) -> dict:
    print("  [Node 1] 意图分类 —— 解析用户输入")

    reply = chat([
        {"role": "system", "content": INTENT_PROMPT},
        {"role": "user", "content": state["user_input"]},
    ], temperature=0.1)

    try:
        parsed = json.loads(reply)
    except json.JSONDecodeError:
        parsed = {"order_id": None, "reason": state["user_input"]}

    order_id = parsed.get("order_id", "") or ""
    print(f"           提取: order_id={order_id}, reason={parsed.get('reason', '')}")
    return {"order_id": order_id}


# ══════════════════════════════════════════════════════════════
# Node 2: 订单核实 —— 用 query_order 获取真实订单数据
# WHY: 政策判断必须基于真实数据（签收日期、商品品类），
#      不用 LLM 而用确定性函数查询，保证数据准确。
# ══════════════════════════════════════════════════════════════

def order_node(state: RefundState) -> dict:
    print("  [Node 2] 订单核实 —— 查询订单数据")

    order_id = state.get("order_id", "")
    order = MOCK_ORDERS.get(order_id)

    if order:
        order_info = json.dumps(order, ensure_ascii=False, indent=2)
        print(f"           查到: {order['product']}, {order['status']}, "
              f"签收于{order.get('delivery_time', '?')[:10]}")
    else:
        order_info = f"订单 {order_id} 不存在"
        print(f"           {order_info}")

    return {"order_info": order_info}


# ══════════════════════════════════════════════════════════════
# Node 3: 政策匹配 —— LLM 根据订单数据匹配退换货政策
# WHY: 这个节点是"判断引擎"——把订单数据（事实）和政策
#      （规则）一起给 LLM，让它判断属于哪种情况。
#      不是简单关键词匹配，而是语义推理。
# ══════════════════════════════════════════════════════════════

POLICY_PROMPT = f"""你是退换货政策审核员。根据以下订单信息和平台政策，
判断该退款申请应该被批准、拒绝还是升级人工。

平台政策：
{RETURN_POLICY}

输出格式（严格 JSON）：
{{"decision": "approved|rejected|escalated",
  "reason": "判断依据，引用具体政策条款"}}

决策指南：
- 签收7天内 + 未拆封/完好 → approved（可退款）
- 签收7天内 + 已拆封（特殊商品如耳机）→ rejected（不支持无理由退货）
- 签收15天内 + 质量问题 → escalated（换货而非退款，需人工确认）
- 投诉/情绪激烈 → escalated
- 订单数据不足 → rejected（引导用户补充信息）"""


def policy_node(state: RefundState) -> dict:
    print("  [Node 3] 政策匹配 —— LLM 审核订单+政策")

    reply = chat([
        {"role": "system", "content": POLICY_PROMPT},
        {"role": "user",
         "content": f"订单信息:\n{state['order_info']}\n\n"
                    f"用户申请:\n{state['user_input']}"},
    ], temperature=0.1)

    try:
        result = json.loads(reply)
        decision = result.get("decision", "escalated")
    except json.JSONDecodeError:
        decision = "escalated"

    print(f"           决策: {decision}")
    return {"decision": decision, "policy_info": reply}


# ══════════════════════════════════════════════════════════════
# Node 4: 条件路由 —— 根据 decision 字段分发到不同分支
# WHY: 这是 LangGraph 的核心——不是写 if/elif/else，
#      而是返回一个字符串，LangGraph 自动路由到对应节点。
#      新增分支只需加一个 return 值和对应的节点，不改现有逻辑。
# ══════════════════════════════════════════════════════════════

def decision_router(state: RefundState) -> Literal["approved", "rejected",
                                                    "escalated"]:
    decision = state.get("decision", "escalated")
    print(f"  [Router] → {decision}")
    return decision


# ══════════════════════════════════════════════════════════════
# Node 5-7: 结果节点 —— 三种决策分别生成回复
# WHY: 每个分支有独立的回复生成逻辑和语气——
#      批准的回复要包含退款指引，
#      拒绝的要解释原因并给替代方案，
#      升级的要安抚情绪并说明后续流程。
# ══════════════════════════════════════════════════════════════

RESULT_PROMPTS = {
    "approved": """你是"小选"，退款申请已批准。请根据订单和审核信息，
生成一条友好的批准回复。包含：
1. 祝贺退款申请通过
2. 退款金额和预计到账时间（3个工作日原路返回）
3. 操作指引（App 内确认即可）""",

    "rejected": """你是"小选"，退款申请未通过。请根据审核结果生成回复。
语气温和但坦诚。包含：
1. 遗憾告知结果
2. 引用政策说明原因
3. 提供替代方案（换货/联系人工客服）""",

    "escalated": """你是"小选"，退款申请需要升级人工处理。请生成回复。
包含：
1. 说明情况较复杂需人工审核
2. 预计 xx时间内回复
3. 提供客服热线 400-800-8888"""
}


def make_result_fn(label: str):
    """生成结果节点函数"""
    def result_fn(state: RefundState) -> dict:
        print(f"  [Node] 生成回复 —— {label}")
        reply = chat([
            {"role": "system", "content": RESULT_PROMPTS[label]},
            {"role": "user",
             "content": f"审核结论: {state.get('policy_info', '')}\n\n"
                        f"订单信息: {state.get('order_info', '')}"},
        ], temperature=0.3)
        return {"final_response": reply}
    return result_fn


# ══════════════════════════════════════════════════════════════
# 构建 LangGraph 工作流
# WHY: 所有节点注册到图里，边定义了流转方向。
#      add_conditional_edges 是核心——根据 decision_router 的
#      返回值自动分发到三个不同的结果节点。
#      这就是"编排"：定义规则一次，每次执行自动流转。
# ══════════════════════════════════════════════════════════════

def build_refund_graph() -> StateGraph:
    """构建退款审批 StateGraph"""
    workflow = StateGraph(RefundState)

    # WHY: 每个节点是一个独立的处理单元，只关心自己的输入输出
    workflow.add_node("intent", intent_node)
    workflow.add_node("order", order_node)
    workflow.add_node("policy", policy_node)
    workflow.add_node("approved_result", make_result_fn("approved"))
    workflow.add_node("rejected_result", make_result_fn("rejected"))
    workflow.add_node("escalated_result", make_result_fn("escalated"))

    # WHY: 直线流程——意图→订单→政策，不需要条件判断
    workflow.set_entry_point("intent")
    workflow.add_edge("intent", "order")
    workflow.add_edge("order", "policy")

    # WHY: 关键的条件分支——根据 decision_router 的返回值，
    #      LangGraph 自动选择走哪个结果节点，然后全部汇聚到 END
    workflow.add_conditional_edges(
        "policy",
        decision_router,
        {
            "approved": "approved_result",
            "rejected": "rejected_result",
            "escalated": "escalated_result",
        }
    )

    # 三个结果节点都指向 END
    workflow.add_edge("approved_result", END)
    workflow.add_edge("rejected_result", END)
    workflow.add_edge("escalated_result", END)

    return workflow.compile()


# ══════════════════════════════════════════════════════════════
# 演示函数
# ══════════════════════════════════════════════════════════════

def demo_refund_flow(graph):
    """
    演示1：完整退款审批流 —— 从用户输入到最终决策的自动化编排。
    WHY: 用三个不同场景展示同一套工作流如何处理不同情况：
         场景A：正常退货（7天内未拆封→批准）
         场景B：拆封耳机（特殊商品→拒绝）
         场景C：质量问题投诉（复杂情况→升级人工）
         同一张图，不同输入，自动走不同分支。
    """
    print("=" * 60)
    print(" 演示1：退款审批流 —— 三场景走不同分支")
    print("=" * 60)

    scenarios = [
        ("场景A: 正常退货",
         "订单 ORD20240001，我买的耳机包装都没拆，能退款吗？"),
        ("场景B: 拆封退货",
         "订单 ORD20240001，耳机用了5天左耳有杂音，我要全额退款！"),
        ("场景C: 质量问题投诉",
         "ORD20240001这个订单质量太差了！左耳没声音，"
         "你们必须给我一个说法，不然我去投诉！"),
    ]

    for label, question in scenarios:
        print(f"\n{'─' * 50}")
        print(f" {label}")
        print(f" 用户: {question}")
        print(f"{'─' * 50}")

        # WHY: graph.invoke() 是 LangGraph 的唯一入口——
        #      传入初始 state，自动按图流转所有节点，
        #      返回最终 state（含所有节点的累积输出）
        result = graph.invoke({"user_input": question})
        print(f"\n 最终回复:\n{result['final_response']}")
        print(f" 决策路径: {result.get('decision', '?')}")


def demo_graph_structure():
    """
    演示2：可视化 LangGraph 的编排结构。
    WHY: 用 ASCII 展示图的节点和边，帮助理解编排逻辑。
    """
    print("\n" + "=" * 60)
    print(" 演示2：编排结构可视化")
    print("=" * 60)

    print("""
  LangGraph 工作流定义（代码对应结构）:

  workflow = StateGraph(RefundState)
  workflow.add_node("intent", intent_node)        ──┐
  workflow.add_node("order", order_node)          ──┤ 顺序链路
  workflow.add_node("policy", policy_node)        ──┘
  workflow.add_node("approved_result", ...)       ──┐
  workflow.add_node("rejected_result", ...)       ──┤ 三个结果分支
  workflow.add_node("escalated_result", ...)      ──┘

  workflow.set_entry_point("intent")              # 入口
  workflow.add_edge("intent", "order")            # 固定边
  workflow.add_edge("order", "policy")            # 固定边
  workflow.add_conditional_edges(                 # 条件边
      "policy", decision_router,                  # 从 policy 出发
      {"approved": "approved_result", ...}        # 根据返回值路由
  )
  workflow.add_edge("approved_result", END)       # 终结边
  ...

  对比 Demo 10（手动编排）:
  ┌──────────────────────┬────────────────────────┐
  │  Demo 10 手动         │  Demo 11 LangGraph     │
  ├──────────────────────┼────────────────────────┤
  │ if route == "X":     │ add_conditional_edges() │
  │    call_agent_X()    │ 一次定义，自动流转       │
  │ elif route == "Y":   │                        │
  │    call_agent_Y()    │ 节点可复用、可插拔       │
  │                      │ 状态传递自动化           │
  │ 加分支 = 改代码       │ 加分支 = 加一个节点+边    │
  └──────────────────────┴────────────────────────┘
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 11: LangGraph 多Agent编排  ║")
    print("║  StateGraph → Node → Edge → Conditional Route    ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    graph = build_refund_graph()
    demo_refund_flow(graph)
    demo_graph_structure()

    print("=" * 60)
    print(" Demo 11 完成！编排 = 定义规则, 自动流转")
    print("=" * 60)


if __name__ == "__main__":
    main()
