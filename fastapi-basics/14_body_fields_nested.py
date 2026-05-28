# -*- coding: utf-8 -*-
"""
14_body_fields_nested.py — FastAPI 请求体字段与嵌套模型
=========================================================

【概念】请求体字段校验与嵌套模型
Pydantic 的 Field() 函数不仅能声明字段，还提供丰富的校验：
  - 类型校验 (str, int, float, bool)
  - 长度/范围 (min_length, max_length, ge, le, gt, lt)
  - 正则匹配 (regex, pattern)
  - 默认值/必填 (default, ...)
  - 嵌套模型（一个模型包含另一个模型）

嵌套模型让复杂数据结构清晰、可复用、可独立校验。

【在智能客服中解决什么问题】
客服工单是多层嵌套结构：
  Order
    ├── Customer (顾客信息)
    │   ├── name, phone
    │   └── Address (地址)
    │       ├── province, city
    │       └── detail
    ├── Items[] (商品列表)
    │   └── Item (单项商品)
    │       ├── product_name, price, quantity
    └── Payment (支付信息)
        ├── method, amount
        └── time

【核心流程】

  JSON 请求体                              Pydantic 校验链
  ──────────────────────────────────────────────────────

  {                                        ┌──────────────────┐
    "customer": {                          │ Customer 模型校验 │
      "name": "张伟",             ─────→    │  ├ name: str ✓   │
      "address": {                          │  └ address:       │
        "province": "北京",                 │     Address 模型   │
        "city": "北京",                     │     ├ province ✓  │
        "detail": "朝阳区..."               │     └ city ✓      │
      }                                     └──────────────────┘
    },                                     ┌──────────────────┐
    "items": [                             │ Item[] 列表校验   │
      {"name": "耳机", "qty": 1}  ─────→    │  每个元素独立校验  │
    ]                                       └──────────────────┘
  }

【测试案例】
  # 启动服务器
  python fastapi-basics/14_body_fields_nested.py

  # 提交评价——基础字段校验
  curl -X POST http://localhost:8000/review \
    -H "Content-Type: application/json" \
    -d '{"reviewer_email":"zhangwei@example.com","product_id":1,"rating":5,"content":"耳机音质非常好，降噪效果惊艳，推荐购买！","tags":["音质好","降噪"]}'
  # → {"message":"评价成功","review":{...}}

  # 评分超出范围（6 > 5）→ 422
  curl -X POST http://localhost:8000/review \
    -H "Content-Type: application/json" \
    -d '{"reviewer_email":"test@example.com","product_id":1,"rating":6,"content":"很好很好很好很好很好"}'
  # → 422（rating 必须在 1-5 之间）

  # 三层嵌套模型——创建订单（Customer > Address, OrderItem[], Payment）
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"customer":{"name":"张伟","address":{"province":"广东省","city":"深圳市","district":"南山区","detail":"科技园南区A栋101室","phone":"13800138000"}},"items":[{"product_id":1,"product_name":"蓝牙耳机","price":299,"quantity":1},{"product_id":2,"product_name":"数据线","price":19.9,"quantity":2}],"payment":"微信支付","remark":"请工作日送货"}'
  # → {"order_id":"ORD-20240120-0001","customer":"张伟","city":"深圳市","items_count":2,"total":338.8,...}

  # 地址手机号格式错误 → 422（嵌套子模型 Address.phone regex 校验）
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"customer":{"name":"张伟","address":{"province":"广东","city":"深圳","detail":"科技园A栋101","phone":"12345"}},"items":[{"product_id":1,"product_name":"耳机","price":299,"quantity":1}],"payment":"微信支付"}'
  # → 422（phone 不匹配手机号正则 ^1[3-9]\\d{9}$）

  # 保存对话——List 嵌套模型
  curl -X POST http://localhost:8000/conversation \
    -H "Content-Type: application/json" \
    -d '{"session_id":"sess-001","customer_name":"张伟","messages":[{"role":"customer","content":"我的耳机有杂音"},{"role":"agent","content":"您好，请拍照发给我们确认"}]}'
  # → {"session_id":"sess-001","message_count":2,"last_message":"您好，请拍照发给我们确认"}

【pip install】
pip install fastapi uvicorn pydantic
"""

import uvicorn
from typing import Optional, List, Set
from datetime import datetime
from decimal import Decimal
from enum import Enum

from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr, HttpUrl

