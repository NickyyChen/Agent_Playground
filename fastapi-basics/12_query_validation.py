# -*- coding: utf-8 -*-
"""
12_query_validation.py — FastAPI 查询参数校验
===============================================

【概念】查询参数校验
FastAPI 的 Query() 不仅能声明查询参数，还内置了强大的字符串校验功能。
这些校验在数据进入业务逻辑之前自动执行，避免"垃圾数据"污染系统。

【在智能客服中解决什么问题】
  - 搜索关键词不能为空 → min_length=1
  - 手机号必须 11 位 → min_length=11, max_length=11
  - 日期范围必须合法 → regex 匹配日期格式
  - 评分必须在 1-5 之间 → ge=1, le=5

【Query 校验参数速查表】

  ┌──────────────┬────────────────────┬──────────────────┐
  │ 参数          │ 作用                │ 示例              │
  ├──────────────┼────────────────────┼──────────────────┤
  │ ...           │ 必填                │ Query(...)        │
  │ min_length    │ 最小长度（字符串）   │ Query(..., min_length=1) │
  │ max_length    │ 最大长度（字符串）   │ Query(..., max_length=50) │
  │ ge            │ >= (greater/equal) │ Query(..., ge=0)  │
  │ le            │ <= (less/equal)    │ Query(..., le=100)│
  │ gt            │ >  (greater than)  │ Query(..., gt=0)  │
  │ lt            │ <  (less than)     │ Query(..., lt=100)│
  │ regex         │ 正则表达式          │ Query(..., regex=r"^\d+$") │
  │ alias         │ URL 参数别名        │ Query(..., alias="q") │
  │ deprecated    │ 标记已废弃          │ Query(..., deprecated=True) │
  │ title         │ Swagger 字段标题    │ Query(..., title="关键词") │
  │ description   │ Swagger 字段描述    │ Query(..., description="...")│
  └──────────────┴────────────────────┴──────────────────┘

【测试案例】
  # 启动服务器
  python fastapi-basics/12_query_validation.py

  # 字符串长度校验——空关键词 → 422
  curl "http://localhost:8000/search?keyword="
  # → 422（min_length=1 校验失败）

  curl "http://localhost:8000/search?keyword=蓝牙耳机"
  # → 200 OK

  # 数值范围校验——负价 → 422
  curl "http://localhost:8000/products/filter?min_price=-10"
  # → 422（ge=0 校验失败）

  curl "http://localhost:8000/products/filter?min_price=100&max_price=500&page=1&page_size=20"
  # → 200 OK

  # 正则校验——错误的订单号格式 → 422
  curl "http://localhost:8000/order/track?order_id=abc123"
  # → 422（regex 不匹配 "ORD-YYYYMMDD-NNNN"）

  curl "http://localhost:8000/order/track?order_id=ORD-20240115-0001&phone=13800138000"
  # → 200 OK

  # 别名——URL 中用短参数名 q
  curl "http://localhost:8000/tickets?q=退款"
  # → {"keyword":"退款","status":null,...}

  # 隐藏参数——debug 在 Swagger 中不可见但 URL 可以用
  curl "http://localhost:8000/internal/search?keyword=测试&debug=true"
  # → 200 OK（_internal 调试信息可见）

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional, List
from fastapi import FastAPI, Query

app = FastAPI(title="好买电商客服 API - 查询参数校验")


# ══════════════════════════════════════════════════════════════
# 1. 字符串长度校验
# ══════════════════════════════════════════════════════════════

@app.get("/search")
def search(
    # WHY: min_length=1 防止空字符串查询
    #      max_length=100 防止超长查询导致性能问题
    keyword: str = Query(
        ...,
        min_length=1,
        max_length=100,
        title="搜索关键词",
        description="商品名或品类关键词",
    ),
):
    """搜索商品——限制关键词长度。"""
    return {"keyword": keyword, "results": [{"name": "蓝牙耳机", "price": 299}]}


# ══════════════════════════════════════════════════════════════
# 2. 数值范围校验
# ══════════════════════════════════════════════════════════════

@app.get("/products/filter")
def filter_by_price(
    # WHY: ge=0 确保最低价不会是负数
    # WHY: le=999999 设置上限防止异常值
    min_price: Optional[float] = Query(
        None, ge=0, le=999999, description="最低价（元），>= 0"
    ),
    max_price: Optional[float] = Query(
        None, ge=0, le=999999, description="最高价（元），>= 0"
    ),
    # WHY: ge=1 页码从 1 开始
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量 (1-100)"),
):
    """
    按价格筛选商品。
    所有数值参数都有范围限制——防止客户端传入异常值。
    """
    return {
        "price_range": {"min": min_price, "max": max_price},
        "page": page,
        "page_size": page_size,
    }


# ══════════════════════════════════════════════════════════════
# 3. 正则表达式校验
# ══════════════════════════════════════════════════════════════

@app.get("/order/track")
def track_order(
    # WHY: regex 确保订单号格式正确（如 ORD-年月日-序号）
    #      格式不对的直接返回 422，不需要在代码里再判断
    order_id: str = Query(
        ...,
        regex=r"^ORD-\d{8}-\d{4}$",
        description="订单号，格式: ORD-YYYYMMDD-NNNN",
    ),
    # WHY: 手机号正则——1 开头 + 3-9 中一位 + 9 个数字
    phone: Optional[str] = Query(
        None,
        regex=r"^1[3-9]\d{9}$",
        description="11位手机号",
    ),
):
    """
    查询物流——正则校验订单号格式。
    WHY: 在接口层面拦截非法格式，减轻数据库压力。
    """
    return {
        "order_id": order_id,
        "phone": phone,
        "logistics": {"company": "顺丰快递", "status": "运输中"},
    }


# ══════════════════════════════════════════════════════════════
# 4. 别名与废弃标记
# ══════════════════════════════════════════════════════════════

@app.get("/tickets")
def list_tickets(
    # WHY: alias="q" 让 URL 可以是 ?q=关键词 而不是 ?keyword=关键词
    #      URL 参数名可以和 Python 变量名不同
    keyword: str = Query(None, alias="q", description="搜索关键词（URL 中用 q）"),
    # WHY: deprecated=True 在 Swagger 中灰色显示，提示前端迁移到新参数
    old_filter: Optional[str] = Query(
        None,
        deprecated=True,
        description="旧版筛选（已废弃，请用 status 参数）",
    ),
    status: Optional[str] = Query(None, description="工单状态"),
):
    """
    工单列表——展示别名和废弃标记。
    WHY: API 演进时，用 deprecated 标记旧参数而非直接删除，给前端缓冲期。
    """
    return {
        "keyword": keyword,
        "status": status,
        "results": [{"id": "TKT-001", "status": status or "全部"}],
    }


# ══════════════════════════════════════════════════════════════
# 5. 隐藏在文档中
# ══════════════════════════════════════════════════════════════

@app.get("/internal/search")
def internal_search(
    keyword: str = Query(...),
    # WHY: include_in_schema=False 让这个参数不在 Swagger 中出现
    #      用于内部调试参数，不向外部公开
    debug: bool = Query(
        False,
        include_in_schema=False,
        description="调试模式（仅内部使用）",
    ),
):
    """
    内部搜索——debug 参数在文档中不可见。
    """
    result = {"keyword": keyword, "results": []}
    if debug:
        result["_internal"] = {"query_time_ms": 12, "cache_hit": True}
    return result


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
