# -*- coding: utf-8 -*-
"""
LangGraph 多 Agent 编排器 —— Demo 11 + Demo 10 + Demo 16
=========================================================
知识点:
  Demo 10 — 多 Agent 协作 (Router → 售前/售后)
  Demo 11 — LangGraph StateGraph 编排 + 条件路由
  Demo 16 — Human-in-the-Loop (interrupt + Command resume)
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from demos_all.config import LLM_CONFIG


class ServiceState(TypedDict):
    user_input: str
    intent: str              # pre_sales / after_sales
    agent_result: str
    needs_human: bool
    human_decision: str      # approved / rejected
    final_response: str


class CustomerServiceOrchestrator:
    """
    多 Agent 客服编排器。
    流程: Router → [售前|售后] → [HITL(可选)] → 最终回答
    """

    def __init__(self, llm, tools, verbose: bool = True):
        self.llm = llm
        self.tools = tools
        self.verbose = verbose
        self.graph = self._build()

    # ─── 节点函数 ──────────────────────────────

    def _router_node(self, state: ServiceState) -> dict:
        """Demo 10: Router Agent"""
        reply = self.llm.chat([
            {"role": "system",
             "content": "分类用户意图: pre_sales(售前/推荐/促销) 或 after_sales(售后/订单/退货/投诉)。只输出这两个词之一。"},
            {"role": "user", "content": state["user_input"]},
        ], profile="fast")
        intent = "after_sales" if "after" in reply.lower() else \
                 "pre_sales" if "pre" in reply.lower() else "after_sales"
        if self.verbose:
            print(f"  [Router] → {intent}")
        return {"intent": intent}

    def _pre_sales_node(self, state: ServiceState) -> dict:
        if self.verbose:
            print(f"  [售前Agent] 处理中...")
        result = self.llm.chat([
            {"role": "system",
             "content": "你是好买电商售前专家：商品推荐、参数对比、促销介绍。热情专业。"},
            {"role": "user", "content": state["user_input"]},
        ], profile="premium")
        return {"agent_result": result}

    def _after_sales_node(self, state: ServiceState) -> dict:
        if self.verbose:
            print(f"  [售后Agent] 处理中...")
        # 使用工具查询
        messages = [
            {"role": "system", "content": "你是好买电商售后专家。用工具查数据后回答。"},
            {"role": "user", "content": state["user_input"]},
        ]
        openai_tools = self.tools.to_openai()
        resp = self.llm.client.chat.completions.create(
            model=LLM_CONFIG["model"], messages=messages,
            tools=openai_tools, temperature=0.1)
        msg = resp.choices[0].message
        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = self.tools.call(tc.function.name, **args)
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": result})
        final = self.llm.chat(messages, profile="standard")
        return {"agent_result": final}

    def _hitl_node(self, state: ServiceState) -> dict:
        """Demo 16: 高风险操作需人工审核"""
        if "退款" not in state["user_input"] and "投诉" not in state["user_input"]:
            return {"needs_human": False}
        if self.verbose:
            print(f"  [HITL] 检测到退款/投诉，暂停等人工审核...")
        decision = interrupt({
            "message": "请审核以下客服回复",
            "agent_reply": state["agent_result"],
            "options": ["approved", "rejected"],
        })
        if self.verbose:
            print(f"  [HITL] 人工决策: {decision}")
        return {"needs_human": True, "human_decision": decision}

    def _merge_node(self, state: ServiceState) -> dict:
        final = state.get("agent_result", "")
        if state.get("needs_human") and state.get("human_decision") == "rejected":
            final = "该回复经人工审核被驳回，已交由高级客服重新处理。请致电 400-800-8888。"
        return {"final_response": final}

    # ─── 路由函数 ──────────────────────────────

    def _intent_router(self, state: ServiceState) -> Literal["pre_sales", "after_sales"]:
        return state["intent"]

    # ─── 构建图 (Demo 11) ──────────────────────

    def _build(self):
        wf = StateGraph(ServiceState)
        wf.add_node("router", self._router_node)
        wf.add_node("pre_sales", self._pre_sales_node)
        wf.add_node("after_sales", self._after_sales_node)
        wf.add_node("hitl", self._hitl_node)
        wf.add_node("merge", self._merge_node)

        wf.set_entry_point("router")
        wf.add_conditional_edges("router", self._intent_router, {
            "pre_sales": "pre_sales",
            "after_sales": "after_sales",
        })
        wf.add_edge("pre_sales", "hitl")
        wf.add_edge("after_sales", "hitl")
        wf.add_edge("hitl", "merge")
        wf.add_edge("merge", END)
        return wf.compile(checkpointer=MemorySaver())

    def run(self, user_input: str) -> dict:
        result = self.graph.invoke({"user_input": user_input},
                                   {"configurable": {"thread_id": "default"}})
        return result
