# -*- coding: utf-8 -*-
"""
FastAPI 路由 —— 知识点: FastAPI 全栈 (路由/模型/DI/中间件)
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ─── 请求/响应模型 (Demo 02 + FastAPI Pydantic) ────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    mode: str = Field(default="react", description="react / plan / reflect / orchestrate")

class ChatResponse(BaseModel):
    reply: str
    mode: str
    trace: dict = Field(default_factory=dict)
    cache_stats: dict = Field(default_factory=dict)


# ─── 创建 App ─────────────────────────────────────

def create_app(agent_system):
    """创建 FastAPI 应用，注入 agent_system"""
    app = FastAPI(title="好买电商智能客服系统",
                  description="Agent-Playground 知识点集成工程",
                  version="2.0.0")

    # CORS
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    # ─── 日志中间件 ──────────────────────────
    @app.middleware("http")
    async def log_middleware(request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        print(f"[{response.status_code}] {request.method} "
              f"{request.url.path} — {duration:.0f}ms")
        response.headers["X-Process-Time-ms"] = str(int(duration))
        return response

    # ─── 路由 ────────────────────────────────

    @app.get("/")
    def root():
        return {"service": "好买电商智能客服", "version": "2.0",
                "endpoints": ["/chat", "/health", "/stats"]}

    @app.post("/chat", response_model=ChatResponse)
    def chat(req: ChatRequest):
        """
        核心对话接口。
        知识点:
          Demo 06/07/08/11 — Agent 工作模式
          Demo 03/04/05 — 工具+记忆+RAG
          Demo 13 — 安全护栏
          Demo 14 — 追踪
          Demo 19 — 模型路由
          Demo 20 — 缓存
        """
        # 安全护栏 (Demo 13)
        blocked = agent_system.safety.pipeline(req.message)
        if blocked:
            return ChatResponse(reply=blocked, mode="blocked",
                                trace={}, cache_stats={})

        # 执行 Agent (Demo 06/07/08/11)
        trace = {}
        if req.mode == "plan":
            result = agent_system.run_plan_execute(req.message)
            reply = result["answer"]
        elif req.mode == "reflect":
            result = agent_system.run_reflection(req.message)
            reply = result["final"]
        elif req.mode == "orchestrate":
            result = agent_system.run_orchestrator(req.message)
            reply = result.get("final_response", "")
        else:  # react (default)
            reply, react_trace = agent_system.run_react(req.message)
            trace["react_steps"] = react_trace

        # 输出护栏
        blocked = agent_system.safety.pipeline(req.message, agent_reply=reply)
        if blocked and "[输出护栏]" in blocked:
            reply = blocked

        return ChatResponse(
            reply=reply, mode=req.mode,
            trace=trace,
            cache_stats=agent_system.llm.cache_stats,
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/stats")
    def stats():
        return {
            "llm_cache": agent_system.llm.cache_stats,
            "safety": agent_system.safety.stats,
            "memory_size": len(agent_system.memory.short_term),
        }

    return app
