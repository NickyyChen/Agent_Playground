# -*- coding: utf-8 -*-
"""
可观测性追踪 —— Demo 14 + LangSmith 深度集成
=============================================
支持双模式:
  1. LangSmith 云追踪 (设置 LANGCHAIN_API_KEY 自动启用)
  2. 本地追踪 (离线模式, 默认)

LangSmith 功能:
  - trace() 上下文管理器: 自动记录 run tree
  - Client: 查询历史 run、记录 feedback
  - Metadata: tags / inputs / outputs / token_usage
  - 集成 langchain 自动回调
"""

import sys, os, time, json, uuid
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

# ─── LangSmith 初始化 ──────────────────────────────
class _LSState:
    client = None

def _get_ls_client():
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        return None
    if _LSState.client is not None:
        return _LSState.client
    try:
        from langsmith import Client
        _LSState.client = Client(api_key=api_key)
        _LSState.client.list_projects()
        print("[LangSmith] 连接成功")
    except Exception as e:
        print(f"[LangSmith] 连接失败: {e}")
    return _LSState.client


# ══════════════════════════════════════════════════════════════
# 本地 Span / Trace (离线模式)
# ══════════════════════════════════════════════════════════════

class Span:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.start = time.time()
        self.end = None
        self.meta = {}
        self.input = ""
        self.output = ""

    def finish(self, output: str = "", **meta):
        self.end = time.time()
        self.output = output[:200]
        self.meta.update(meta)
        if self.parent:
            self.parent.children.append(self)

    @property
    def duration_ms(self) -> float:
        return (self.end - self.start) * 1000 if self.end else 0

    def to_dict(self) -> dict:
        return {"name": self.name, "duration_ms": round(self.duration_ms, 1),
                "input": self.input, "output": self.output,
                "meta": self.meta,
                "children": [c.to_dict() for c in self.children]}


class Tracer:
    """本地追踪器"""

    def __init__(self, name: str = "trace"):
        self.name = name
        self.spans = []
        self._stack = []

    def start(self, name: str, input_summary: str = "") -> Span:
        parent = self._stack[-1] if self._stack else None
        span = Span(name, parent)
        span.input = input_summary
        self._stack.append(span)
        if not parent:
            self.spans.append(span)
        return span

    def end(self, span: Span, output: str = "", **meta):
        span.finish(output, **meta)
        if self._stack and self._stack[-1] == span:
            self._stack.pop()

    def report(self) -> str:
        total_ms = sum(s.duration_ms for s in self.spans)

        def _render(spans, indent=0):
            lines = []
            for s in spans:
                bar = "█" * int(s.duration_ms / max(total_ms, 1) * 15)
                lines.append(f"{'  ' * indent}├─ {s.name:<20s} "
                             f"{s.duration_ms:>6.0f}ms {bar}")
                lines.extend(_render(s.children, indent + 1))
            return lines

        lines = [f"Trace: {self.name} (总耗时 {total_ms:.0f}ms)"]
        lines.extend(_render(self.spans))
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════
# LangSmith 集成追踪器
# ══════════════════════════════════════════════════════════════

