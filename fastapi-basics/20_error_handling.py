# -*- coding: utf-8 -*-
"""
20_error_handling.py — FastAPI 错误处理
=========================================

【概念】FastAPI 错误处理
FastAPI 提供多层错误处理机制：

  1. HTTPException       →  主动抛出 HTTP 错误
  2. @app.exception_handler → 自定义异常处理器（全局或特定异常）
  3. 自定义异常类         →  业务异常（OrderNotFoundError 等）
  4. 请求校验钩子         →  @app.middleware 在请求阶段拦截

错误处理层次：
  ┌─────────────────────────────────────────────┐
  │  第1层：Pydantic 自动校验 → 422             │
  │  第2层：路由内 HTTPException → 4xx/5xx       │
  │  第3层：自定义 exception_handler → 格式化    │
  │  第4层：兜底 Exception handler → 500         │
  └─────────────────────────────────────────────┘

【在智能客服中解决什么问题】
  - 订单不存在 → 404 并返回友好的中文提示
  - 权限不足 → 403 并告知缺少什么权限
  - 退款金额异常 → 400 并说明具体校验失败原因
  - 系统异常 → 500 但不让用户看到堆栈信息

【测试案例】
  # 启动服务器
  python fastapi-basics/20_error_handling.py

  # 查询存在的订单 → 200
  curl http://localhost:8000/order/ORD001
  # → {"order_id":"ORD001","product":"蓝牙耳机","status":"已签收","price":299}

  # 不存在的订单 → 404（自定义 OrderNotFoundError 异常）
  curl http://localhost:8000/order/NOTEXIST
  # → 404，响应格式: {"error":"ORDER_NOT_FOUND","message":"订单 NOTEXIST 不存在，请检查订单号是否正确","path":"/order/NOTEXIST"}

  # 无权限的退款 → 403（InsufficientPermissionError）
  curl -X POST "http://localhost:8000/refund?order_id=ORD001&reason=质量问题&operator_role=user"
  # → 403，{"error":"FORBIDDEN","message":"用户 当前用户 权限不足，需要 客服(agent) 角色",...}

  # 有客服权限的正常退款
  curl -X POST "http://localhost:8000/refund?order_id=ORD001&reason=质量问题&operator_role=agent"
  # → 200，{"ticket_id":"TKT-ORD001","status":"已受理"}

  # 待付款订单申请退款 → 400（RefundValidationError）
  curl -X POST "http://localhost:8000/refund?order_id=ORD002&reason=不想要了&operator_role=agent"
  # → 400，{"error":"REFUND_VALIDATION_FAILED","message":"订单 ORD002 退款校验失败: 订单状态为「待付款」，仅已签收订单可退款",...}

  # Pydantic 自动校验——缺少必填字段 → 422
  curl -X POST http://localhost:8000/refund/auto-validate \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001"}'
  # → 422（缺少 amount 字段）

  # 负数金额 → 422（gt=0 校验失败）
  curl -X POST http://localhost:8000/refund/auto-validate \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","amount":-50}'
  # → 422

  # 正常 Pydantic 校验
  curl -X POST http://localhost:8000/refund/auto-validate \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","amount":299}'
  # → 200

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

app = FastAPI(title="好买电商客服 API - 错误处理")


# ══════════════════════════════════════════════════════════════
# 1. 自定义业务异常类
# ══════════════════════════════════════════════════════════════

# WHY: 继承 Exception 创建可抛出的业务异常
#      不同异常类型对应不同的业务场景，比通用 HTTPException 更语义化
class OrderNotFoundError(Exception):
    """订单不存在。"""
    def __init__(self, order_id: str):
        self.order_id = order_id


class InsufficientPermissionError(Exception):
    """权限不足。"""
    def __init__(self, user: str, required_role: str):
        self.user = user
        self.required_role = required_role


class RefundValidationError(Exception):
    """退款校验失败。"""
    def __init__(self, order_id: str, reason: str):
        self.order_id = order_id
        self.reason = reason


# ══════════════════════════════════════════════════════════════
# 2. 注册自定义异常处理器
# ══════════════════════════════════════════════════════════════

# WHY: @app.exception_handler 把自定义异常映射到 HTTP 响应
#      ——抛业务异常 → 自动转为标准 HTTP 错误响应格式
@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    """订单不存在 → 404。"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ORDER_NOT_FOUND",
            "message": f"订单 {exc.order_id} 不存在，请检查订单号是否正确",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(InsufficientPermissionError)
