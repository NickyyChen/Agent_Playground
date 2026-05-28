# -*- coding: utf-8 -*-
"""
02_api_docs.py — FastAPI 交互式 API 文档
==========================================

【概念】什么是交互式 API 文档？
FastAPI 自动为你的 API 生成两份文档（无需额外代码）：
  - Swagger UI (/docs)  →  可视化界面，可直接在浏览器中"试用"每个 API
  - ReDoc (/redoc)      →  更清晰美观的只读文档，适合对外发布

两者都基于 OpenAPI 规范——这是行业标准的 API 描述协议。

【在智能客服中解决什么问题】
智能客服团队协作时，前端/后端/测试需要清晰的 API 接口说明。
Swagger UI 让测试可以在浏览器直接调接口验证；
ReDoc 可以发给第三方合作商作为对接文档。

【核心流程】
  FastAPI() 实例
  ┌─────────────────────────────────────┐
  │ title    →  显示在文档顶部              │
  │ description → 文档首页说明文字          │
  │ version  →  API 版本号                │
  │ openapi_tags →  分组标签（tags）        │
  │ docs_url → Swagger UI 路径（默认/docs）│
  │ redoc_url → ReDoc 路径（默认/redoc）   │
  └─────────────────────────────────────┘

【运行后访问】
  http://localhost:8000/docs    → Swagger UI（可交互试用）
  http://localhost:8000/redoc   → ReDoc（只读文档）
  http://localhost:8000/openapi.json → 原始 OpenAPI JSON

【测试案例】
  # 启动服务器
  python fastapi-basics/02_api_docs.py

  # 终端测试 API 接口
  curl http://localhost:8000/order/ORD001
  # → {"order_id":"ORD001","product":"漫步者 W820NB 无线降噪耳机","price":299.0,"status":"已签收"}

  curl -X POST http://localhost:8000/refund
  # → {"ticket_id":"TKT-20240001","status":"已受理"}

  curl http://localhost:8000/products/search
  # → [{"name":"漫步者 W820NB","price":299,"stock":120},...]

  # 浏览器访问自动生成的文档（最推荐的测试方式）
  open http://localhost:8000/docs    # Swagger UI — 页面里直接点 "Try it out" 交互式调用
  open http://localhost:8000/redoc   # ReDoc — 只读文档

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from fastapi import FastAPI

# WHY: docs_url="/docs" 是默认值，写出来是为了展示你可以自定义文档路径
#      openapi_url 是原始 JSON Schema 的路径，自定义 API 网关时需要它
app = FastAPI(
    title="好买电商客服 API",
    description="智能客服系统接口文档 —— 支持订单查询、退款处理、商品搜索",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# WHY: tags_metadata 让文档中的接口按业务模块分组，方便查找
tags_metadata = [
    {"name": "订单管理", "description": "订单查询、物流跟踪相关接口"},
    {"name": "退款售后", "description": "退款申请、售后工单相关接口"},
    {"name": "商品查询", "description": "商品搜索、详情查询相关接口"},
]
# 需要在 app 创建后单独设置（FastAPI 的 API 限制）
app.openapi_tags = tags_metadata


# WHY: tags=["订单管理"] 让这个路由在 Swagger UI 中归入"订单管理"分组
@app.get("/order/ORD001", tags=["订单管理"], summary="查询订单详情")
def get_order():
    """
    查询指定订单的详细信息。

    返回订单状态、商品详情、物流信息等。
    """
    return {
        "order_id": "ORD001",
        "product": "漫步者 W820NB 无线降噪耳机",
        "price": 299.0,
        "status": "已签收",
    }


@app.post("/refund", tags=["退款售后"], summary="提交退款申请")
def create_refund():
    """提交退款申请，返回工单编号。"""
    return {"ticket_id": "TKT-20240001", "status": "已受理"}


@app.get("/products/search", tags=["商品查询"], summary="搜索商品")
def search_products():
    """根据关键词搜索商品。"""
    return [
        {"name": "漫步者 W820NB", "price": 299, "stock": 120},
        {"name": "iPhone 15 手机壳", "price": 29.9, "stock": 500},
    ]


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
