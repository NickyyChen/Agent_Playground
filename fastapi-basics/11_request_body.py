# -*- coding: utf-8 -*-
"""
11_request_body.py — FastAPI 请求体
=====================================

【概念】什么是请求体？
请求体是客户端发送给服务器的数据，通常用于 POST/PUT/PATCH 请求。
与路径参数和查询参数不同：
  - 路径参数 → URL 的一部分（资源定位）
  - 查询参数 → URL ? 后面（过滤条件）
  - 请求体   → HTTP Body（创建/更新数据）

FastAPI 用 Pydantic 模型定义请求体结构，自动完成 JSON 解析和校验。

【在智能客服中解决什么问题】
  - POST /refund → 请求体 = 退款申请数据（订单号、原因、金额）
  - PUT  /order/{id} → 请求体 = 要修改的字段
  - POST /ticket → 请求体 = 工单内容

【核心流程】

  POST /refund HTTP/1.1
  Content-Type: application/json         ← 告诉服务器：数据是 JSON
                                          │
  {                                       │
    "order_id": "ORD001",                 │
    "reason": "商品有划痕",               │  ← 请求体（JSON）
    "amount": 299                         │
  }                                       ▼
                          ┌────────────────────────┐
                          │  FastAPI 自动处理：     │
                          │  1. 读取 JSON 字符串   │
                          │  2. 解析为 Python dict │
                          │  3. 用 Pydantic 校验   │
                          │  4. 注入到函数参数     │
                          └────────────────────────┘

【测试案例】
  # 启动服务器
  python fastapi-basics/11_request_body.py

  # 基础请求体（JSON）
  curl -X POST http://localhost:8000/refund \
    -H "Content-Type: application/json" \
    -d '{"order_id":"ORD001","reason":"商品有划痕需要退货退款","amount":299}'
  # → {"ticket_id":"TKT-ORD001","order_id":"ORD001","amount":299,"status":"已受理"}

  # 多请求体参数（customer + content 两个对象合并到一个 JSON）
  curl -X POST http://localhost:8000/ticket \
    -H "Content-Type: application/json" \
    -d '{"customer":{"name":"张伟","phone":"13800138000"},"content":{"title":"产品问题","description":"蓝牙耳机充电口松动","priority":4}}'
  # → {"ticket_id":"TKT-NEW","customer":"张伟","phone":"13800138000",...}

  # 单一值请求体（直接传字符串，无需包装）
  curl -X PUT http://localhost:8000/order/ORD001/status \
    -H "Content-Type: application/json" \
    -d '"已发货"'
  # → {"order_id":"ORD001","new_status":"已发货"}

  # 嵌套模型——创建含物流的订单
  curl -X POST http://localhost:8000/order \
    -H "Content-Type: application/json" \
    -d '{"product":"蓝牙耳机","quantity":2,"note":"请发顺丰","logistics":{"company":"顺丰","tracking_no":"SF123"},"tags":["加急","易碎"]}'
  # → {"order_id":"ORD-NEW","detail":{...}}

  # 联合类型——发文本消息
  curl -X POST http://localhost:8000/message \
    -H "Content-Type: application/json" \
    -d '{"type":"text","content":"请问我的订单什么时候到？"}'
  # → {"type":"text","preview":"请问我的订单什么时候到？"}

  # 联合类型——发图片消息
  curl -X POST http://localhost:8000/message \
    -H "Content-Type: application/json" \
    -d '{"type":"image","image_url":"https://img.example.com/photo.png","width":800}'
  # → {"type":"image","url":"https://img.example.com/photo.png","width":800}

【pip install】
pip install fastapi uvicorn pydantic
"""

import uvicorn
from typing import Optional, List, Union
from datetime import datetime

from fastapi import FastAPI, Body
from pydantic import BaseModel, Field

app = FastAPI(title="好买电商客服 API - 请求体")


# ══════════════════════════════════════════════════════════════
# 1. 基础请求体
# ══════════════════════════════════════════════════════════════

class RefundRequest(BaseModel):
    """
    退款请求体。
    WHY: 继承 BaseModel → 自动获得 JSON 解析和校验能力。
    """
    order_id: str = Field(..., description="订单号")
    reason: str = Field(..., min_length=5, max_length=500, description="退款原因")
    amount: float = Field(..., gt=0, description="退款金额")


