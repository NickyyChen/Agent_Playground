# -*- coding: utf-8 -*-
"""
26_langgraph_pattern.py — LangGraph 图编排模式
==============================================

【概念】
LangGraph 把 Agent 工作流建模为"有向图"：
  - 节点（Node）: 处理单元（函数/Agent）
  - 边（Edge）: 流转方向（A 处理完 → B 处理）
  - 条件边（Conditional Edge）: 根据状态选择下一节点
  - State: 在节点间共享和传递的数据

对比手动编排（if/else + 函数调用）:
  手动: 3 个 if/elif 分支 → 加第 4 个要改主逻辑
  LangGraph: 3 条条件边 → 加第 4 条只需加一行 add_edge

【在智能客服中的应用】
- 退款审批工作流（demo 11 的完整案例）
- 多 Agent 协作的编排
- 人机协同流程（审批节点等待人工输入）

【pip install】
pip install langgraph

【ASCII 架构图】

  StateGraph 结构:

  ┌──────────┐
  │  START    │
  └────┬─────┘
       ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐
  │ Node A   │───▶│ Node B   │───▶│ Node C   │    ← 固定边
  └──────────┘    └──────────┘    └────┬─────┘
                                       │
                              ┌────────┼────────┐
                              │        │        │        ← 条件边
                              ▼        ▼        ▼
                         ┌────────┐┌────────┐┌────────┐
                         │Node D  ││Node E  ││Node F  │
                         └───┬────┘└───┬────┘└───┬────┘
                             │         │         │
                             └─────────┼─────────┘
                                       ▼
                                  ┌──────────┐
                                  │   END    │
                                  └──────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END


# ══════════════════════════════════════════════════════════════
# 1. 构建最简单的图 —— 两个节点一条边
# WHY: StateGraph + add_node + add_edge 是三个核心操作——
#      理解这三个就可以开始编排任何工作流。
# ══════════════════════════════════════════════════════════════

def demo_simple_graph():
    print("=" * 50)
    print(" 1. 最简单的 LangGraph —— 两个节点一条边")
    print("=" * 50)

    # WHY: TypedDict 定义 State 的形状——
    #      LangGraph 自动在节点间传递这个 State
    class SimpleState(TypedDict):
        user_input: str
        processed: str

    def node_a(state: SimpleState) -> dict:
        """
        节点A：接收用户输入。
        WHY: 返回 dict（字段的增量更新）——
             LangGraph 自动把返回值合并到 state 中。
        """
        print(f"  [Node A] 收到: {state['user_input']}")
        return {"processed": f"已处理: {state['user_input'][:20]}..."}

    def node_b(state: SimpleState) -> dict:
        """节点B：输出结果"""
        print(f"  [Node B] 输出: {state['processed']}")
        return {}

    # 构建图
    workflow = StateGraph(SimpleState)
    workflow.add_node("a", node_a)
    workflow.add_node("b", node_b)

    workflow.set_entry_point("a")     # 入口节点
    workflow.add_edge("a", "b")       # WHY: a → b，固定边
    workflow.add_edge("b", END)       # b → END，结束

    graph = workflow.compile()
    result = graph.invoke({"user_input": "我要退货，订单ORD001"})
    print(f"  最终 state: {result}")
    print()


# ══════════════════════════════════════════════════════════════
# 2. 条件边 —— 根据状态分支
# WHY: add_conditional_edges 是 LangGraph 最强大的特性——
#      不是硬编码 if/elif，而是声明"根据这个函数的返回值选择下一节点"。
#      加分支只需加一个节点 + 一条映射，不改现有代码。
# ══════════════════════════════════════════════════════════════

def demo_conditional():
    print("=" * 50)
    print(" 2. 条件边 —— 根据状态分支")
    print("=" * 50)

    class IntentState(TypedDict):
        user_input: str
        intent: str
        response: str

    def classify_intent(state: IntentState) -> dict:
        """意图分类节点"""
        msg = state["user_input"]
        if "退货" in msg or "退款" in msg:
            intent = "refund"
        elif "订单" in msg or "物流" in msg:
            intent = "order"
        else:
            intent = "general"
        print(f"  [分类] '{msg[:20]}...' → {intent}")
        return {"intent": intent}

    def handle_refund(state: IntentState) -> dict:
        return {"response": "退货部门处理中，请提供订单号"}

    def handle_order(state: IntentState) -> dict:
        return {"response": "正在查询订单，请稍候..."}

    def handle_general(state: IntentState) -> dict:
        return {"response": "您好！请问有什么可以帮您？"}

    def intent_router(state: IntentState) -> Literal["refund", "order",
                                                      "general"]:
        """
        条件路由函数。
        WHY: 返回字符串，LangGraph 根据映射表自动路由到对应节点。
             不是 if/elif——这个返回值直接驱动下游节点选择。
        """
        return state["intent"]

    workflow = StateGraph(IntentState)
    workflow.add_node("classify", classify_intent)
    workflow.add_node("refund_handler", handle_refund)
    workflow.add_node("order_handler", handle_order)
    workflow.add_node("general_handler", handle_general)

    workflow.set_entry_point("classify")

    # WHY: 条件边 = 路由函数 + 值→节点映射表
    workflow.add_conditional_edges(
        "classify",
        intent_router,
        {
            "refund": "refund_handler",
            "order": "order_handler",
            "general": "general_handler",
        }
    )

    # 三个处理节点都指向 END
    workflow.add_edge("refund_handler", END)
    workflow.add_edge("order_handler", END)
    workflow.add_edge("general_handler", END)

    graph = workflow.compile()

    # 测试三条不同路径
    test_cases = [
        "我要退款",
        "查一下订单ORD001",
        "今天天气真好",
    ]

    for msg in test_cases:
        print(f"\n  用户: {msg}")
        result = graph.invoke({"user_input": msg})
        print(f"  客服: {result['response']}")
    print()


# ══════════════════════════════════════════════════════════════
# 3. 对比：手动编排 vs LangGraph 编排
# ══════════════════════════════════════════════════════════════

def demo_comparison():
    print("=" * 50)
    print(" 3. 手动编排 vs LangGraph 编排")
    print("=" * 50)

    print("""
  场景: 退款审批流，需要 意图→订单→政策→路由→结果 五步

  手动编排 (if/elif):
  ┌───────────────────┬──────────────────────┐
  │ def process():    │ 修改成本              │
  │   intent = step1()│                       │
  │   order = step2() │ 加一个"换货"分支:      │
  │   policy = step3()│ - 加一个函数           │
  │                   │ - 在 if 中加 elif     │
  │   if approved:    │ - 可能漏改其他引用      │
  │     result_a()    │                        │
  │   elif rejected:  │                       │
  │     result_b()    │                       │
  │   elif escalated: │                       │
  │     result_c()    │                       │
  └───────────────────┴──────────────────────┘

  LangGraph 编排:
  ┌───────────────────┬──────────────────────┐
  │ workflow = Graph()│ 修改成本              │
  │ add_node("a", fn) │                       │
  │ add_node("b", fn) │ 加一个"换货"分支:      │
  │ add_edge("a","b") │ - 加一个节点           │
  │ add_conditional(  │ - 加一行条件映射       │
  │   "b", router, {  │ - 不加 if，不改已有代码 │
  │     "appr":"c1",  │                       │
  │     "rej":"c2",   │ 节点可复用、可插拔       │
  │     "esc":"c3",   │                       │
  │   })              │                       │
  └───────────────────┴──────────────────────┘

  结论: 3 个分支以下手动 OK，5 个以上 LangGraph 优势明显
  """)
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║  Python 基础 26: LangGraph 图编排模式        ║")
    print("╚══════════════════════════════════════════════╝")
    print()

    demo_simple_graph()
    demo_conditional()
    demo_comparison()


if __name__ == "__main__":
    main()
