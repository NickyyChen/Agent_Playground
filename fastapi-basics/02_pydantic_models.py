# -*- coding: utf-8 -*-
"""
02_pydantic_models.py — Pydantic 数据模型：请求体验证与响应序列化
================================================================

【概念】
FastAPI 深度集成 Pydantic，数据模型承担三重角色：
  1. 请求体验证（Request Body）：自动类型转换 + 字段校验
  2. 响应序列化（Response Model）：过滤不应返回的字段
  3. API 文档生成（OpenAPI Schema）：从模型自动生成 Swagger 文档

响应模型的作用：限制 API 输出——数据库模型可能有 password 字段，
但 response_model 可以只暴露 username/email，自动过滤敏感字段。

【在智能客服中的应用】
- 客服 API 的请求/响应都有固定格式
- 订单数据需要验证（订单号格式、价格范围等）
- 敏感字段（用户手机号）不应出现在某些响应中

【pip install】
pip install fastapi uvicorn pydantic

【ASCII 架构图】

  请求进入                           FastAPI 处理
  ──────── ─────────────────────────────────────

  POST /order
  Body: {"order_id":"xxx", "price": -100}
              │
              ▼
  ┌──────────────────────────┐
  │  Pydantic 请求体校验       │
  │  price=Field(gt=0)       │
  │  → -100 不满足 gt=0      │
  │  → 自动返回 422          │
  │  {"detail": [{"msg":     │
  │    "ensure > 0"}]}       │
  └──────────────────────────┘

  响应返回
  ────────
  OrderResponse (response_model) → 只返回公开字段
  OrderDB (数据库模型)           → order_id, user_phone, price, cost...
"""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional
import re


app = FastAPI(title="Pydantic 数据模型学习")


# ══════════════════════════════════════════════════════════════
# 1. 基础字段校验
# WHY: Field 定义校验规则——类型、范围、长度、默认值。
#      FastAPI 在请求进入函数前就完成了校验，函数内可以安全使用。
# ══════════════════════════════════════════════════════════════

class CreateOrderRequest(BaseModel):
    """创建订单的请求体"""
    product_name: str = Field(..., min_length=1, max_length=100,
                               description="商品名称")
    quantity: int = Field(default=1, ge=1, le=99, description="数量 1-99")
    price: float = Field(..., gt=0, le=100000, description="单价 >0")
    customer_phone: str = Field(..., description="手机号")
    note: Optional[str] = Field(None, max_length=500, description="备注")

    # WHY: @field_validator 做字段级别的自定义校验——
    #      Field 能做简单校验（>, <, 长度），正则匹配手机号这类
    #      复杂逻辑必须用 validator
    @field_validator("customer_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


@app.post("/order")
def create_order(req: CreateOrderRequest):
    """
    创建订单——所有校验由 Pydantic 自动完成。
    校验失败 → 422, 校验通过 → 函数内 req 是完美数据
    """
    return {"status": "created", "order_id": "ORD-NEW",
            "product": req.product_name, "total": req.price * req.quantity}


# ══════════════════════════════════════════════════════════════
# 2. 嵌套模型 —— 复杂 JSON 结构
# WHY: 真实业务中订单包含多个商品项、收货地址等嵌套数据。
#      Pydantic 支持模型嵌套——把复杂 JSON 拆成独立子模型，
#      每个子模型有自己的校验逻辑。
# ══════════════════════════════════════════════════════════════

class OrderItem(BaseModel):
    name: str
    price: float
    quantity: int = 1

class Address(BaseModel):
    province: str
    city: str
    detail: str
    phone: str

class ComplexOrder(BaseModel):
    items: list[OrderItem]          # WHY: list[子模型] → 自动递归校验
    address: Address                 # WHY: 嵌套模型 → 校验会递归到 Address
    coupon_code: Optional[str] = None


@app.post("/order/complex")
def create_complex_order(req: ComplexOrder):
    total = sum(item.price * item.quantity for item in req.items)
    return {
        "status": "created",
        "item_count": len(req.items),
        "total": total,
        "delivery_city": req.address.city,
    }


# ══════════════════════════════════════════════════════════════
# 3. 响应模型 —— 控制输出
# WHY: response_model 决定 API 返回什么字段——
#      数据库模型可能含成本价 cost_price、内部备注等，
#      response_model 只暴露应公开的字段，自动过滤敏感信息。
# ══════════════════════════════════════════════════════════════

# 模拟数据库模型（含敏感字段）
class OrderDB(BaseModel):
    order_id: str
    product: str
    price: float
    cost_price: float      # 成本价——不应返回给用户
    customer_phone: str     # 手机号——隐私字段
    internal_note: str      # 内部备注
    created_at: datetime

# 公开响应模型（只暴露安全字段）
class OrderPublicResponse(BaseModel):
    order_id: str
    product: str
    price: float
    created_at: datetime


@app.get("/order/{order_id}/public", response_model=OrderPublicResponse)
def get_order_public(order_id: str):
    """
    返回订单公开信息。
    WHY: response_model=OrderPublicResponse 确保只输出
         order_id/product/price/created_at，
         即使返回的 OrderDB 对象包含 cost_price/phone，也会被自动过滤掉。
    """
    # 模拟从数据库查出完整对象
    db_order = OrderDB(
        order_id=order_id, product="漫步者 W820NB",
        price=299.0, cost_price=180.0,           # 成本价
        customer_phone="13812345678",             # 手机号
        internal_note="VIP客户优先处理",           # 内部备注
        created_at=datetime.now(),
    )
    # WHY: 直接返回 db_order（含敏感字段），但 FastAPI 会用
    #      response_model 自动过滤——返回给用户的数据只有 OrderPublicResponse 的字段
    return db_order


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
