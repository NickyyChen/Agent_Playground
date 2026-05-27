# -*- coding: utf-8 -*-
"""
04_middleware.py — 中间件与异常处理
===================================

【概念】
中间件（Middleware）在请求-响应链路中拦截所有请求，做横切面处理：
  请求 → [Middleware 1] → [Middleware 2] → 路由处理 → [Middleware 2] → [Middleware 1] → 响应

常用场景：
  - 全局日志：记录每个请求的耗时、状态码
  - 请求限流：同一 IP 每秒最多 N 次
  - CORS 处理：允许前端跨域访问
  - 全局异常捕获：未处理的异常统一返回友好 JSON

【在智能客服中的应用】
- 每个 API 调用自动打日志（请求时间、用户、延迟）
- 异常发生时返回结构化错误而非 HTML 堆栈
- 限流保护（防止单个用户刷 API）

【pip install】
pip install fastapi uvicorn

【ASCII 架构图】

  请求进入
     │
     ▼
  ┌──────────────────────┐
  │  Middleware: 日志      │  ← 记录请求开始时间
  │  (request.state.start)│
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │  Middleware: 限流      │  ← 检查 IP 频率
  │  (rate_limiter)       │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │  路由处理函数           │  ← 业务逻辑
  │  (可能抛异常)           │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │  Exception Handler    │  ← 统一捕获异常, 返回友好 JSON
  │  @app.exception_handler│
  └──────────┬───────────┘
             ▼
        JSON 响应
"""

import uvicorn, time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="中间件与异常处理学习")


# ══════════════════════════════════════════════════════════════
# 1. 日志中间件 —— 记录每个请求的耗时
# WHY: @app.middleware("http") 是 FastAPI 的标准中间件接口——
#      每个请求都会经过这里，可以拿到 request 和 response。
#      call_next() 调用下一个中间件/路由，前后可以插入逻辑。
# ══════════════════════════════════════════════════════════════

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    """
    记录每个请求的方法、路径、状态码和耗时。
    WHY: 中间件是唯一能看到"请求前+请求后"的地方——
         可以在 call_next 前记录开始时间，
         在 call_next 后拿到响应状态码和计算耗时。
    """
    start = time.time()
    # WHY: call_next(request) 是把请求传递给下一个中间件/路由，
    #      返回的是 Response 对象
    response = await call_next(request)
    duration = (time.time() - start) * 1000

    # 生产环境这里应该输出到日志系统（如 loguru/structlog）
    print(f"[{response.status_code}] {request.method} {request.url.path} "
          f"— {duration:.0f}ms")

    # WHY: 在响应头中加自定义字段——前端可以拿到计时代码
    response.headers["X-Process-Time-ms"] = str(int(duration))
    return response


# ══════════════════════════════════════════════════════════════
# 2. 模拟限流中间件
# WHY: 中间件可以提前返回（不调 call_next），直接拦截请求。
#      限流就是在 call_next 之前判断是否超频——超了就返回 429。
# ══════════════════════════════════════════════════════════════

# 简单内存限流: IP → (计数器, 窗口开始时间)
_rate_limits: dict[str, tuple[int, float]] = {}
RATE_LIMIT = 3     # 每窗口最多 3 次
RATE_WINDOW = 10   # 窗口 10 秒

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    count, window_start = _rate_limits.get(client_ip, (0, now))

    # WHY: 窗口过期 → 重置计数器
    if now - window_start > RATE_WINDOW:
        count, window_start = 0, now

    if count >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": f"请求太频繁，{RATE_WINDOW}秒内最多{RATE_LIMIT}次"}
        )

    _rate_limits[client_ip] = (count + 1, window_start)
    return await call_next(request)


# ══════════════════════════════════════════════════════════════
# 3. 全局异常处理器
# WHY: 未捕获的异常默认返回 HTML 堆栈页——JSON API 不应该这样。
#      @app.exception_handler 统一捕获，返回结构化错误。
#      HTTPException 也能被自定义处理器接管。
# ══════════════════════════════════════════════════════════════

class BusinessError(Exception):
    """自定义业务异常——客服系统中用于区分错误类型"""
    def __init__(self, message: str, error_code: str = "BUSINESS_ERROR"):
        self.message = message
        self.error_code = error_code


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """
    统一处理业务异常。
    WHY: 不在这里处理，每个路由都要 try/except 然后返回错误 JSON——
         全局 handler 让业务代码直接 raise，框架层统一处理。
    """
    return JSONResponse(
        status_code=400,
        content={"error": exc.error_code, "message": exc.message}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """
    兜底处理器——所有未预期的异常。
    WHY: 用户不应看到 Python 堆栈——返回友好的通用错误信息。
         生产环境应同时将堆栈发到 Sentry/日志系统。
    """
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "服务器内部错误，请稍后重试"}
    )


# ══════════════════════════════════════════════════════════════
# 测试路由
# ══════════════════════════════════════════════════════════════

@app.get("/hello")
def hello():
    return {"message": "你好"}


@app.get("/refund/{order_id}")
def refund(order_id: str):
    """
    演示业务异常：订单已完成时申请退款 → 抛 BusinessError。
    """
    if order_id == "ORD-DONE":
        # WHY: 直接 raise，不用 return 错误 JSON——
        #      全局 handler 自动处理
        raise BusinessError(
            message="该订单已完成，不可退款",
            error_code="ORDER_ALREADY_COMPLETED"
        )
    return {"status": "退款申请已提交", "order_id": order_id}


@app.get("/crash")
def crash():
    """
    演示 500 异常：除以零 → 被全局 handler 捕获 → 返回友好 JSON。
    """
    # 这会触发 ZeroDivisionError → 被 internal_error_handler 捕获
    1 / 0
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")
