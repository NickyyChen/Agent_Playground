# -*- coding: utf-8 -*-
"""
03_basic_routing.py — FastAPI 基本路由
========================================

【概念】什么是路由？
路由 = HTTP 方法 + URL 路径 → 函数 的映射关系。
FastAPI 用装饰器声明路由：@app.get(), @app.post(), @app.put(), @app.delete()
分别对应 HTTP 的 GET（查）、POST（增）、PUT（改）、DELETE（删）方法。

【在智能客服中解决什么问题】
RESTful API 设计是客服系统的标准做法：
  GET    /order/{id}    →  查询订单
  POST   /refund        →  创建退款
  PUT    /order/{id}    →  修改订单（如改地址）
  DELETE /refund/{id}   →  撤销退款申请
同一 URL 不同方法，做不同的事——这就是 REST 风格。

【核心流程】

  客户端请求                      路由匹配
  ─────────────────────────────────────────
  GET /order/001  ───────→  @app.get("/order/{order_id}")
  POST /order      ──────→  @app.post("/order")
  PUT /order/001   ──────→  @app.put("/order/{order_id}")
  DELETE /order/001 ─────→  @app.delete("/order/{order_id}")

  ★ 同一个 URL /order/001，不同 HTTP 方法，执行不同逻辑！

【测试案例】
  # 启动服务器
  python fastapi-basics/03_basic_routing.py

  # GET 查询订单
  curl http://localhost:8000/order/001
  # → {"order_id":"001","product":"蓝牙耳机","status":"已发货"}

  curl http://localhost:8000/order/latest
  # → {"latest":{"product":"手机壳","status":"待付款"}}

  # POST 创建订单
  curl -X POST "http://localhost:8000/order?product=数据线&status=待付款"
  # → {"order_id":"003","product":"数据线","status":"待付款"}

  # PUT 更新订单
  curl -X PUT "http://localhost:8000/order/001?product=蓝牙耳机Pro&status=已发货"
  # → {"order_id":"001","product":"蓝牙耳机Pro","status":"已发货"}

  # DELETE 删除订单
  curl -X DELETE http://localhost:8000/order/001
  # → {"deleted":"001","was":{"product":"蓝牙耳机","status":"已发货"}}

  【路由优先级规则】
  固定路径 > 动态路径参数：
    /order/latest  (固定) 优先于 /order/{order_id} (动态)
  如果在 {order_id} 之前定义 /latest，/latest 会先匹配；
  反之 /latest 会被 {order_id} 捕获为 "latest" 字符串。

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="好买电商客服 API - 路由学习")

# WHY: 模拟数据库——实际项目中这里是真正的数据库操作
fake_orders = {
    "001": {"product": "蓝牙耳机", "status": "已发货"},
    "002": {"product": "手机壳", "status": "待付款"},
}
fake_refunds = {}


# ══════════════════════════════════════════════════════════════
# GET —— 查询操作（不会修改服务器数据）
# ══════════════════════════════════════════════════════════════

@app.get("/order/latest")
def get_latest_order():
    """获取最新订单。固定路径 /order/latest 优先于 /order/{order_id}。"""
    return {"latest": list(fake_orders.values())[-1]}


@app.get("/order/{order_id}")
def get_order(order_id: str):
    """
    根据 ID 查询订单。
    WHY: {order_id} 是路径参数——FastAPI 自动从 URL 提取并传给函数。
    """
    order = fake_orders.get(order_id)
    if not order:
        return {"error": f"订单 {order_id} 不存在"}
    return {"order_id": order_id, **order}


# ══════════════════════════════════════════════════════════════
# POST —— 创建操作
# ══════════════════════════════════════════════════════════════

@app.post("/order")
def create_order(product: str, status: str = "待付款"):
    """
    创建新订单。
    WHY: POST 用于创建资源，数据通常放在请求体中。
         这里为了演示简单使用查询参数方式传参。
    """
    new_id = f"{len(fake_orders) + 1:03d}"
    fake_orders[new_id] = {"product": product, "status": status}
    return {"order_id": new_id, **fake_orders[new_id]}


# ══════════════════════════════════════════════════════════════
# PUT —— 完整更新操作
# ══════════════════════════════════════════════════════════════

@app.put("/order/{order_id}")
def update_order(order_id: str, product: str, status: str):
    """
    更新订单信息。
    WHY: PUT 用于完整替换资源——这里要求提供所有字段。
    """
    if order_id not in fake_orders:
        return {"error": f"订单 {order_id} 不存在"}
    fake_orders[order_id] = {"product": product, "status": status}
    return {"order_id": order_id, **fake_orders[order_id]}


# ══════════════════════════════════════════════════════════════
# DELETE —— 删除操作
# ══════════════════════════════════════════════════════════════

@app.delete("/order/{order_id}")
def delete_order(order_id: str):
    """
    删除订单。
    WHY: DELETE 用于删除资源——操作不可逆，实际项目需加软删除或二次确认。
    """
    if order_id not in fake_orders:
        return {"error": f"订单 {order_id} 不存在"}
    removed = fake_orders.pop(order_id)
    return {"deleted": order_id, "was": removed}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