@app.post("/refund")
def create_refund(refund: RefundRequest):
    """
    提交退款申请。
    refund 参数自动从请求体 JSON 解析——不需要手动 json.loads()。
    """
    return {
        "ticket_id": f"TKT-{refund.order_id}",
        "order_id": refund.order_id,
        "amount": refund.amount,
        "status": "已受理",
    }


# ══════════════════════════════════════════════════════════════
# 2. 多请求体参数（Body 嵌套）
# ══════════════════════════════════════════════════════════════

class CustomerInfo(BaseModel):
    name: str = Field(..., description="顾客姓名")
    phone: str = Field(..., description="联系电话")


class TicketContent(BaseModel):
    title: str = Field(..., description="工单标题")
    description: str = Field(..., description="详细描述")
    priority: int = Field(default=3, ge=1, le=5, description="优先级 1-5")


@app.post("/ticket")
def create_ticket(
    customer: CustomerInfo,
    content: TicketContent,
):
    """
    创建工单——多个请求体参数。
    WHY: 多个 Pydantic 参数 → FastAPI 自动合并 JSON 字段。
         前端只需发一个 JSON，里面包含 customer 和 content 两个对象的字段：
         {"customer": {"name": "张", "phone": "138..."},
          "content": {"title": "产品问题", "description": "..."}}
    """
    return {
        "ticket_id": "TKT-NEW",
        "customer": customer.name,
        "phone": customer.phone,
        "title": content.title,
        "priority": content.priority,
    }


# ══════════════════════════════════════════════════════════════
# 3. 单一值请求体
# ══════════════════════════════════════════════════════════════

@app.put("/order/{order_id}/status")
def update_order_status(
    order_id: str,
    # WHY: Body(...) 嵌入单个值 → 请求体直接是字符串，而不是 {"status": "xxx"}
    #      Body(..., embed=True) 则要求包装在 JSON 对象中
    new_status: str = Body(..., description="新状态"),
):
    """
    更新订单状态——请求体只有一个字符串。
    WHY: 有时前端只想传一个值，不需要 Pydantic 模型。
         请求体示例： "已发货"（不是 {"new_status": "已发货"}）
    """
    return {"order_id": order_id, "new_status": new_status}


# ══════════════════════════════════════════════════════════════
# 4. 可选字段与嵌套
# ══════════════════════════════════════════════════════════════

class LogisticsInfo(BaseModel):
    company: str = Field(..., description="快递公司")
    tracking_no: str = Field(..., description="运单号")


class OrderCreate(BaseModel):
    product: str = Field(..., description="商品名称")
    quantity: int = Field(default=1, ge=1, description="数量 ≥ 1")
    # WHY: Optional[...] = None 表示字段可选，不传时为 None
    note: Optional[str] = Field(None, max_length=200, description="备注")
    # WHY: 嵌套模型——logistics 字段本身是一个对象
    logistics: Optional[LogisticsInfo] = Field(None, description="物流信息（发货后补充）")
    # WHY: List[str] 表示字符串数组
    tags: List[str] = Field(default_factory=list, description="标签")


@app.post("/order")
def create_order(order: OrderCreate):
    """创建订单——展示嵌套模型和可选字段。"""
    return {"order_id": "ORD-NEW", "detail": order.model_dump()}


# ══════════════════════════════════════════════════════════════
# 5. 联合类型请求体
# ══════════════════════════════════════════════════════════════

class TextMessage(BaseModel):
    type: str = "text"
    content: str


class ImageMessage(BaseModel):
    type: str = "image"
    image_url: str
    width: Optional[int] = None


@app.post("/message")
def receive_message(
    # WHY: Union[TextMessage, ImageMessage] 支持两种不同的请求体格式
    #      FastAPI 根据 JSON 字段结构自动判断是哪种类型
    msg: Union[TextMessage, ImageMessage],
):
    """
    处理客服消息——支持文本和图片两种格式。
    WHY: 联合类型让同一个接口接受不同结构的请求体，
         智能客服需要处理多种消息类型（文本、图片、语音等）。
    """
    if isinstance(msg, TextMessage):
        return {"type": "text", "preview": msg.content[:50]}
    else:
        return {
            "type": "image",
            "url": msg.image_url,
            "width": msg.width,
        }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