async def permission_handler(request: Request, exc: InsufficientPermissionError):
    """权限不足 → 403。"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "FORBIDDEN",
            "message": f"用户 {exc.user} 权限不足，需要 {exc.required_role} 角色",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(RefundValidationError)
async def refund_validation_handler(request: Request, exc: RefundValidationError):
    """退款校验失败 → 400。"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "REFUND_VALIDATION_FAILED",
            "message": f"订单 {exc.order_id} 退款校验失败: {exc.reason}",
            "path": str(request.url.path),
        },
    )


# ══════════════════════════════════════════════════════════════
# 3. 全局兜底异常处理器
# ══════════════════════════════════════════════════════════════

# WHY: 捕获所有未被特定处理器拦截的 Exception——最后一道防线
#      防止内部错误信息（堆栈、代码路径）泄露给客户端
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理的异常 → 500。"""
    # 在实际项目中，这里会记录日志、发送告警
    print(f"[ERROR] {request.method} {request.url.path} → {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试或联系技术支持",
            "ref_id": f"ERR-{id(exc):x}",  # WHY: ref_id 用于技术支持定位问题
        },
    )


# ══════════════════════════════════════════════════════════════
# 4. HTTPException 处理器（统一格式）
# ══════════════════════════════════════════════════════════════

# WHY: 拦截所有 HTTPException，统一错误响应格式
#      默认 FastAPI 返回的 422 校验错误格式比较"技术化"——这里让它更友好
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """统一 HTTP 异常的响应格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path),
        },
        # WHY: 保留原始 headers（如 429 的 Retry-After）
        headers=getattr(exc, "headers", None),
    )


# ══════════════════════════════════════════════════════════════
# 5. 路由——使用自定义异常
# ══════════════════════════════════════════════════════════════

# 模拟数据
fake_orders = {
    "ORD001": {"product": "蓝牙耳机", "status": "已签收", "price": 299},
    "ORD002": {"product": "手机壳", "status": "待付款", "price": 29.9},
}


@app.get("/order/{order_id}")
def get_order(order_id: str):
    """
    查询订单——使用自定义异常。
    WHY: 抛 OrderNotFoundError 比手动构造 JSONResponse 更简洁，
         异常处理器统一处理格式。
    """
    order = fake_orders.get(order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    return order


@app.post("/refund")
def create_refund(order_id: str, reason: str, operator_role: str = "user"):
    """
    提交退款——组合使用多种自定义异常。
    """
    # 1. 检查订单是否存在
    order = fake_orders.get(order_id)
    if not order:
        raise OrderNotFoundError(order_id)

    # 2. 检查权限
    if operator_role != "agent":
        raise InsufficientPermissionError(
            user="当前用户",
            required_role="客服(agent)",
        )

    # 3. 检查退款条件
    if order["status"] != "已签收":
        raise RefundValidationError(
            order_id=order_id,
            reason=f"订单状态为「{order['status']}」，仅已签收订单可退款",
        )

    return {"ticket_id": f"TKT-{order_id}", "status": "已受理"}


# ══════════════════════════════════════════════════════════════
# 6. 触发自动校验错误（FastAPI 原生 422）
# ══════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field


class RefundForm(BaseModel):
    order_id: str = Field(..., min_length=5)
    amount: float = Field(..., gt=0)


@app.post("/refund/auto-validate")
def auto_validated_refund(form: RefundForm):
    """
    自动校验退款表单——展示 FastAPI 原生的 422 错误。
    WHY: 不需要手动写校验——Pydantic 自动校验，失败返回 422。
         访问 /docs 可以看到详细的校验规则。
    """
    return {"message": f"退款 {form.order_id} 金额 {form.amount}", "status": "已受理"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
