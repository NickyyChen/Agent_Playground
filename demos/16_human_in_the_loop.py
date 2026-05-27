# -*- coding: utf-8 -*-
"""
16_human_in_the_loop.py — Human-in-the-Loop：人工审核节点
=========================================================

【概念】
Agent 不能所有事都自己决定。涉及金钱、数据删除、对外发送消息等
高风险操作时，必须在执行前暂停，等待人类审核确认。

LangGraph 提供了两个关键 API 实现这个模式：
  interrupt(msg) —— 在节点中暂停执行，向人类展示审核信息
  Command(resume=value) —— 人类决策后，把决策值注入图继续执行

【在智能客服中解决什么问题】
退款/大额优惠券发放/投诉赔偿 —— 这些操作如果让 Agent 自动执行，
一旦判断错误直接造成经济损失。Human-in-the-Loop 在关键节点
插入"人工确认"环节，Agent 负责分析建议，人类做最终决策。

【核心流程】
1. Agent 分析订单 → 匹配政策 → 生成退款建议
2. 在"确认退款"节点调用 interrupt()，暂停并展示决策信息
3. 人类审核后，通过 Command(resume={"approved": True/False}) 继续
4. 批准 → 执行退款；拒绝 → 生成拒绝回复

【pip install】
pip install openai langgraph

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │            Human-in-the-Loop 退款审核流程             │
  │                                                       │
  │  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
  │  │ 订单核实  │───▶│ 政策匹配  │───▶│ 退款建议生成  │   │
  │  └──────────┘    └──────────┘    └──────┬───────┘   │
  │                                         │           │
  │                                         ▼           │
  │                              ┌──────────────────┐   │
  │                              │  🔴 interrupt()   │   │
  │                              │  暂停！等待人工审核 │   │
  │                              │                  │   │
  │                              │ "订单299元, 7天内 │   │
  │                              │  未拆封, 建议退款" │   │
  │                              └────┬────┬────────┘   │
  │                                   │    │            │
  │                         批准 ◄────┘    └────► 拒绝  │
  │                           │                  │      │
  │                           ▼                  ▼      │
  │                    ┌──────────┐      ┌──────────┐   │
  │                    │ 执行退款  │      │ 拒绝退款  │   │
  │                    └──────────┘      └──────────┘   │
  └──────────────────────────────────────────────────────┘
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from shared.llm_client import chat
from shared.mock_data import MOCK_ORDERS, RETURN_POLICY


# ══════════════════════════════════════════════════════════════
# 状态定义
# ══════════════════════════════════════════════════════════════

class RefundState(TypedDict):
    user_input: str
    order_id: str
    order_info: str
    policy_analysis: str
    refund_suggestion: str
    human_decision: str    # "approved" | "rejected"
    final_response: str


# ══════════════════════════════════════════════════════════════
# 节点函数
# ══════════════════════════════════════════════════════════════

def extract_intent(state: RefundState) -> dict:
    """Step 1: 提取订单号"""
    print("  [Step 1] 意图提取...")
    reply = chat([
        {"role": "system", "content": "提取用户输入中的订单号，只输出订单号，无则输出null"},
        {"role": "user", "content": state["user_input"]},
    ], temperature=0)
    order_id = reply.strip()
    print(f"           订单号: {order_id}")
    return {"order_id": order_id if order_id != "null" else ""}


def check_order(state: RefundState) -> dict:
    """Step 2: 查询订单"""
    print("  [Step 2] 订单核实...")
    oid = state.get("order_id", "")
    order = MOCK_ORDERS.get(oid, {})
    info = json.dumps(order, ensure_ascii=False, indent=2) if order else f"订单{oid}不存在"
    print(f"           {info[:80]}...")
    return {"order_info": info}


def analyze_policy(state: RefundState) -> dict:
    """Step 3: LLM 分析政策 + 生成退款建议"""
    print("  [Step 3] 政策分析 & 生成退款建议...")
    reply = chat([
        {"role": "system", "content": f"""你是退款审核助理。分析以下订单是否满足退款条件。

平台政策:
{RETURN_POLICY}

