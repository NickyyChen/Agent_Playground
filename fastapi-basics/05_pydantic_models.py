# -*- coding: utf-8 -*-
"""
05_pydantic_models.py — FastAPI Pydantic 模型
===============================================

【概念】什么是 Pydantic？
Pydantic 是 Python 的数据校验库，通过**类型注解**定义数据模型。
FastAPI 深度集成 Pydantic：
  - 请求体校验：自动检查 JSON 字段类型、必填、长度、数值范围
  - 响应序列化：自动将 Pydantic 对象转为 JSON
  - 文档生成：字段描述自动出现在 Swagger UI 中

【在智能客服中解决什么问题】
前端传过来的退款申请数据不可信——可能缺字段、类型错误、金额为负数。
Pydantic 在数据进入业务逻辑之前就完成校验，不合法数据直接返回 422。
避免"垃圾进垃圾出"，减少 80% 的数据类 Bug。

【核心流程】

  JSON 请求体                           Pydantic 校验
  ─────────────────────────────────────────────────

  {"order_id": "001",                   ┌─────────────────────┐
   "reason": "质量",  ← 少于5字 ❌       │ 自动校验：           │
   "amount": -50}     ← 负数 ❌          │  类型、必填、长度、   │
                                        │  范围、正则表达式    │
                                        └──────┬──────────────┘
                                               │
                                   校验失败 → 422 Unprocessable Entity
                                   校验通过 → 转为 Pydantic 对象，传给函数

【测试案例】
  # 启动服务器
  python fastapi-basics/05_pydantic_models.py

  # 正常创建订单
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","product_name":"蓝牙耳机","price":299,"status":"待付款"}'
  # → {"message":"订单创建成功","order":{...}}

  # 缺少必填字段 → 422（Pydantic 自动校验）
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001"}'
  # → 422 Unprocessable Entity（缺少 product_name, price）

  # 退款金额超过原价 → 422（自定义 @validator 拦截）
  curl -X POST http://localhost:8000/refund \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","reason":"质量问题退货退款","refund_amount":500,"original_price":299}'
  # → 422（退款金额(500)不能超过原订单金额(299)）

  # 正常提交咨询（可选字段可不传）
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d '{"name":"张伟","phone":"13800138000","tags":["投诉","物流"]}'
  # → {"message":"咨询已记录","name":"张伟","tags":["投诉","物流"]}

【pip install】
pip install fastapi uvicorn pydantic
"""

import uvicorn
from typing import Optional, List
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field, field_validator, model_validator

app = FastAPI(title="好买电商客服 API - Pydantic 模型")


# ══════════════════════════════════════════════════════════════
# 1. 基础 Pydantic 模型
# ══════════════════════════════════════════════════════════════

# WHY: 枚举限制字段只能取预定义值，避免"待付款/待支付/未付款"这样的同义词混乱
class OrderStatus(str, Enum):
    pending = "待付款"
    paid = "已付款"
    shipped = "已发货"
    delivered = "已签收"
    refunding = "退款中"


class OrderBase(BaseModel):
    """
    订单基础模型。
    Field() 参数说明：
      ...      → 必填（Ellipsis）
      min_length → 最小长度
      max_length → 最大长度
      gt        → 大于（greater than）
      ge        → 大于等于（greater or equal）
      pattern   → 正则匹配
      description → Swagger 文档描述
      example   → Swagger 示例值
    """
    order_id: str = Field(..., min_length=3, max_length=20, description="订单号")
    product_name: str = Field(..., min_length=1, max_length=100, description="商品名称")
    price: float = Field(..., gt=0, description="价格，必须 > 0")
    status: OrderStatus = Field(default=OrderStatus.pending, description="订单状态")


# ══════════════════════════════════════════════════════════════
# 2. 自定义校验
# ══════════════════════════════════════════════════════════════

class RefundRequest(BaseModel):
    """
    退款申请模型——展示自定义校验器。
    WHY: 业务规则校验（如退款金额不能超过原价）属于业务逻辑层，
         放在 Pydantic validator 中可以让校验靠近数据定义。
    """
    order_id: str = Field(..., min_length=3)
    reason: str = Field(..., min_length=5, max_length=200, description="退款原因")
    refund_amount: float = Field(..., gt=0, description="退款金额")
    original_price: float = Field(..., gt=0, description="原订单金额")

    # WHY: @field_validator 定义单字段校验规则（Pydantic V2）
    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v):
        """校验退款原因不能全是空格。"""
        if not v.strip():
            raise ValueError("退款原因不能是空白字符")
        return v.strip()

    # WHY: @model_validator(mode='after') 在所有字段校验完后运行，可以安全地跨字段比较
    @model_validator(mode='after')
    def amount_not_exceed_original(self):
        """校验退款金额不超过原价。"""
        if self.refund_amount > self.original_price:
            raise ValueError(
                f"退款金额({self.refund_amount})不能超过原订单金额({self.original_price})"
            )
        return self


# ══════════════════════════════════════════════════════════════
# 3. 可选字段与默认值
# ══════════════════════════════════════════════════════════════

class CustomerQuery(BaseModel):
    """
    顾客咨询模型——展示可选字段。
    Optional[str] = None 表示字段可选（可以为 None 或 JSON 中不传）。
    """
    name: str = Field(..., description="顾客姓名")
    # WHY: Optional[str] 表示这个字段可选，没有时默认为 None
    phone: Optional[str] = Field(None, pattern=r"^1[3-9]\d{9}$", description="手机号")
    # WHY: List[str] 表示字符串列表，default_factory=list 确保默认值是新的空列表
    tags: List[str] = Field(default_factory=list, description="咨询标签")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


# ══════════════════════════════════════════════════════════════
# 路由
# ══════════════════════════════════════════════════════════════

@app.post("/order")
def create_order(order: OrderBase):
    """创建订单——FastAPI 自动用 OrderBase 校验请求体。"""
    return {"message": "订单创建成功", "order": order.model_dump()}


@app.post("/refund")
def create_refund(refund: RefundRequest):
    """提交退款——含自定义校验器。"""
    return {
        "message": "退款申请已受理",
        "order_id": refund.order_id,
        "refund_amount": refund.refund_amount,
    }


@app.post("/query")
def submit_query(query: CustomerQuery):
    """提交咨询。"""
    return {
        "message": "咨询已记录",
        "name": query.name,
        "tags": query.tags,
        "time": query.created_at.isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
