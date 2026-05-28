# -*- coding: utf-8 -*-
"""
10_query_params.py — FastAPI 查询参数
========================================

【概念】什么是查询参数？
查询参数是 URL 中 ? 后面的 key=value 键值对，用 & 分隔。
在 FastAPI 中，函数签名里所有不是路径参数的参数，自动成为查询参数。

  /search?keyword=耳机&category=数码&page=1

  keyword → 查询参数
  category → 查询参数
  page → 查询参数

【在智能客服中解决什么问题】
智能客服系统的搜索/过滤/分页全靠查询参数：
  - 商品搜索：?keyword=蓝牙耳机&min_price=100&max_price=500
  - 工单查询：?status=待处理&agent=小李&page=2
  - 日志筛选：?start_date=2024-01-01&level=error

【核心流程】

  ?keyword=耳机&page=1&sort=price_desc
     │          │        │
     ▼          ▼        ▼
  ┌─────────────────────────────────┐
  │ def search(                    │
  │   keyword: str,     ← 必填     │
  │   page: int = 1,    ← 可选(有默认值) │
  │   sort: str = None  ← 可选(可空)   │
  │ )                              │
  └─────────────────────────────────┘

  ★ 原则：路径参数 = 找什么，查询参数 = 怎么展示

【测试案例】
  # 启动服务器
  python fastapi-basics/10_query_params.py

  # 可选查询参数——不传时用默认值
  curl "http://localhost:8000/orders"
  # → {"filters":{"status":null},"pagination":{"page":1,"page_size":10},...}

  # 带筛选条件
  curl "http://localhost:8000/orders?status=已签收&page=2&page_size=5"
  # → {"filters":{"status":"已签收"},"pagination":{"page":2,"page_size":5},...}

  # 多值查询参数（同一参数传多次 → List）
  curl "http://localhost:8000/products/filter?category=耳机&category=数据线"
  # → filters.categories = ["耳机", "数据线"]

  # 必填 + 校验的搜索
  curl "http://localhost:8000/products/search?keyword=蓝牙"
  # → {"keyword":"蓝牙","price_range":{...},"results":[...]}

  # 空关键词 → 422（min_length=1 校验）
  curl "http://localhost:8000/products/search?keyword="
  # → 422 Unprocessable Entity

  # 布尔查询参数——控制返回详细程度
  curl "http://localhost:8000/order/ORD001?include_logs=true&include_payment=true"
  # → 包含完整物流 + 支付信息的订单详情

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional, List

from fastapi import FastAPI, Query

app = FastAPI(title="好买电商客服 API - 查询参数")


# ══════════════════════════════════════════════════════════════
# 1. 基础查询参数——可选和默认值
# ══════════════════════════════════════════════════════════════

# WHY: 函数签名中没在路径里的参数自动是查询参数
#      str 类型 → 必填；str = None → 可选；str = "默认" → 有默认值
@app.get("/orders")
def list_orders(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    """
    查询订单列表。
    status: 可选，不传时查询全部
    page: 有默认值 1
    page_size: 有默认值 10
    """
    return {
        "filters": {"status": status},
        "pagination": {"page": page, "page_size": page_size},
        "items": [{"order_id": "ORD001", "status": status or "全部"}],
    }


# ══════════════════════════════════════════════════════════════
# 2. 多值查询参数
# ══════════════════════════════════════════════════════════════

@app.get("/products/filter")
def filter_products(
    # WHY: List[str] = Query(...) 表示同一个参数可以传多次
    #      ?category=耳机&category=数据线 → category = ["耳机", "数据线"]
    categories: List[str] = Query(default_factory=list, description="品类筛选，可多选"),
    tags: List[str] = Query(default_factory=list, description="标签，可多选"),
):
    """
    多条件筛选商品。
    WHY: 查询参数传多次（?key=a&key=b）→ FastAPI 自动收集为列表。
    """
    return {
        "filters": {
            "categories": categories,
            "tags": tags,
        },
        "results": [
            {"name": "漫步者 W820NB", "category": "耳机", "tags": ["降噪", "无线"]},
            {"name": "iPhone 15 手机壳", "category": "手机配件", "tags": ["保护壳"]},
        ],
    }


# ══════════════════════════════════════════════════════════════
# 3. Query 校验参数
# ══════════════════════════════════════════════════════════════

@app.get("/products/search")
def search_products(
    # WHY: Query(..., min_length=1) → ... 表示必填，min_length 校验最小长度
    keyword: str = Query(..., min_length=1, max_length=50, description="搜索关键词"),
    # WHY: Query(default=None, ge=0) → ge=0 校验 >=0，因为价格不能是负数
    min_price: Optional[float] = Query(None, ge=0, description="最低价 ≥ 0"),
    max_price: Optional[float] = Query(None, le=99999, description="最高价 ≤ 99999"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    # WHY: alias="page_size" 允许 URL 中用下划线命名，Python 变量名则任意
    page_size: int = Query(20, ge=1, le=100, alias="page_size", description="每页数量"),
    # WHY: deprecated=True 在 Swagger 中标记接口已废弃
    sort_by: Optional[str] = Query(
        None, deprecated=True, description="排序字段（已废弃，请用 order_by）"
    ),
):
    """
    搜索商品——展示 Query 的完整校验能力。

    Query 常用校验参数：
      ...            → 必填
      min_length     → 最小长度
      max_length     → 最大长度
      ge (>=)        → 大于等于
      le (<=)        → 小于等于
      gt (>)         → 大于
      lt (<)         → 小于
      regex          → 正则匹配
      alias          → URL 参数别名
      deprecated     → 标记已废弃
      description    → Swagger 文档说明
      include_in_schema → 是否显示在文档中
    """
    return {
        "keyword": keyword,
        "price_range": {"min": min_price, "max": max_price},
        "page": page,
        "page_size": page_size,
        "results": [
            {"name": "漫步者 W820NB", "price": 299},
            {"name": "小米 Buds 4 Pro", "price": 399},
        ],
    }


# ══════════════════════════════════════════════════════════════
# 4. 布尔查询参数——开关/标记
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order_detail(
    order_id: str,
    # WHY: bool 类型的查询参数，URL 中 ?include_logs=true / ?include_logs=1 / ?include_logs
    #      三种写法都表示 True
    include_logs: bool = False,
    include_payment: bool = False,
):
    """
    查询订单详情——可选是否附带物流和支付信息。
    WHY: bool 查询参数常用于控制返回数据的详细程度（轻量 vs 完整）。
    """
    result = {"order_id": order_id, "product": "蓝牙耳机", "status": "已签收"}

    if include_logs:
        result["logs"] = [
            "2024-01-15 下单",
            "2024-01-16 发货",
            "2024-01-18 签收",
        ]
    if include_payment:
        result["payment"] = {"method": "微信支付", "amount": 299, "time": "2024-01-15 10:30"}

    return result


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