输出格式:
建议: [批准/拒绝] 退款 [金额] 元
理由: [一句话依据]
风险: [低/中/高] — [风险说明]"""},
        {"role": "user", "content": f"订单: {state['order_info']}\n用户请求: {state['user_input']}"},
    ], temperature=0.1)
    print(f"           建议: {reply[:100]}...")
    return {"policy_analysis": reply, "refund_suggestion": reply}


def human_review(state: RefundState) -> dict:
    """
    Step 4: 🔴 Human-in-the-Loop —— 暂停，等待人工决策。
    WHY: interrupt() 会将当前 state 保存到 checkpoint，
         暂停图执行，等待外部通过 Command(resume=...) 继续。
         人工看到的是 suggestion + order_info，做出批准/拒绝决策。
    """
    print("  [Step 4] 🔴 暂停 —— 等待人工审核...")

    # WHY: interrupt() 的参数是人类审核者看到的信息——
    #      包含退款建议、订单信息，帮助人类做出决策
    decision = interrupt({
        "message": "请审核以下退款申请",
        "suggestion": state["refund_suggestion"],
        "order": state.get("order_info", ""),
        "options": ["approved", "rejected"],
    })

    # 人类通过 Command(resume="approved") 或 Command(resume="rejected") 继续
    print(f"           人工决策: {decision}")
    return {"human_decision": decision}


def approved_result(state: RefundState) -> dict:
    """Step 5a: 退款批准"""
    print("  [Step 5a] 退款已批准 —— 生成通知")
    reply = chat([
        {"role": "system", "content": "退款已批准，生成友好的通知消息。包含退款金额和到账时间（3工作日）。"},
        {"role": "user", "content": state["refund_suggestion"]},
    ])
    return {"final_response": reply}


def rejected_result(state: RefundState) -> dict:
    """Step 5b: 退款拒绝"""
    print("  [Step 5b] 退款已拒绝 —— 生成通知")
    reply = chat([
        {"role": "system", "content": "退款被审核拒绝，生成礼貌的通知消息。说明原因并提供替代方案（联系人工客服 400-800-8888）。"},
        {"role": "user", "content": state["refund_suggestion"]},
    ])
    return {"final_response": reply}


# ══════════════════════════════════════════════════════════════
# 条件路由
# ══════════════════════════════════════════════════════════════

def after_review(state: RefundState) -> str:
    decision = state.get("human_decision", "rejected")
    return decision  # "approved" → approved_result, "rejected" → rejected_result


# ══════════════════════════════════════════════════════════════
# 构建图
# ══════════════════════════════════════════════════════════════

def build_graph():
    workflow = StateGraph(RefundState)

    workflow.add_node("extract", extract_intent)
    workflow.add_node("order", check_order)
    workflow.add_node("policy", analyze_policy)
    workflow.add_node("review", human_review)
    workflow.add_node("approved", approved_result)
    workflow.add_node("rejected", rejected_result)

    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "order")
    workflow.add_edge("order", "policy")
    workflow.add_edge("policy", "review")
    workflow.add_conditional_edges("review", after_review, {
        "approved": "approved",
        "rejected": "rejected",
    })
    workflow.add_edge("approved", END)
    workflow.add_edge("rejected", END)

    # WHY: MemorySaver 提供 checkpoint 持久化——
    #      interrupt() 暂停时 state 存到 checkpointer，
    #      resume 时从 checkpoint 恢复继续执行
    return workflow.compile(checkpointer=MemorySaver())


# ══════════════════════════════════════════════════════════════
# 演示
# ══════════════════════════════════════════════════════════════

def demo_hitl_approved():
    """
    演示1：人工批准流程 —— Agent 建议退款，人类批准。
    """
    print("=" * 60)
    print(" 演示1：完整 HITL 流程 —— 人工批准退款")
    print("=" * 60)

    graph = build_graph()
    # WHY: thread_id 标识一次对话，checkpointer 按 thread_id 存储 checkpoint
    config = {"configurable": {"thread_id": "demo-approved"}}

    question = "订单 ORD20240001，我买的耳机包装都没拆，申请退款"

    print(f"\n  用户: {question}\n")

    # Step A: 执行到 interrupt 点
    print("  ▶ 开始执行（到 interrupt 自动暂停）...\n")
    state = graph.invoke({"user_input": question}, config)
    print(f"\n  🔴 图已暂停在 human_review 节点")
    print(f"  当前决策信息: {state.get('refund_suggestion', '')[:100]}...")

    # Step B: 人类审核 → 批准
    print("\n  👤 人工审核中... 审核结果: 批准 ✓")
    print("  ▶ 通过 Command(resume) 继续执行...\n")

    graph.invoke(Command(resume="approved"), config)
    final_state = graph.get_state(config)
    print(f"\n  最终回复: {final_state.values.get('final_response', '')}")


def demo_hitl_rejected():
    """
    演示2：人工拒绝 —— 同一条流程，人类拒绝的结果。
    WHY: 展示同一个工作流，人类决策不同 → 走不同分支。
    """
    print("\n" + "=" * 60)
    print(" 演示2：人工拒绝退款")
    print("=" * 60)

    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-rejected"}}

    question = "订单 ORD20240001，耳机用了5天左耳有杂音，我要全额退款！"

    print(f"\n  用户: {question}\n")
    print("  ▶ 开始执行...\n")

    state = graph.invoke({"user_input": question}, config)
    print(f"\n  🔴 暂停，等待审核...")
    print(f"  Agent建议: {state.get('refund_suggestion', '')[:150]}...")

    # 人类审核：质量问题 → 应该换货而不是退款 → 拒绝退款
    print("\n  👤 人工审核: 质量问题应走换货，拒绝退款 → 建议用户换货")
    graph.invoke(Command(resume="rejected"), config)
    final_state = graph.get_state(config)
    print(f"\n  最终回复: {final_state.values.get('final_response', '')}")


def demo_hitl_explanation():
    """
    演示3：HITL 的关键设计决策。
    """
    print("\n" + "=" * 60)
    print(" 演示3：Human-in-the-Loop 设计原则")
    print("=" * 60)

    print("""
  interrupt() 应该放在哪里？

  ✅ 应该放的位置:
  - 涉及金钱: 退款、发券、赔款
  - 不可逆操作: 删除订单、注销账户
  - 对外通信: 发送营销短信/邮件
  - 高风险决策: AI 置信度低时升级人工

  ❌ 不应该放的位置:
  - 纯信息查询 (查订单/物流)
  - 确定性规则判断 (金额计算)
  - 用户明确授权过的操作

  interrupt() 传什么信息给人类？
  - What: 要做什么操作
  - Why: Agent 为什么建议这样做
  - Context: 相关的订单/政策/用户信息
  - Options: 可选决策 (批准/拒绝/修改金额等)
""")


def main():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║  Agent-Playground Demo 16: Human-in-the-Loop      ║")
    print("║  interrupt() → 暂停 → 人工审核 → Command(resume)   ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_hitl_approved()
    demo_hitl_rejected()
    demo_hitl_explanation()

    print("=" * 60)
    print(" Demo 16 完成！HITL = 高风险操作必须经过人类")
    print("=" * 60)


if __name__ == "__main__":
    main()
