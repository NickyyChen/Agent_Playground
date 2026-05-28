# -*- coding: utf-8 -*-
"""
21_middleware.py — FastAPI 中间件
====================================

【概念】什么是中间件？
中间件是在**每个请求**被路由处理之前和之后执行的函数——横切面（cross-cutting）。
它像一个洋葱：请求从外到内穿过各层中间件，响应从内到外返回。

  请求 →
  ┌────────────────────────────────────────────┐
  │  中间件1 (如 CORS)          ← 最外层        │
  │  ┌──────────────────────────────────────┐  │
  │  │ 中间件2 (如日志)                      │  │
  │  │ ┌────────────────────────────────┐   │  │
  │  │ │ 中间件3 (如限流)                │   │  │
  │  │ │ ┌──────────────────────┐       │   │  │
  │  │ │ │  路由处理 (业务逻辑)   │       │   │  │
  │  │ │ └──────────────────────┘       │   │  │
  │  │ └────────────────────────────────┘   │  │
  │  └──────────────────────────────────────┘  │
  └────────────────────────────────────────────┘
  响应 ←

【在智能客服中解决什么问题】
  - 全链路日志记录（每个请求耗时、状态码）
  - 请求限流（防止恶意刷接口）
  - 统一的异常捕获
  - 请求/响应的数据脱敏

【测试案例】
  # 启动服务器（观察控制台——每个请求自动输出日志）
  python fastapi-basics/21_middleware.py

  # 正常请求——观察响应头 X-Process-Time-ms 和 X-Request-ID
  curl -i http://localhost:8000/order/ORD001
  # → 响应头含 X-Process-Time-ms 和 X-Request-ID，控制台打印请求日志

  # 工单列表
  curl http://localhost:8000/tickets
  # → 同样自动记录日志 + 耗时

  # 健康检查（中间件同样记录）
  curl http://localhost:8000/health

  # 测试限流——快速发送 35 次请求（超过 30 次/分钟的限流阈值）
  for i in $(seq 1 35); do
    curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/order/ORD001
  done
  # → 前 30 次返回 200，第 31-35 次返回 429 Too Many Requests

【pip install】
pip install fastapi uvicorn
"""

import time
import uvicorn
from typing import Optional, Dict
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


app = FastAPI(title="好买电商客服 API - 中间件")


# ══════════════════════════════════════════════════════════════
# 1. @app.middleware 基础中间件——请求日志
# ══════════════════════════════════════════════════════════════

# WHY: @app.middleware 是最简单的中间件定义方式
#      每个请求都会经过这个函数
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    记录每个请求的日志——方法、路径、耗时、状态码。
    WHY: 全链路日志是最常用的中间件——监控、排错、性能分析都依赖它。
    call_next 是调用下一个中间件（或最终路由）的函数。
    """
    start_time = time.time()

    # WHY: call_next(request) 调用下一个中间件/路由——
    #      必须 await，因为中间件链是异步的
    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000
    print(
        f"[{time.strftime('%H:%M:%S')}] "
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"({duration_ms:.1f}ms)"
    )

    # WHY: 在响应头中添加处理耗时，方便客户端调试
    response.headers["X-Process-Time-ms"] = f"{duration_ms:.1f}"
    return response


# ══════════════════════════════════════════════════════════════
# 2. BaseHTTPMiddleware 类方式中间件——简易限流器
# ══════════════════════════════════════════════════════════════

# WHY: 继承 BaseHTTPMiddleware 实现更复杂的中间件逻辑
#      dispatch 方法在每个请求时调用
class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    简易请求限流中间件。
    WHY: 按客户端 IP 限流——防止单个用户刷接口。
         实际项目用 Redis 做分布式限流。
    """

    def __init__(self, app: ASGIApp, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests  # 时间窗口内最大请求数
        self.window_seconds = window_seconds
        # WHY: defaultdict 自动为不存在的 key 创建空列表
        self.requests: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        # WHY: 清理过期的时间戳——滑动窗口算法
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < self.window_seconds
        ]

        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"请求过于频繁，请 {self.window_seconds} 秒后重试",
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response


# WHY: add_middleware 添加中间件——可以传额外参数
app.add_middleware(RateLimitMiddleware, max_requests=30, window_seconds=60)


# ══════════════════════════════════════════════════════════════
# 3. 中间件——添加请求 ID 追踪
# ══════════════════════════════════════════════════════════════

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """
    为每个请求添加唯一追踪 ID。
    WHY: request_id 关联所有日志——当用户反馈问题时，
         用 request_id 可以快速定位到具体请求和全链路日志。
    """
    import uuid

    # WHY: 优先用客户端传的 X-Request-ID，否则自动生成
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ══════════════════════════════════════════════════════════════
# 4. 路由
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(order_id: str, request: Request):
    """
    查询订单——展示 request.state 传递的 request_id。
    """
    request_id = getattr(request.state, "request_id", "unknown")
    return {
        "order_id": order_id,
        "product": "蓝牙耳机",
        "trace_id": request_id,
    }


@app.get("/tickets")
def list_tickets():
    """查询工单列表——中间件自动记录日志和耗时。"""
    return {
        "items": [
            {"id": "TKT-001", "title": "蓝牙耳机杂音", "status": "处理中"},
            {"id": "TKT-002", "title": "物流未更新", "status": "待分配"},
        ]
    }


@app.get("/health")
def health():
    """健康检查——中间件也记录这个请求。"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
