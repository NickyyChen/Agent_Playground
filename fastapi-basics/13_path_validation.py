# -*- coding: utf-8 -*-
"""
13_path_validation.py — FastAPI 路径参数数值校验
==================================================

【概念】路径参数数值校验
路径参数同样可以使用 Path() 进行数值校验。
Path() 和 Query() 用法几乎一样，区别是 Path() 针对路径参数。

  Path(...)   → 必填的路径参数
  Path(1)     → 有默认值 1 的路径参数
  Path(..., ge=1, le=1000) → 必填，且 1 <= 值 <= 1000

【在智能客服中解决什么问题】
  - GET /order/{order_id} → order_id 不能为空
  - GET /product/{product_id} → product_id 必须是正整数
  - GET /ticket/{ticket_id} → ticket_id 必须符合格式

【核心流程】

  /product/abc  ──────→  product_id: int  →  422 错误 (abc 不是整数)
  /product/0    ──────→  product_id: int = Path(..., gt=0)  →  422 (必须 >0)
  /product/100  ──────→  product_id: int = Path(..., gt=0)  →  通过！

  ★ Path() 优先级高于类型注解——先校验 Path 条件，再做类型转换

【测试案例】
  # 启动服务器
  python fastapi-basics/13_path_validation.py

  # 数值范围校验——product_id 必须 1-999999
  curl http://localhost:8000/product/100
  # → 200 OK

  curl http://localhost:8000/product/0
  # → 422（ge=1 校验失败：product_id 必须 >= 1）

  # gt vs ge 的区别——金额必须 > 0（严格大于）
  curl http://localhost:8000/price/199.99
  # → {"amount":199.99,"tax":26.0}

  curl http://localhost:8000/price/0
  # → 422（gt=0 校验失败：0 不允许）

  # 正则校验订单号——必须符合 XXX-YYYYMMDD-NNNN
  curl http://localhost:8000/order/ORD-20240115-0001
  # → 200 OK

  curl http://localhost:8000/order/invalid
  # → 422（regex 不匹配）

  # 多路径参数分别校验
  curl http://localhost:8000/category/5/product/1
  # → 200 OK

  curl http://localhost:8000/category/200/product/1
  # → 422（category_id 超出 1-100 范围）

  # 路径参数 + 查询参数混合校验
  curl "http://localhost:8000/ticket/1?include_messages=true&message_limit=5"
  # → 200 OK（含对话记录，最多5条）

  # Swagger 示例（仓库代码有下拉示例）
  curl http://localhost:8000/warehouse/WH-BJ-01
  # → {"code":"WH-BJ-01","city":"北京","capacity":5000}

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional
from fastapi import FastAPI, Path, Query

app = FastAPI(title="好买电商客服 API - 路径参数数值校验")


# ══════════════════════════════════════════════════════════════
# 1. 基础数值校验——范围限制
# ══════════════════════════════════════════════════════════════

@app.get("/product/{product_id}")
def get_product(
    # WHY: ge=1 确保 product_id >= 1（数据库 ID 通常从 1 开始）
    #      lt=1000000 限制上限，防止遍历攻击
    product_id: int = Path(
        ...,
        ge=1,
        lt=1000000,
        title="商品 ID",
        description="商品唯一标识，1-999999 之间的整数",
    ),
):
    """
    查询商品——product_id 必须是 1-999999 之间的整数。
    /product/0   → 422 错误（< 1）
    /product/abc → 422 错误（不是整数）
    """
    return {"product_id": product_id, "name": "漫步者 W820NB", "price": 299}


# ══════════════════════════════════════════════════════════════
# 2. gt vs ge, lt vs le 的区别
# ══════════════════════════════════════════════════════════════

@app.get("/price/{amount}")
def check_price(
    amount: float = Path(
        ...,
        # WHY: gt=0  → 必须严格大于 0（0 不允许）
        #      ge=0  → 大于等于 0（0 允许）
        #      lt=100000 → 必须严格小于 100000
        #      le=100000 → 小于等于 100000
        gt=0,
        lt=100000,
        description="金额，必须 > 0 且 < 100000",
    ),
):
    """
    金额校验——展示 gt/lt 与 ge/le 的区别。
    gt=0 拒绝 0 元商品，lt=100000 拒绝异常大额。
    """
    return {"amount": amount, "tax": round(amount * 0.13, 2)}


# ══════════════════════════════════════════════════════════════
# 3. 字符串路径参数校验
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(
    order_id: str = Path(
        ...,
        min_length=5,
        max_length=30,
        # WHY: regex 在路径参数中同样可用
        regex=r"^[A-Z]{3}-\d{8}-\d{4}$",
        description="订单号，格式: XXX-YYYYMMDD-NNNN",
    ),
):
    """
    查询订单——校验订单号格式。
    WHY: 路径参数同样可以用正则——不合法的订单号直接 422，不到达业务逻辑。
    """
    return {"order_id": order_id, "status": "已发货"}


# ══════════════════════════════════════════════════════════════
# 4. 多个路径参数同时校验
# ══════════════════════════════════════════════════════════════

@app.get("/category/{category_id}/product/{product_no}")
def get_category_product(
    # WHY: 两个路径参数各自独立校验
    category_id: int = Path(..., ge=1, le=100, description="品类 ID (1-100)"),
    product_no: int = Path(..., ge=1, le=9999, description="商品序号 (1-9999)"),
):
    """
    按品类和序号查商品——多路径参数校验。
    """
    return {
        "category_id": category_id,
        "product_no": product_no,
        "product": {"name": "蓝牙耳机", "price": 299},
    }


# ══════════════════════════════════════════════════════════════
# 5. 路径参数 + 查询参数混合校验
# ══════════════════════════════════════════════════════════════

@app.get("/ticket/{ticket_id}")
def get_ticket(
    ticket_id: int = Path(..., ge=1, description="工单 ID"),
    # WHY: 路径参数和查询参数可以各自用 Path/Query 独立校验
    include_messages: bool = Query(False, description="是否包含对话记录"),
    message_limit: Optional[int] = Query(
        None, ge=1, le=200, description="对话记录条数限制"
    ),
):
    """
    查询工单——路径参数 + 查询参数混合校验。
    """
    result = {"ticket_id": ticket_id, "status": "处理中"}
    if include_messages:
        result["messages"] = [
            {"from": "顾客", "content": "我的耳机有杂音"},
            {"from": "客服", "content": "您好，请拍照发给我们确认"},
        ][:message_limit]
    return result


# ══════════════════════════════════════════════════════════════
# 6. 路径参数元数据
# ══════════════════════════════════════════════════════════════

@app.get("/warehouse/{warehouse_code}")
def get_warehouse(
    # WHY: Path 的 title/description 出现在 Swagger 文档中
    #      帮助前端和测试理解参数含义
    warehouse_code: str = Path(
        ...,
        title="仓库代码",
        description="仓库的唯一代码标识，如 WH-BJ-01（北京仓）",
        min_length=3,
        max_length=20,
        # WHY: openapi_examples 在 Swagger 中以示例下拉框展示
        examples={
            "北京仓": {"value": "WH-BJ-01"},
            "上海仓": {"value": "WH-SH-01"},
            "广州仓": {"value": "WH-GZ-01"},
        },
    ),
):
    """
    查询仓库——展示 Path 的元数据能力。
    """
    warehouses = {
        "WH-BJ-01": {"city": "北京", "capacity": 5000},
        "WH-SH-01": {"city": "上海", "capacity": 8000},
        "WH-GZ-01": {"city": "广州", "capacity": 3000},
    }
    wh = warehouses.get(warehouse_code)
    if not wh:
        return {"error": f"仓库 {warehouse_code} 不存在"}
    return {"code": warehouse_code, **wh}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
