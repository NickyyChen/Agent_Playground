# -*- coding: utf-8 -*-
"""
04_request_response.py — FastAPI 请求和响应
=============================================

【概念】请求和响应
FastAPI 处理 HTTP 请求时，提供了丰富的工具来读取请求数据和构造响应：

  请求数据来源：
  ┌──────────────────────────────────────────────┐
  │ 路径参数    /order/{order_id}                │  资源标识
  │ 查询参数    ?keyword=耳机&page=1             │  过滤/分页
  │ 请求体      POST body (JSON)                 │  创建/更新数据
  │ 请求头      Headers: Authorization, Cookie  │  身份/配置
  │ Cookie      Cookie: session_id=xxx           │  会话状态
  └──────────────────────────────────────────────┘

  响应控制：
  ┌──────────────────────────────────────────────┐
  │ 返回 dict      → FastAPI 自动序列化为 JSON   │
  │ Response()     → 手动控制状态码、响应头       │
  │ JSONResponse() → 自定义 JSON 的响应格式       │
  │ RedirectResponse → 重定向                    │
  └──────────────────────────────────────────────┘

【在智能客服中解决什么问题】
从请求中提取用户身份（Cookie/Header）、查询条件（查询参数）、
操作数据（请求体），然后返回合适的响应——这是每个 API 的基本流程。

【核心流程】

  客户端                          服务器
  ────────────────────────────────────────────
  POST /refund HTTP/1.1
  Host: api.haomai.com
  Authorization: Bearer token123          ← 请求头：认证
  Content-Type: application/json          ← 请求头：数据类型
  Cookie: session_id=abc                  ← Cookie：会话
                                           │
  {"order_id": "001", "reason": "质量问题"} ← 请求体
      │                                    │
      ▼                                    ▼
                               ┌────────────────────┐
                               │ FastAPI 自动解析：  │
                               │  Header  → 字典    │
                               │  Cookie  → 字典    │
                               │  Body    → Pydantic │
                               └────────────────────┘
                                    │
                                    ▼
                               返回 JSON 响应
                               {status: "ok"}

【测试案例】
  # 启动服务器
  python fastapi-basics/04_request_response.py

  # 路径参数 + 查询参数
  curl "http://localhost:8000/order/ORD001?include_logistics=true"
  # → 返回含物流信息的订单详情

  # POST 请求体（JSON）
  curl -X POST http://localhost:8000/refund \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","reason":"商品有划痕需要退货"}'
  # → {"status":"已受理","ticket_id":"TKT-NEW","order_id":"ORD001"}

  # 读取请求头
  curl http://localhost:8000/whoami \
    -H "User-Agent: Mozilla/5.0" \
    -H "Cookie: session_id=abc123"
  # → {"user_agent":"Mozilla/5.0","session_id":"abc123"}

  # 重定向（-L 跟随重定向）
  curl -L http://localhost:8000/old-api
  # → 自动跳转到 /order/001

  # 自定义 JSON 响应
  curl http://localhost:8000/custom-response
  # → {"message":"你好"} （响应头含 X-Custom-Header）

  # 原始请求调试
  curl -X POST http://localhost:8000/debug \
    -H "Content-Type: application/json" \
    -d '{"action":"test"}'
  # → 返回完整的请求信息（method/url/headers/body）

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from fastapi import FastAPI, Request, Header, Cookie
from fastapi.responses import JSONResponse, RedirectResponse, Response

app = FastAPI(title="好买电商客服 API - 请求与响应")


# ══════════════════════════════════════════════════════════════
# 1. 读取路径参数 + 查询参数（最常用）
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(order_id: str, include_logistics: bool = False):
    """
    查询订单。
    order_id: 路径参数，必填
    include_logistics: 查询参数，可选（默认 False）
    """
    result = {"order_id": order_id, "product": "蓝牙耳机", "status": "已发货"}
    if include_logistics:
        result["logistics"] = {"company": "顺丰快递", "tracking": "SF123456789"}
    return result


# ══════════════════════════════════════════════════════════════
# 2. 从请求体读取数据（POST/PUT）
# ══════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field

# WHY: Pydantic 模型定义请求体结构——FastAPI 自动校验 JSON 数据
class RefundBody(BaseModel):
    order_id: str = Field(..., description="订单号")
    reason: str = Field(..., min_length=5, description="退款原因，至少5个字")


@app.post("/refund")
def create_refund(body: RefundBody):
    """body 参数自动从请求体 JSON 解析并校验。"""
    return {"status": "已受理", "ticket_id": "TKT-NEW", "order_id": body.order_id}


# ══════════════════════════════════════════════════════════════
# 3. 读取请求头
# ══════════════════════════════════════════════════════════════

@app.get("/whoami")
def whoami(
    user_agent: str = Header(None),
    # WHY: Header(None) 从请求头读取 User-Agent 字段，None 表示可选
    session_id: str = Cookie(None),
    # WHY: Cookie(None) 从 Cookie 中读取 session_id，None 表示可选
):
    """读取请求头中的 User-Agent 和 Cookie。"""
    return {"user_agent": user_agent, "session_id": session_id}


# ══════════════════════════════════════════════════════════════
# 4. 自定义响应
# ══════════════════════════════════════════════════════════════

@app.get("/old-api")
def redirect_to_new():
    """
    WHY: RedirectResponse 让旧接口 301 跳转到新地址——
         客户端无需修改代码，服务器自动引导。
    """
    return RedirectResponse(url="/order/001")


@app.get("/custom-response")
def custom_response():
    """
    WHY: JSONResponse 可以手动设置响应状态码和响应头——
         比如设置自定义 Header 或 CORS 头。
    """
    content = {"message": "你好"}
    return JSONResponse(
        content=content,
        status_code=200,
        headers={"X-Custom-Header": "fastapi-demo"},
    )


# ══════════════════════════════════════════════════════════════
# 5. 原始 Request 对象——获取所有请求信息
# ══════════════════════════════════════════════════════════════

@app.post("/debug")
async def debug_request(request: Request):
    """
    WHY: Request 对象提供最底层的请求信息——
         URL、方法、原始 Headers、客户端 IP 等。
         用于日志记录、调试、风控分析。
    """
    body = await request.json()  # WHY: await——FastAPI 支持异步，Request.json() 是异步方法
    return {
        "method": request.method,
        "url": str(request.url),
        "client_host": request.client.host,
        "headers": dict(request.headers),
        "body": body,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