class LangSmithTracer:
    """
    LangSmith 全功能追踪器。
    知识点:
      - trace() 上下文管理器: 自动创建 run tree
      - Client.create_run(): 手动创建 run
      - Client.create_feedback(): 记录用户反馈
      - run.add_metadata(): 附加自定义标签
      - 集成 langchain 自动回调
    """

    def __init__(self, project_name: str = "agent-playground"):
        self.project_name = project_name
        self.client = _get_ls_client()
        self.available = self.client is not None
        self.local_tracer = None

    def _ensure_project(self):
        """确保 LangSmith project 存在"""
        try:
            if self.client:
                # 尝试读取 project，不存在则创建
                self.client.create_project(self.project_name,
                                           description="Agent-Playground 智能客服追踪")
        except Exception:
            pass

    # ─── 核心追踪 ──────────────────────────────

    @contextmanager
    def trace_run(self, name: str, inputs: dict = None,
                  tags: list[str] = None, metadata: dict = None):
        if self.available:
            run_id = str(uuid.uuid4())
            self.client.create_run(
                id=run_id, name=name, run_type="chain",
                inputs=inputs or {},
                tags=tags or [],
                extra={"metadata": metadata or {}},
                project_name=self.project_name,
            )
            try:
                yield run_id  # 返回 run_id 字符串
            except Exception as e:
                self.client.update_run(run_id, error=str(e),
                                       end_time=datetime.now())
                raise
            finally:
                self.client.update_run(run_id, end_time=datetime.now())
        else:
            self.local_tracer = Tracer(name)
            span = self.local_tracer.start(name,
                                           json.dumps(inputs or {}, ensure_ascii=False))
            yield span

    def log_llm_call(self, run, name: str, messages: list,
                     response: str, duration_ms: float,
                     token_count: int = None, model: str = None):
        """
        记录单次 LLM 调用到 run 下。
        WHY: 在父 run 下创建子 run，形成 run tree——
             一个完整对话可以拆为多个 LLM 调用子 run。
        """
        if self.available and run:
            try:
                self.client.create_run(
                    name=name,
                    run_type="llm",
                    inputs={"messages": str(messages)[:500]},
                    outputs={"response": response[:500]},
                    parent_run_id=run,
                    start_time=time.time() - duration_ms / 1000,
                    end_time=time.time(),
                    extra={
                        "metadata": {
                            "model": model or "deepseek-chat",
                            "duration_ms": duration_ms,
                            "estimated_tokens": token_count or 0,
                        }
                    },
                    project_name=self.project_name,
                )
            except Exception:
                pass  # LangSmith 不可用时静默跳过
        elif self.local_tracer:
            span = self.local_tracer.start(name, str(messages)[:100])
            self.local_tracer.end(span, response[:100],
                                  type="llm_call", tokens=token_count or 0)

    def log_tool_call(self, run, tool_name: str, args: dict,
                      result: str, duration_ms: float):
        """记录工具调用"""
        if self.available and run:
            try:
                self.client.create_run(
                    name=f"tool:{tool_name}",
                    run_type="tool",
                    inputs=args,
                    outputs={"result": result[:500]},
                    parent_run_id=run,
                    extra={"metadata": {"duration_ms": duration_ms}},
                    project_name=self.project_name,
                )
            except Exception:
                pass
        elif self.local_tracer:
            span = self.local_tracer.start(f"tool:{tool_name}",
                                           json.dumps(args, ensure_ascii=False))
            self.local_tracer.end(span, result[:100], type="tool_call")

    def log_retrieval(self, run, query: str, docs: list[dict],
                      latency_ms: float):
        """记录 RAG 检索"""
        if self.available and run:
            try:
                self.client.create_run(
                    name="rag_retrieval",
                    run_type="retriever",
                    inputs={"query": query},
                    outputs={"documents": docs},
                    parent_run_id=run,
                    extra={"metadata": {"hit_count": len(docs),
                                        "latency_ms": latency_ms}},
                    project_name=self.project_name,
                )
            except Exception:
                pass

    # ─── Feedback ──────────────────────────────

    def create_feedback(self, run_id: str, score: float,
                        comment: str = "", key: str = "user_feedback"):
        """
        记录用户反馈。
        WHY: LangSmith 的 feedback 机制支持对 run 打分——
             可以在对话后收集用户满意度，关联到具体 run 做质量分析。
        """
        if self.available:
            try:
                self.client.create_feedback(
                    run_id=run_id,
                    key=key,
                    score=score,
                    comment=comment,
                )
            except Exception:
                pass

    # ─── Run 查询 ──────────────────────────────

    def list_runs(self, limit: int = 10, filter_str: str = None) -> list:
        """查询历史 run 记录"""
        if self.available:
            try:
                runs = self.client.list_runs(
                    project_name=self.project_name,
                    execution_order=1,  # 只取根 run
                )
                result = []
                for i, run in enumerate(runs):
                    if i >= limit:
                        break
                    result.append({
                        "id": str(run.id) if hasattr(run, 'id') else str(run),
                        "name": run.name,
                        "start_time": str(run.start_time),
                        "end_time": str(run.end_time) if run.end_time else "",
                        "error": run.error,
                        "tags": run.tags,
                    })
                return result
            except Exception:
                pass
        return []

    # ─── 统计 ──────────────────────────────────

    def get_stats(self, last_n_days: int = 7) -> dict:
        """获取项目统计摘要"""
        if self.available:
            try:
                runs = list(self.client.list_runs(
                    project_name=self.project_name,
                    execution_order=1,
                ))
                return {
                    "platform": "LangSmith Cloud",
                    "project": self.project_name,
                    "total_runs": len(runs),
                    "dashboard": f"https://smith.langchain.com/o/{os.getenv('LANGCHAIN_API_KEY', '')[:8]}.../projects/{self.project_name}",
                }
            except Exception as e:
                return {"platform": "LangSmith Cloud (已连接)", "note": str(e)[:100]}
        return {"platform": "Local", "note": "设置 LANGCHAIN_API_KEY 启用 LangSmith"}

    # ─── LangChain 自动回调 ─────────────────────

    @staticmethod
    def setup_langchain_callback():
        """
        配置 LangChain 自动追踪回调。
        WHY: 设置环境变量后，LangChain 的 LLM/Tool 调用会自动上报到
             LangSmith，不需要手动在每个地方加追踪代码。
        """
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if not os.environ.get("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = "agent-playground"


# ══════════════════════════════════════════════════════════════
# 便捷函数
# ══════════════════════════════════════════════════════════════

def is_langsmith_available() -> bool:
    return _get_ls_client() is not None


def create_tracer(project: str = "agent-playground") -> LangSmithTracer:
    return LangSmithTracer(project)
