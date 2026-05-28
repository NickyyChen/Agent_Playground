# -*- coding: utf-8 -*-
"""
09_path_params.py — FastAPI 路径参数
=======================================

【概念】什么是路径参数？
路径参数是 URL 路径的一部分，用于标识"哪一个资源"。
格式：/resource/{param} → FastAPI 自动从 URL 中提取 {param} 的值并传给函数。

路径参数 vs 查询参数：
  路径参数：/order/ORD001     → "是哪个订单？"（资源定位，必填）
  查询参数：/orders?page=2    → "怎么展示？"（过滤/排序，可选）

【在智能客服中解决什么问题】
客服系统需要根据 ID 精确定位资源：
  GET  /order/{order_id}     →  查询某个订单
  GET  /user/{user_id}        →  查询某个用户
  PUT  /ticket/{ticket_id}    →  更新某个工单

【核心流程】

  URL: /order/ORD-2024-0015?detail=true
         │           │           │
         │ 路径参数   │ 查询参数   │
         ▼           ▼           ▼
  @app.get("/order/{order_id}")
  def get_order(order_id: str, detail: bool = False):
      ...

  ★ 路径参数必须填（否则 URL 不匹配），查询参数可选

【测试案例】
  # 启动服务器
  python fastapi-basics/09_path_params.py

  # 基础路径参数（字符串）
  curl http://localhost:8000/order/ORD001
  # → {"order_id":"ORD001","product":"蓝牙耳机","price":299}

  # 类型转换——int 类型自动校验
  curl http://localhost:8000/product/1
  # → {"product_id":1,"name":"漫步者 W820NB","price":299}

  # 传非数字 → 422（int 转换失败）
  curl http://localhost:8000/product/abc
  # → 422 Unprocessable Entity

  # 枚举路径参数——只能传 normal/vip/svip
  curl http://localhost:8000/customer/vip
  # → {"level":"VIP会员","customers":["张经理","李总监"]}

  # 包含 / 的路径参数（:path 标记）
  curl http://localhost:8000/files/logs/2024/error.txt
  # → {"file_path":"logs/2024/error.txt","exists":false}

  # 多个路径参数——层级资源
  curl http://localhost:8000/order/ORD001/item/2
  # → {"order_id":"ORD001","item_no":2,"name":"数据线","price":19.9}

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from enum import Enum
from fastapi import FastAPI

app = FastAPI(title="好买电商客服 API - 路径参数")


# ══════════════════════════════════════════════════════════════
# 1. 基础路径参数
# ══════════════════════════════════════════════════════════════

# WHY: {order_id} 中的 order_id 必须和函数参数名一致——
#      FastAPI 通过参数名匹配 URL 中的变量
@app.get("/order/{order_id}")
def get_order(order_id: str):
    """
    根据订单号查询订单。
    order_id 是路径参数——自动从 URL 中提取。
    """
    return {"order_id": order_id, "product": "蓝牙耳机", "price": 299}


# ══════════════════════════════════════════════════════════════
# 2. 类型转换——路径参数自动转换类型
# ══════════════════════════════════════════════════════════════

@app.get("/product/{product_id}")
def get_product(product_id: int):
    """
    根据商品 ID 查询商品。
    WHY: product_id: int —— FastAPI 自动将 URL 中的字符串转为 int。
         访问 /product/abc → 返回 422 错误（abc 不是合法 int）。
    """
    mock_products = {
        1: {"name": "漫步者 W820NB", "price": 299},
        2: {"name": "iPhone 15 手机壳", "price": 29.9},
    }
    product = mock_products.get(product_id)
    if not product:
        return {"error": f"商品 {product_id} 不存在"}
    return {"product_id": product_id, **product}


# ══════════════════════════════════════════════════════════════
# 3. 枚举路径参数——限制可选值
# ══════════════════════════════════════════════════════════════

# WHY: 枚举类型限制路径参数只能取预定义值
#      FastAPI 在 Swagger UI 中自动生成下拉选择框
class CustomerLevel(str, Enum):
    normal = "普通会员"
    vip = "VIP会员"
    svip = "超级VIP会员"


@app.get("/customer/{level}")
def get_customers_by_level(level: CustomerLevel):
    """
    按会员等级查询顾客。
    WHY: level 参数是枚举——只能是 normal/vip/svip 之一。
         访问 /customer/gold → 返回 422 错误。
    """
    data = {
        CustomerLevel.normal: ["用户A", "用户B"],
        CustomerLevel.vip: ["张经理", "李总监"],
        CustomerLevel.svip: ["王董事长"],
    }
    return {"level": level.value, "customers": data.get(level, [])}


# ══════════════════════════════════════════════════════════════
# 4. 包含路径的路径参数
# ══════════════════════════════════════════════════════════════

@app.get("/files/{file_path:path}")
def get_file(file_path: str):
    """
    读取文件——支持路径中包含 /。
    WHY: :path 是 FastAPI 的特殊标记，表示这个参数可以包含斜杠。
         /files/a/b/c.txt → file_path = "a/b/c.txt"
    """
    return {"file_path": file_path, "exists": False}


# ══════════════════════════════════════════════════════════════
# 5. 多个路径参数
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}/item/{item_no}")
def get_order_item(order_id: str, item_no: int):
    """
    查询订单中的某个商品项。
    WHY: 多个路径参数用于层级资源——
         /order/ORD001/item/2 → 订单 ORD001 的第 2 件商品。
    """
    items = {
        1: {"name": "蓝牙耳机", "price": 299},
        2: {"name": "数据线", "price": 19.9},
    }
    item = items.get(item_no)
    if not item:
        return {"error": f"订单 {order_id} 中不存在第 {item_no} 项"}
    return {"order_id": order_id, "item_no": item_no, **item}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
