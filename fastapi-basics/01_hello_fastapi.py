# -*- coding: utf-8 -*-
"""
01_hello_fastapi.py — 路由基础：路径参数、查询参数、请求体
=========================================================

【概念】
FastAPI 路由用装饰器定义 HTTP 端点：
  @app.get("/path/{param}")     → GET 请求，路径参数
  @app.post("/path")            → POST 请求，请求体用 Pydantic Model 校验
  /path?key=value               → 查询参数（函数签名中没在路径里的参数）

路径参数 vs 查询参数：
  路径参数：/order/ORD001 → def get(order_id: str)  → 资源标识
  查询参数：/search?keyword=耳机&page=1 → def search(keyword: str, page: int=1) → 过滤/分页

运行：python fastapi-basics/01_hello_fastapi.py
访问：http://localhost:8000/docs  (自动生成的 Swagger UI)

【pip install】
pip install fastapi uvicorn

【ASCII 架构图】

  HTTP 请求                                     FastAPI 处理
  ─────────────────────────────────────────────────────────

  GET /order/ORD001?detail=true
      │                    │
      │  路径参数           │  查询参数
      │  {order_id}=ORD001 │  detail=true
      ▼                    ▼
  ┌─────────────────────────────────────────┐
  │  @app.get("/order/{order_id}")          │
  │  def get_order(order_id: str,           │
  │                detail: bool = False)    │
  └─────────────────────────────────────────┘
      │
      ▼
  {"order_id": "ORD001", "detail": true}
"""

import uvicorn
from fastapi import FastAPI, Query, Path

# WHY: FastAPI() 是整个应用的核心——所有路由、中间件都注册在它上面
app = FastAPI(
    title="好买电商客服 API",
    description="Agent-Playground FastAPI 学习 Demo",
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════
# 1. 最简单的 GET 端点
# ══════════════════════════════════════════════════════════════

@app.get("/")
def root():
    """根路径——不需要任何参数"""
    return {"message": "欢迎来到好买电商客服 API"}


# ══════════════════════════════════════════════════════════════
# 2. 路径参数 —— 资源标识
# WHY: 路径参数是 URL 的一部分，标识"哪个资源"。
#      FastAPI 自动将 URL 中的 {order_id} 绑定到函数参数 order_id。
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(
    order_id: str = Path(..., description="订单号，如 ORD20240001"),
):
    """
    获取订单详情。
    Path(...) 中 ... 表示必填，description 会出现在 Swagger 文档中。
    """
    # 模拟数据库查询
    mock_db = {
        "ORD20240001": {"product": "漫步者 W820NB", "price": 299, "status": "已签收"},
    }
    order = mock_db.get(order_id)
    if not order:
        return {"error": f"订单 {order_id} 不存在"}
    return {"order_id": order_id, **order}


# ══════════════════════════════════════════════════════════════
# 3. 查询参数 —— 过滤/分页/开关
# WHY: 查询参数放在 ? 后面，是可选的过滤条件。
#      函数签名中没在路径里的参数自动成为查询参数。
# ══════════════════════════════════════════════════════════════

@app.get("/products/search")
def search_products(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    category: str = Query(None, description="品类筛选，如'耳机'"),
    min_price: float = Query(None, ge=0, description="最低价"),
    max_price: float = Query(None, le=10000, description="最高价"),
    page: int = Query(1, ge=1, description="页码"),
):
    """
    搜索商品——展示查询参数的多重用法。
    Query 支持校验：min_length, ge(>=), le(<=) 等。
    """
    return {
        "keyword": keyword,
        "filters": {"category": category, "min_price": min_price,
                    "max_price": max_price},
        "page": page,
        "results": [{"name": "漫步者 W820NB", "price": 299}],
    }


# ══════════════════════════════════════════════════════════════
# 4. POST 端点 —— 请求体
# WHY: POST 用于创建/提交操作，数据放在请求体中。
#      用 Pydantic Model 做类型校验——FastAPI 自动解析 JSON 并校验。
# ══════════════════════════════════════════════════════════════

from pydantic import BaseModel, Field

class RefundRequest(BaseModel):
    """
    退款申请的数据模型。
    WHY: Pydantic 定义字段类型和校验规则——
         前端传错类型/漏字段时，FastAPI 自动返回 422 错误。
    """
    order_id: str = Field(..., min_length=5, description="订单号")
    reason: str = Field(..., min_length=5, max_length=200, description="退货原因")
    refund_amount: float = Field(..., gt=0, description="退款金额，必须 >0")


@app.post("/refund")
def create_refund(req: RefundRequest):
    """
    提交退款申请。
    FastAPI 自动：① 解析 JSON 请求体 ② 校验字段 ③ 注入 Pydantic 对象
    """
    return {
        "status": "submitted",
        "ticket_id": "TKT-20240001",
        "order_id": req.order_id,
        "amount": req.refund_amount,
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
