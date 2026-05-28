# -*- coding: utf-8 -*-
"""
19_headers_cookies.py — FastAPI 请求头与 Cookie
==================================================

【概念】请求头和 Cookie
HTTP 请求除了 URL 和 Body，还有两个隐藏的数据通道：

  请求头 (Headers)：
  ┌──────────────────────────────────────────────┐
  │ 作用：传递请求的元信息                         │
  │ 常见请求头：                                  │
  │   Authorization: Bearer <token>  → 认证      │
  │   Content-Type: application/json   → 数据类型  │
  │   User-Agent: Chrome/120           → 客户端信息 │
  │   X-Request-ID: abc-123            → 请求追踪  │
  │   Accept-Language: zh-CN           → 语言偏好  │
  └──────────────────────────────────────────────┘

  Cookie：
  ┌──────────────────────────────────────────────┐
  │ 作用：在浏览器端存储小块数据，每次请求自动携带    │
  │ 常见用途：                                    │
  │   session_id → 会话保持（登录状态）             │
  │   csrf_token → 安全防护                       │
  │   user_pref  → 用户偏好（语言、主题）           │
  └──────────────────────────────────────────────┘

【在智能客服中解决什么问题】
  - Authorization 头传递客服的登录 token
  - Cookie 保持客服后台的会话状态
  - X-Request-ID 实现全链路追踪（定位问题）
  - User-Agent 判断是 App 还是网页端

【核心流程】

  HTTP 请求
  ┌─────────────────────────────────────────────┐
  │ GET /tickets HTTP/1.1                       │
  │ Host: api.haomai.com                        │
  │ Authorization: Bearer eyJhbGciOi...          │  ← 请求头
  │ Cookie: session_id=abc123; theme=dark        │  ← Cookie
  │ User-Agent: Mozilla/5.0 ...                 │  ← 请求头
  │ Accept-Language: zh-CN                      │  ← 请求头
  └─────────────────────────────────────────────┘
      │
      ▼
  FastAPI:
    Header("Authorization")  →  "Bearer eyJhbGciOi..."
    Cookie("session_id")     →  "abc123"

  响应：服务器也可以设置 Cookie 和响应头
  ┌─────────────────────────────────────────────┐
  │ Set-Cookie: session_id=new-xyz; HttpOnly     │  ← 设置 Cookie
  │ X-Response-Time: 23ms                       │  ← 自定义响应头
  └─────────────────────────────────────────────┘

【测试案例】
  # 启动服务器
  python fastapi-basics/19_headers_cookies.py

  # 读取请求头——查看客户端信息
  curl http://localhost:8000/whoami \
    -H "User-Agent: Mozilla/5.0" \
    -H "Accept-Language: zh-CN" \
    -H "X-Request-ID: trace-abc123"
  # → {"client":{"user_agent":"Mozilla/5.0","language":"zh-CN"},"trace":{"request_id":"trace-abc123"}}

  # Bearer Token 认证——客服查看个人信息
  curl http://localhost:8000/profile \
    -H "Authorization: Bearer token-admin-001"
  # → {"message":"你好 张经理","profile":{"name":"张经理","role":"admin"}}

  # 无 token → 401
  curl http://localhost:8000/profile
  # → 401

  # Cookie 会话读取
  curl http://localhost:8000/session \
    -H "Cookie: session_id=sess-abc123"
  # → {"session_id":"sess-abc123","user":"张经理",...}

  # 登录——服务器设置 Cookie（观察 Set-Cookie 响应头和 X-Login-Time）
  curl -i -X POST "http://localhost:8000/login?username=张经理"
  # → 响应含 Set-Cookie 头和 X-Login-Time/X-User-Name 自定义头

  # 登出——删除 Cookie
  curl -i -X POST http://localhost:8000/logout \
    -H "Cookie: session_id=sess-abc123"
  # → 响应含 Set-Cookie 将 session_id 设为过期

  # 分页信息在响应头中
  curl -i http://localhost:8000/tickets
  # → 响应头含 X-Total-Count: 156, X-Total-Pages: 8

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, Header, Cookie, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="好买电商客服 API - 请求头与 Cookie")


# ══════════════════════════════════════════════════════════════
# 1. 读取标准请求头
# ══════════════════════════════════════════════════════════════

@app.get("/whoami")
def whoami(
    # WHY: Header(None) 读取请求头——None 表示可选（不传时为 None）
    user_agent: Optional[str] = Header(None, description="客户端信息"),
    # WHY: FastAPI 自动将 Header 名中的下划线转连字符
    #      accept_language → Accept-Language（HTTP 标准命名）
    accept_language: Optional[str] = Header(None, description="语言偏好"),
    # WHY: convert_underscores=False 禁用自动转换
    #      这样 Python 变量名 = 请求头原名
    x_request_id: Optional[str] = Header(
        None, convert_underscores=True, description="请求追踪 ID"
    ),
):
    """
    查看"我是谁"——读取客户端发来的请求头。
    WHY: User-Agent 能判断客户端类型（App/Web/Postman），
         Accept-Language 决定返回中文还是英文。
    """
    return {
        "client": {"user_agent": user_agent, "language": accept_language},
        "trace": {"request_id": x_request_id},
    }


# ══════════════════════════════════════════════════════════════
# 2. 从 Header 中认证
# ══════════════════════════════════════════════════════════════

fake_tokens = {
    "token-admin-001": {"name": "张经理", "role": "admin"},
    "token-agent-002": {"name": "李客服", "role": "agent"},
}


@app.get("/profile")
def get_profile(
    # WHY: 从 Authorization 头提取 token——这是 JWT 认证的标准做法
    authorization: Optional[str] = Header(None, description="Bearer <token>"),
):
    """
    获取当前客服的个人信息——通过 Authorization 头认证。
    WHY: 请求头是携带 token 的最佳位置——不会缓存、不会被 URL 泄露。
    """
    if not authorization:
        return JSONResponse(
            status_code=401,
            content={"error": "请提供 Authorization 请求头"},
        )

    token = authorization.replace("Bearer ", "")
    user = fake_tokens.get(token)

    if not user:
        return JSONResponse(
            status_code=401,
            content={"error": "无效的 token"},
        )

    return {"message": f"你好 {user['name']}", "profile": user}


# ══════════════════════════════════════════════════════════════
# 3. Cookie 读取与会话管理
# ══════════════════════════════════════════════════════════════

# 模拟会话存储
fake_sessions = {
    "sess-abc123": {"user": "张经理", "login_time": "2024-01-20 09:00", "cart_items": 3},
    "sess-def456": {"user": "王小明", "login_time": "2024-01-20 10:30", "cart_items": 1},
}


@app.get("/session")
def get_session_info(
    # WHY: Cookie(...) 读取 Cookie——... 表示必填（未登录无法使用）
    session_id: str = Cookie(..., description="会话 ID"),
):
    """
    读取会话信息——通过 Cookie 获取当前会话。
    WHY: Cookie 自动携带，不需要前端手动设置请求头——适合 Web 页面。
    """
    session = fake_sessions.get(session_id)
    if not session:
        return JSONResponse(
            status_code=401,
            content={"error": "会话过期或无效，请重新登录"},
        )
    return {"session_id": session_id, **session}


# ══════════════════════════════════════════════════════════════
# 4. 设置 Cookie 和响应头
# ══════════════════════════════════════════════════════════════

@app.post("/login")
def login(username: str, response: Response):
    """
    登录——设置 Cookie 和响应头。
    WHY: 服务器通过 Set-Cookie 告诉浏览器"记住这个 session_id"。
         浏览器后续请求自动带上这个 Cookie。
    """
    # WHY: 模拟创建会话——实际项目生成随机 session_id 并存入 Redis
    new_session = f"sess-{username}-{datetime.now().timestamp():.0f}"

    # WHY: set_cookie() 设置浏览器端的 Cookie
    #      httponly=True → JS 无法读取（防 XSS 攻击）
    #      max_age=3600 → 1 小时后过期
    response.set_cookie(
        key="session_id",
        value=new_session,
        httponly=True,
        max_age=3600,
        samesite="lax",
    )

    # WHY: 设置自定义响应头
    response.headers["X-Login-Time"] = datetime.now().isoformat()
    response.headers["X-User-Name"] = username

    return {"message": f"登录成功，欢迎 {username}", "session_id": new_session}


# ══════════════════════════════════════════════════════════════
# 5. 删除 Cookie（登出）
# ══════════════════════════════════════════════════════════════

@app.post("/logout")
def logout(response: Response, session_id: Optional[str] = Cookie(None)):
    """
    登出——删除 Cookie。
    WHY: 设置 max_age=0 让浏览器删除 Cookie。
    """
    response.delete_cookie(key="session_id")
    return {"message": "已登出", "was_session": session_id}


# ══════════════════════════════════════════════════════════════
# 6. 通过 Response 参数设置响应头（另一种方式）
# ══════════════════════════════════════════════════════════════

@app.get("/tickets")
def list_tickets(response: Response):
    """
    查询工单列表——在响应头中返回分页信息。
    WHY: 分页信息放在响应头比放在 Body 中更 RESTful。
    """
    response.headers["X-Total-Count"] = "156"
    response.headers["X-Total-Pages"] = "8"
    response.headers["X-Current-Page"] = "1"

    return {
        "items": [
            {"id": "TKT-001", "title": "蓝牙耳机杂音", "status": "处理中"},
            {"id": "TKT-002", "title": "订单未收到", "status": "待分配"},
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
