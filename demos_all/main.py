# -*- coding: utf-8 -*-
"""
main.py —— 好买电商智能客服系统
=================================
集成 21 个 Demo 全部知识点的可运行工程。

运行方式:
  python demos_all/main.py              → CLI 交互模式
  python demos_all/main.py --server     → 启动 FastAPI 服务 (http://localhost:8080)
  python demos_all/main.py --demo       → 自动演示所有知识点

知识点覆盖:
  01 LLM 参数控制     → agent/llm.py (temperature/max_tokens 透传)
  02 Prompt 模板      → config.py (SYSTEM_PROMPT)
  03 Function Calling → agent/tools.py (ToolRegistry)
  04 记忆系统         → agent/memory.py (短期+长期+窗口管理)
  05 RAG 知识库       → agent/rag.py (切块+嵌入+检索+融合)
  06 ReAct Agent      → workflows/react.py
  07 Plan & Execute   → workflows/planner.py
  08 Reflection       → workflows/reflector.py
  09 MCP 协议         → agent/tools.py (to_mcp_tools/to_mcp_tools_call)
  10 多 Agent 协作     → workflows/orchestrator.py (Router→售前/售后)
  11 LangGraph 编排   → workflows/orchestrator.py (StateGraph+条件路由)
  12 LangChain 链式   → agent/llm.py (链式调用封装)
  13 安全护栏         → safety/guard.py (Topic/Input/Output)
  14 可观测性         → tracing/tracer.py (Span/Trace)
  15 Agent 评测       → tests/test_agent.py
  16 Human-in-the-Loop→ workflows/orchestrator.py (interrupt+Command)
  17 Context Window   → agent/memory.py (滑动窗口+摘要压缩)
  18 错误处理         → agent/llm.py (重试+熔断)
  19 模型路由         → agent/llm.py (fast/standard/premium)
  20 Prompt 缓存      → agent/llm.py (本地缓存)
  21 Skill 系统       → agent/skills.py (SkillRegistry+@skill装饰器)
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from demos_all.agent.llm import LLMClient
from demos_all.agent.memory import MemoryManager
from demos_all.agent.tools import ToolRegistry
from demos_all.agent.rag import RAGKnowledgeBase
from demos_all.agent.skills import SkillRegistry

from demos_all.workflows.react import ReActAgent
from demos_all.workflows.planner import PlanExecuteAgent
from demos_all.workflows.reflector import ReflectionAgent
from demos_all.workflows.orchestrator import CustomerServiceOrchestrator

from demos_all.safety.guard import SafetyGuard
from demos_all.tracing.tracer import Tracer, LangSmithTracer, create_tracer


class CustomerServiceSystem:
    """
    智能客服系统 —— 所有模块的集成点。
    """

    def __init__(self, tracer: LangSmithTracer = None):
        print("正在初始化智能客服系统...")

        # Core
        self.llm = LLMClient()
        self.tools = ToolRegistry()
        self.skills = SkillRegistry()
        self.safety = SafetyGuard(self.llm)
        self.tracer = tracer or create_tracer()

        # Memory & RAG (懒加载)
        self._memory = None
        self._rag = None

        # Workflows
        self.react = ReActAgent(self.llm, self.tools)
        self.planner = PlanExecuteAgent(self.llm, self.tools)
        self.reflector = ReflectionAgent(self.llm)
        self.orchestrator = CustomerServiceOrchestrator(self.llm, self.tools)

        print(f"初始化完成！LangSmith: {'已连接' if self.tracer.available else '离线模式'}")

    @property
    def memory(self):
        if self._memory is None:
            self._memory = MemoryManager()
            self._memory.llm = self.llm
        return self._memory

    @property
    def rag(self):
        if self._rag is None:
            self._rag = RAGKnowledgeBase()
        return self._rag

    # ─── Agent 运行接口 ──────────────────────────

    def run_react(self, question: str) -> tuple[str, list]:
        tracer = Tracer("ReAct")
        s = tracer.start("react_loop", question)
        reply, trace = self.react.run(question)
        tracer.end(s, reply[:80], type="react")
        return reply, trace

    def run_plan_execute(self, question: str) -> dict:
        return self.planner.run(question)

    def run_reflection(self, question: str) -> dict:
        return self.reflector.run(question)

    def run_orchestrator(self, question: str) -> dict:
        return self.orchestrator.run(question)

    def chat(self, question: str, mode: str = "react") -> str:
        """
        统一对话接口：安全流水线 → LangSmith 追踪 → Agent 处理。
        """
        # 安全护栏
        blocked = self.safety.pipeline(question)
        if blocked:
            return blocked

        # 模型路由
        profile = self.llm.route(question)

        # ─── LangSmith trace_run 包裹 Agent 执行 ───
        with self.tracer.trace_run(
            f"{mode}_agent",
            inputs={"question": question, "mode": mode, "profile": profile},
            tags=[mode, profile, "customer_service"],
            metadata={"router_profile": profile},
        ) as run:
            t0 = time.time()

            # Agent 执行
            if mode == "plan":
                result = self.planner.run(question)
                reply = result["answer"]
                # 记录工具调用
                for step in result.get("steps", []):
                    self.tracer.log_tool_call(
                        run, step["tool"], step.get("args", {}),
                        step.get("result", ""),
                        duration_ms=0)
            elif mode == "reflect":
                result = self.reflector.run(question)
                reply = result["final"]
            elif mode == "orchestrate":
                result = self.orchestrator.run(question)
                reply = result.get("final_response", "")
            else:  # react
                reply, react_trace = self.react.run(question)
                for t in react_trace:
                    self.tracer.log_tool_call(
                        run, t["tool"], t.get("args", {}),
                        t.get("result", ""),
                        duration_ms=0)

            elapsed = (time.time() - t0) * 1000

            # 记录 LLM 调用
            self.tracer.log_llm_call(
                run, f"{mode}_llm",
                messages=[{"role": "user", "content": question}],
                response=reply, duration_ms=elapsed,
                model="deepseek-chat", token_count=len(reply) // 2)

        # 输出护栏
        blocked = self.safety.pipeline(question, agent_reply=reply)
        if blocked and "[输出护栏]" in blocked:
            return blocked

        # 更新短期记忆
        self.memory.add_message("user", question)
        self.memory.add_message("assistant", reply)

        return reply


# ══════════════════════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════════════════════

def demo_mode():
    """演示模式：每个 Agent 调用自动上报 LangSmith"""
    system = CustomerServiceSystem()

    print(f"\n  LangSmith: {'已连接 ✓' if system.tracer.available else '离线模式 (设置 LANGCHAIN_API_KEY 启用)'}")
    print(f"  {json.dumps(system.tracer.get_stats(), ensure_ascii=False)}")

    demos = [
        ("ReAct", "react", "订单 ORD20240001 的耳机左耳有杂音，能换货吗？"),
        ("Plan&Exec", "plan", "查订单 ORD20240001，再看物流 SF1234567890"),
        ("Reflection", "reflect", "耳机用5天左耳没声，能退款吗？"),
        ("MultiAgent", "orchestrate", "推荐一款300以内的降噪耳机"),
    ]

    for name, mode, question in demos:
        print(f"\n{'='*60}")
        print(f"  [{name}] {question}")
        print(f"{'='*60}")
        reply = system.chat(question, mode=mode)
        print(f"  客服: {reply}")

    print(f"\n{'='*60}")
    print(f"  缓存: {system.llm.cache_stats}")
    print(f"  安全: {system.safety.stats}")
    print(f"  LangSmith: {'在线 ✓' if system.tracer.available else '离线'}")
    print(f"{'='*60}")


def cli_mode():
    """命令行交互模式"""
    system = CustomerServiceSystem()
    print(f"\nLangSmith: {'已连接' if system.tracer.available else '离线'}")
    print("输入消息开始对话（输入 quit 退出）")
    print("支持的模式: [r]eact / [p]lan / [f]eflect / [o]rchestrate\n")

    mode = "react"
    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() in ("r", "p", "f", "o"):
            modes = {"r": "react", "p": "plan", "f": "reflect", "o": "orchestrate"}
            mode = modes[user_input.lower()]
            print(f"  → 切换到 {mode} 模式\n")
            continue

        reply = system.chat(user_input, mode=mode)
        print(f"Bot > {reply}\n")


def server_mode():
    """启动 FastAPI 服务"""
    from api.routes import create_app
    import uvicorn

    system = CustomerServiceSystem()
    print(f"LangSmith: {'已连接' if system.tracer.available else '离线'}")
    app = create_app(system)
    print("启动 FastAPI 服务: http://127.0.0.1:8080")
    print("API 文档: http://127.0.0.1:8080/docs")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


if __name__ == "__main__":
    if "--server" in sys.argv:
        server_mode()
    elif "--demo" in sys.argv:
        demo_mode()
    else:
        cli_mode()
