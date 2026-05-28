# -*- coding: utf-8 -*-
"""
16_response_status.py — FastAPI 响应状态码
=============================================

【概念】HTTP 响应状态码
状态码是服务器告诉客户端"请求结果如何"的三位数字。

  ┌──────────┬────────────────────────────────────┐
  │ 状态码范围 │ 含义                               │
  ├──────────┼────────────────────────────────────┤
  │ 1xx      │ 信息——请求已收到，继续处理             │
  │ 2xx      │ 成功——请求已成功接收、理解、接受        │
  │ 3xx      │ 重定向——需要进一步操作完成请求          │
  │ 4xx      │ 客户端错误——请求有语法错误或无法实现     │
  │ 5xx      │ 服务器错误——服务器未能实现合法请求       │
  └──────────┴────────────────────────────────────┘

  常见状态码：
  200 OK            → 请求成功
  201 Created       → 创建成功
  204 No Content    → 成功但无返回内容（如删除）
  301 永久重定向    → 资源已永久移动
  400 Bad Request   → 请求参数错误
  401 Unauthorized  → 未认证
  403 Forbidden     → 无权限
  404 Not Found     → 资源不存在
  422 Unprocessable → 数据校验失败
  500 Internal Error → 服务器内部错误

【在智能客服中解决什么问题】
客服 API 需要精确的状态码让前端知道发生了什么：
  - 200: 查询成功
  - 201: 工单创建成功
  - 404: 订单不存在
  - 422: 退款金额校验失败
  - 429: 请求太频繁（防刷）

【测试案例】
  # 启动服务器
  python fastapi-basics/16_response_status.py

  # 正常查询 → 200（默认）
  curl http://localhost:8000/order/ORD001
  # → 200 OK

  # 不存在的订单 → 404
  curl http://localhost:8000/order/NOTEXIST
  # → 404 Not Found

  # 创建订单 → 201 Created
  curl -X POST "http://localhost:8000/order?product=数据线&price=19.9"
  # → 201 Created（而不是 200）

  # 删除订单 → 204 No Content（无响应体）
  curl -X DELETE http://localhost:8000/order/ORD002
  # → 204 No Content（无 body）

  # 退款申请 → 202 Accepted（异步处理）
  curl -X POST "http://localhost:8000/refund?order_id=ORD001&reason=质量问题"
  # → 202 Accepted

  # 待付款订单申请退款 → 400 Bad Request
  curl -X POST "http://localhost:8000/refund?order_id=ORD002&reason=不想要了"
  # → 400 Bad Request（仅已签收订单可退款）

  # 频繁请求触发限流 → 429 Too Many Requests
  for i in $(seq 1 15); do
    curl -s "http://localhost:8000/products/search?keyword=test&client_ip=127.0.0.1"
  done
  # → 第11次开始返回 429 Too Many Requests（含 Retry-After: 60 头）

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from fastapi import FastAPI, HTTPException, status

app = FastAPI(title="好买电商客服 API - 响应状态码")

# 模拟数据
db_orders = {
    "ORD001": {"product": "蓝牙耳机", "price": 299, "status": "已签收"},
    "ORD002": {"product": "手机壳", "price": 29.9, "status": "待付款"},
}


# ══════════════════════════════════════════════════════════════
# 1. 默认状态码 + 自定义状态码
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(order_id: str):
    """
    查询订单——默认返回 200 OK。
    GET 请求默认 200，不需要显式声明。
    """
    order = db_orders.get(order_id)
    if not order:
        # WHY: HTTPException 直接设置 HTTP 状态码和错误信息
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单 {order_id} 不存在",
        )
    return order


# ══════════════════════════════════════════════════════════════
# 2. @app.post 的 status_code 参数
# ══════════════════════════════════════════════════════════════

# WHY: status_code=201 表示"创建成功"——
#      REST 规范中，POST 创建资源应返回 201，而不是 200
@app.post("/order", status_code=status.HTTP_201_CREATED)
def create_order(product: str, price: float):
    """
    创建订单——返回 201 Created。
    WHY: 201 告诉客户端"新资源已创建"，前端可以据此跳转到新订单详情页。
    """
    new_id = f"ORD{len(db_orders) + 1:03d}"
    db_orders[new_id] = {"product": product, "price": price, "status": "待付款"}
    return {"order_id": new_id, **db_orders[new_id]}


# ══════════════════════════════════════════════════════════════
# 3. 204 No Content——删除操作
# ══════════════════════════════════════════════════════════════

# WHY: status_code=204 表示"操作成功但没有返回内容"——DELETE 的标准状态码
@app.delete("/order/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: str):
    """
    删除订单——返回 204 No Content。
    WHY: 删除成功后不需要返回内容，204 就是不返回 body 的 200。
    """
    if order_id not in db_orders:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    db_orders.pop(order_id)
    # 返回 None → FastAPI 看到 204 + None = 空响应体


# ══════════════════════════════════════════════════════════════
# 4. 使用 status 模块（可读性更好）
# ══════════════════════════════════════════════════════════════

@app.post("/refund", status_code=status.HTTP_202_ACCEPTED)
def create_refund(order_id: str, reason: str):
    """
    提交退款申请——返回 202 Accepted。
    WHY: 202 表示"已接受请求但尚未处理"——
         退款不是即时完成的，需要人工审核，202 比 201 更准确。
    """
    if order_id not in db_orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"订单 {order_id} 不存在",
        )
    if db_orders[order_id]["status"] != "已签收":
        # WHY: 400 表示客户端错误——订单状态不符合退款条件
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅已签收的订单可以申请退款",
        )
    return {
        "ticket_id": f"TKT-{order_id}",
        "status": "审核中",
        "estimated_days": "3-5个工作日",
    }


# ══════════════════════════════════════════════════════════════
# 5. 429 Too Many Requests——限流
# ══════════════════════════════════════════════════════════════

# WHY: 模拟调用计数——实际项目用 Redis 做限流
request_count = {}


@app.get("/products/search")
def search_products(keyword: str, client_ip: str = "127.0.0.1"):
    """
    搜索商品——带简易限流。
    WHY: 429 用于告诉客户端"请求太频繁，请稍后再试"——防刷/保护服务器。
    """
    count = request_count.get(client_ip, 0)
    if count > 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请 1 分钟后重试",
            # WHY: headers 可以返回额外的元信息，如重试时间
            headers={"Retry-After": "60"},
        )
    request_count[client_ip] = count + 1
    return {"keyword": keyword, "results": [{"name": "蓝牙耳机", "price": 299}]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
