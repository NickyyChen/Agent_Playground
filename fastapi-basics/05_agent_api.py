# -*- coding: utf-8 -*-
"""
05_agent_api.py — 综合：客服 Agent 的 FastAPI 接口
=================================================

【概念】
把前面 4 个 demo 学到的知识组合成一个可用的客服 Agent API：
  - 路由 + 参数校验（01）
  - Pydantic 请求/响应模型（02）
  - 依赖注入——鉴权 + Agent 服务（03）
  - 中间件——日志（04）

最终产物：一个对外提供客服对话 + 订单查询 + 退货申请的 REST API。

【在智能客服中的应用】
这是 Agent Demo（如 03_function_calling）的"产品化封装"——
内部分析 Agent 处理，对外暴露标准 REST API 供前端/第三方调用。

【pip install】
pip install fastapi uvicorn openai

【ASCII 架构图】

  ┌──────────────────────────────────────────────────────┐
  │                 客服 Agent API                        │
  │                                                       │
  │  客户端 (Web/App/第三方)                                │
  │     │                                                 │
  │     ▼                                                 │
  │  ┌──────────────────────────────────────────┐        │
  │  │  FastAPI 层                               │        │
  │  │  - 鉴权 (Depends)                         │        │
  │  │  - 参数校验 (Pydantic)                     │        │
  │  │  - 日志 (Middleware)                      │        │
  │  └──────────────┬───────────────────────────┘        │
  │                 ▼                                     │
  │  ┌──────────────────────────────────────────┐        │
  │  │  Agent 层                                 │        │
  │  │  - 意图分析 → 调工具 → 生成回答            │        │
  │  │  (复用 demos/03 + demos/06 的 Agent 逻辑)  │        │
  │  └──────────────────────────────────────────┘        │
  └──────────────────────────────────────────────────────┘
"""

import sys, os, json, uvicorn, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

from shared.llm_client import chat
from shared.mock_data import MOCK_ORDERS, MOCK_LOGISTICS, RETURN_POLICY


app = FastAPI(
    title="好买电商智能客服 API",
    description="Agent-Playground 综合学习 Demo",
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════
# 中间件：全局日志
# ══════════════════════════════════════════════════════════════

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    print(f"[{response.status_code}] {request.method} {request.url.path} "
          f"— {duration:.0f}ms")
    response.headers["X-Process-Time-ms"] = str(int(duration))
    return response


# ══════════════════════════════════════════════════════════════
# Pydantic 模型
# ══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """客服对话请求"""
    message: str = Field(..., min_length=1, max_length=500, description="用户消息")

class ChatResponse(BaseModel):
    """客服对话响应"""
    reply: str
    intent: Optional[str] = None
    order_info: Optional[dict] = None

class RefundApply(BaseModel):
    """退货申请请求"""
    order_id: str = Field(..., min_length=5, description="订单号")
    reason: str = Field(..., min_length=5, max_length=200, description="退货原因")


# ══════════════════════════════════════════════════════════════
# 鉴权依赖
# ══════════════════════════════════════════════════════════════

TOKENS = {
    "demo-token": {"user_id": "U1", "name": "测试用户"},
}

def authenticate(authorization: str = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(401, "请提供 Authorization Header")
    token = authorization.replace("Bearer ", "")
    user = TOKENS.get(token)
    if not user:
        raise HTTPException(403, "Token 无效")
    return user


# ══════════════════════════════════════════════════════════════
# Agent 核心逻辑 —— 简单的意图路由 + 工具调用
# WHY: 这里的 Agent 是 Demo 03 中 Function Calling 的"产品化版本"——
#      同样的逻辑（查订单、查政策），包装成可调用的服务函数。
# ══════════════════════════════════════════════════════════════

def analyze_and_respond(user_message: str) -> dict:
    """
    分析用户消息并返回回答 + 可能的订单信息。
    """
    # 用 LLM 判断是否涉及订单号
    intent_check = chat([
        {"role": "system",
         "content": "判断用户消息是否包含订单号（格式 ORD...）。"
                    "如果包含，提取订单号。输出 JSON: "
                    '{"has_order": bool, "order_id": "xxx或null"}'},
        {"role": "user", "content": user_message},
    ], temperature=0, max_tokens=50)

    result = {"intent": "general"}
    order_info = None

    try:
        parsed = json.loads(intent_check)
    except json.JSONDecodeError:
        parsed = {"has_order": False, "order_id": None}

    # 如果涉及订单号 → 自动查订单
    if parsed.get("has_order") and parsed.get("order_id"):
        oid = parsed["order_id"]
        order = MOCK_ORDERS.get(oid)
        if order:
            result["intent"] = "order_query"
            order_info = order

    # 生成客服回复
    system = "你是小选，好买电商客服。回答简洁专业，不超过3句话。"

    if order_info:
        system += f"\n\n当前订单信息: {json.dumps(order_info, ensure_ascii=False)}"
    if "退货" in user_message or "退款" in user_message:
        system += f"\n\n退换货政策: {RETURN_POLICY[:200]}"

    reply = chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ])

    return {"reply": reply, "intent": result["intent"], "order_info": order_info}


# ══════════════════════════════════════════════════════════════
# API 端点
# ══════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {"service": "好买电商智能客服 API", "version": "1.0"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest, user: dict = Depends(authenticate)):
    """
    客服对话接口 —— POST /chat
    需要鉴权: Authorization: Bearer demo-token
    请求体: {"message": "查一下订单ORD20240001"}

    WHY: Depends(authenticate) 自动从 Header 提取 Token 并验证，
         Pydantic 自动校验请求体——函数内直接写业务逻辑。
    """
    result = analyze_and_respond(req.message)

    return ChatResponse(
        reply=result["reply"],
        intent=result["intent"],
        order_info=result.get("order_info"),
    )


@app.post("/refund")
def refund_endpoint(req: RefundApply, user: dict = Depends(authenticate)):
    """退货申请接口 —— POST /refund"""
    order = MOCK_ORDERS.get(req.order_id)
    if not order:
        raise HTTPException(404, f"订单 {req.order_id} 不存在")

    # 简单校验：已签收的订单才能申请退货
    if order["status"] != "已签收":
        raise HTTPException(400, f"订单状态为'{order['status']}'，不可退货")

    return {
        "status": "submitted",
        "ticket_id": f"RFD-{req.order_id}",
        "order": order,
        "reason": req.reason,
    }


@app.get("/order/{order_id}")
def query_order_endpoint(
    order_id: str,
    user: dict = Depends(authenticate)
):
    """订单查询接口 —— GET /order/{order_id}"""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        raise HTTPException(404, f"订单 {order_id} 不存在")
    return {"order": order}


@app.get("/health")
def health():
    """健康检查——不需要鉴权"""
    return {"status": "ok"}


class ErrorResponse(BaseModel):
    error: str
    message: str


@app.get("/openapi.json")
async def get_openapi():
    """返回 OpenAPI Schema"""
    return app.openapi()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8004, log_level="info")
