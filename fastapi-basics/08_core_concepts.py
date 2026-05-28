# -*- coding: utf-8 -*-
"""
08_core_concepts.py — FastAPI 核心概念
========================================

【概念】FastAPI 核心概念一览
本篇汇总 FastAPI 中最核心的几个概念，帮你建立全局认知：

  1. ASGI 应用     →  FastAPI 底层基于 Starlette（ASGI 框架）
  2. 路径操作装饰器 →  @app.get/post/put/delete/patch/options/head/trace
  3. 路径参数       →  /resource/{id}
  4. 查询参数       →  ?key=value&key2=value2
  5. 请求体         →  POST/PUT 的 JSON body
  6. 依赖注入       →  Depends() 复用公共逻辑
  7. 中间件         →  请求前/后的横切逻辑（日志、CORS）
  8. 后台任务       →  BackgroundTasks 异步执行耗时操作
  9. 事件处理       →  startup/shutdown 生命周期事件
  10. 异常处理      →  HTTPException + 自定义异常处理器

【在智能客服中解决什么问题】
这些核心概念组合起来，构成完整的智能客服 API 系统：
  用户请求 → 中间件(日志/限流) → 路由 → 依赖(认证/权限) → 业务逻辑 → 响应

【测试案例】
  # 启动服务器（观察控制台输出的生命周期日志）
  python fastapi-basics/08_core_concepts.py

  # 健康检查
  curl http://localhost:8000/health
  # → {"status":"healthy","service":"智能客服 API"}

  # 应用信息
  curl http://localhost:8000/info
  # → {"title":"好买电商客服 API - 核心概念","version":"0.1.0",...}

  # 创建退款（后台异步发邮件——观察控制台 2 秒后的日志）
  curl -X POST "http://localhost:8000/refund?order_id=ORD001&reason=质量问题"
  # → {"message":"退款申请已提交","ticket_id":"TKT-ORD001"}
  #   （响应立即返回，后台任务异步执行）

  # 查询工单——需要 token
  curl "http://localhost:8000/ticket/TKT-001?token=agent-token&include_logs=true"
  # → {"ticket_id":"TKT-001","operator":{"name":"客服小李","role":"agent"},"status":"处理中","logs":[...]}

  # 无 token → 401（统一异常格式化响应）
  curl http://localhost:8000/ticket/TKT-001
  # → {"error":true,"code":401,"message":"请先登录","path":"/ticket/TKT-001"}

【pip install】
pip install fastapi uvicorn
"""

import time
import uvicorn
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse


# ══════════════════════════════════════════════════════════════
# 1. 生命周期事件（startup / shutdown）
# ══════════════════════════════════════════════════════════════

# WHY: @asynccontextmanager 定义应用启动和关闭时的钩子函数
#      startup → 初始化数据库连接池、加载模型
#      shutdown → 关闭连接、清理资源
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print("🚀 智能客服 API 启动中...")
    print("   - 连接数据库...")
    print("   - 加载知识库...")
    print("   - 预热模型缓存...")
    yield  # ← 应用运行期间
    # 关闭时执行
    print("🛑 智能客服 API 关闭中...")
    print("   - 关闭数据库连接...")
    print("   - 保存日志...")


# WHY: lifespan 参数传入 FastAPI，替代已废弃的 on_event 装饰器
app = FastAPI(
    title="好买电商客服 API - 核心概念",
    lifespan=lifespan,
)


# ══════════════════════════════════════════════════════════════
# 2. 后台任务
# ══════════════════════════════════════════════════════════════

# WHY: 发邮件/发通知等耗时操作不应阻塞 HTTP 响应
#      BackgroundTasks 让它们在响应返回后异步执行
def send_email_notification(email: str, message: str):
    """模拟发送邮件（实际项目中连接 SMTP 服务器）。"""
    time.sleep(2)  # 模拟耗时
    print(f"📧 邮件已发送至 {email}: {message}")


def log_to_file(data: str):
    """模拟写入日志文件。"""
    print(f"📝 日志已记录: {data}")


@app.post("/refund")
async def create_refund(
    order_id: str,
    reason: str,
    background_tasks: BackgroundTasks,
    # WHY: 在函数签名中声明 BackgroundTasks，FastAPI 自动注入
):
    """创建退款申请——之后异步发送通知邮件。"""
    background_tasks.add_task(
        send_email_notification,
        "customer@example.com",
        f"退款申请已受理，工单号 TKT-{order_id}",
    )
    background_tasks.add_task(log_to_file, f"退款: {order_id}, 原因: {reason}")

    return {"message": "退款申请已提交", "ticket_id": f"TKT-{order_id}"}


# ══════════════════════════════════════════════════════════════
# 3. 异常处理
# ══════════════════════════════════════════════════════════════

# WHY: 自定义异常处理器——统一错误响应格式
#      所有 HTTPException 都会被这里拦截并格式化
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一格式化 HTTP 异常响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


# WHY: 捕获所有未预料的异常，避免暴露内部细节
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """兜底异常处理——避免 500 错误暴露内部信息。"""
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
        },
    )


# ══════════════════════════════════════════════════════════════
# 4. 组合所有概念的路由
# ══════════════════════════════════════════════════════════════

# WHY: 模拟依赖注入获取用户
def get_current_user(token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    return {"name": "客服小李", "role": "agent"}


@app.get("/ticket/{ticket_id}")
def get_ticket(
    ticket_id: str,
    user: dict = Depends(get_current_user),
    include_logs: bool = False,
):
    """
    查询工单——组合了：
    - 路径参数 ticket_id
    - 依赖注入 user (认证)
    - 查询参数 include_logs
    """
    result = {
        "ticket_id": ticket_id,
        "operator": user["name"],
        "status": "处理中",
    }
    if include_logs:
        result["logs"] = ["已分配客服", "已联系顾客"]
    return result


# ══════════════════════════════════════════════════════════════
# 5. 健康检查与元信息
# ══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    """健康检查端点。"""
    return {"status": "healthy", "service": "智能客服 API"}


@app.get("/info")
def app_info():
    """应用信息——展示各种元数据。"""
    return {
        "title": app.title,
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