app = FastAPI(title="好买电商客服 API - 请求体字段与嵌套模型")


# ══════════════════════════════════════════════════════════════
# 1. Field() 完整校验参数
# ══════════════════════════════════════════════════════════════

class ProductReview(BaseModel):
    """
    商品评价模型——展示 Field 的完整校验能力。
    """
    # WHY: EmailStr 需要 pip install pydantic[email]，这里用 str + regex 替代
    reviewer_email: str = Field(
        ...,
        regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="评价者邮箱",
    )
    product_id: int = Field(..., ge=1, description="商品 ID")
    # WHY: ge=1, le=5 限制评分范围
    rating: int = Field(..., ge=1, le=5, description="评分 (1-5)")
    # WHY: min_length=10 确保评价不是敷衍的"好""不错"
    content: str = Field(..., min_length=10, max_length=1000, description="评价内容")
    # WHY: List[str] 且每个元素独立校验长度
    tags: List[str] = Field(
        default_factory=list,
        description="评价标签",
    )
    # WHY: default_factory=datetime.now 确保每次创建对象都生成新时间
    created_at: datetime = Field(default_factory=datetime.now, description="评价时间")


@app.post("/review")
def submit_review(review: ProductReview):
    """提交商品评价——完整字段校验。"""
    return {"message": "评价成功", "review": review.model_dump()}


# ══════════════════════════════════════════════════════════════
# 2. 嵌套模型
# ══════════════════════════════════════════════════════════════

class Address(BaseModel):
    """收货地址——嵌套模型的基础组件。"""
    province: str = Field(..., description="省份")
    city: str = Field(..., description="城市")
    district: Optional[str] = Field(None, description="区/县")
    detail: str = Field(..., min_length=5, description="详细地址")
    phone: str = Field(..., regex=r"^1[3-9]\d{9}$", description="收货人手机号")


class Customer(BaseModel):
    """顾客信息——包含嵌套的 Address。"""
    name: str = Field(..., min_length=1, max_length=50, description="收货人姓名")
    # WHY: Address 作为字段类型——自动递归校验所有子字段
    address: Address


class OrderItem(BaseModel):
    """订单中的单项商品。"""
    product_id: int = Field(..., ge=1)
    product_name: str = Field(..., min_length=1)
    # WHY: Decimal 比 float 更适合金额——避免浮点数精度问题
    price: float = Field(..., gt=0, description="单价")
    quantity: int = Field(..., ge=1, description="数量")


class PaymentMethod(str, Enum):
    wechat = "微信支付"
    alipay = "支付宝"
    card = "银行卡"


class OrderCreate(BaseModel):
    """
    创建订单——三层嵌套模型。
    包含 Customer(含 Address)、OrderItem[]、支付方式。
    """
    customer: Customer
    items: List[OrderItem] = Field(..., min_length=1, description="订单商品列表")
    payment: PaymentMethod = Field(..., description="支付方式")
    # WHY: Optional[str] = None → 可选字段，不传时为 None
    coupon_code: Optional[str] = Field(None, min_length=6, max_length=20, description="优惠券码")
    remark: Optional[str] = Field(None, max_length=200, description="备注")


@app.post("/order")
def create_order(order: OrderCreate):
    """
    创建订单——多层嵌套校验。
    WHY: 嵌套模型自动递归校验——Address 的 phone 字段不合法也会报 422。
    """
    total = sum(item.price * item.quantity for item in order.items)
    return {
        "order_id": "ORD-20240120-0001",
        "customer": order.customer.name,
        "city": order.customer.address.city,
        "items_count": len(order.items),
        "total": round(total, 2),
        "payment": order.payment.value,
    }


# ══════════════════════════════════════════════════════════════
# 3. 列表中的嵌套模型
# ══════════════════════════════════════════════════════════════

class MessageItem(BaseModel):
    role: str = Field(..., regex=r"^(customer|agent|system)$")
    content: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.now)


class Conversation(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    customer_name: str = Field(...)
    # WHY: List[MessageItem] 确保数组中每个元素都符合 MessageItem 结构
    messages: List[MessageItem] = Field(..., min_length=1, description="对话消息列表")


@app.post("/conversation")
def save_conversation(conv: Conversation):
    """保存客服对话——列表嵌套模型校验。"""
    return {
        "session_id": conv.session_id,
        "message_count": len(conv.messages),
        "last_message": conv.messages[-1].content[:50],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
