# -*- coding: utf-8 -*-
"""
15_response_model.py — FastAPI 响应模型
==========================================

【概念】什么是响应模型？
响应模型（response_model）控制 API **返回给客户端的数据结构和字段**。
用 response_model 参数声明后，FastAPI 会：
  1. 过滤掉多余的字段（不在模型中的字段不会返回）
  2. 自动转换类型（如 datetime → ISO 字符串）
  3. 在 Swagger 文档中显示响应结构

【在智能客服中解决什么问题】
安全场景——有些字段绝不能返回给客户端：
  - 用户的密码哈希
  - 内部成本价（只需返回售价）
  - 其他用户的隐私数据
用响应模型可以自动"裁剪"响应数据，防止信息泄露。

【核心流程】

  数据库对象 (含敏感字段)         Response Model (公开字段)        API 响应
  ───────────────────────       ────────────────────────       ──────────
  {                             {                             {
    "username": "zhang",    →    "username": str,         →     "username": "zhang",
    "password_hash": "xxx",     }                                 "role": "维护"
    "role": "agent",
    "internal_id": 42,
  }
  ★ response_model 自动过滤掉 password_hash 和 internal_id！

【测试案例】
  # 启动服务器
  python fastapi-basics/15_response_model.py

  # 查询用户——敏感字段自动过滤
  curl http://localhost:8000/user/zhangwei
  # → {"username":"zhangwei","full_name":"张伟","email":"zhangwei@haomai.com","role":"客服主管"}
  #   ★ password_hash 和 salary 不会出现在响应中！

  # 工单列表——内部字段被过滤
  curl http://localhost:8000/tickets
  # → 返回数组，每个元素只有 ticket_id, title, status, created_at
  #   ★ _internal_handler_id 和 priority_score 不会暴露

  # 排除特定字段
  curl http://localhost:8000/order/ORD001
  # → 有 order_id, product, price，但没有 cost_price 和 supplier

  # 只包含指定字段
  curl http://localhost:8000/agent/001
  # → {"username":"li_xiaomei","role":"客服"}  ← 只有两个字段

  # 去掉 None 值
  curl http://localhost:8000/product/1
  # → {"name":"漫步者 W820NB","price":299}  ← discount_price 等 None 字段不返回

【pip install】
pip install fastapi uvicorn pydantic
"""

import uvicorn
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="好买电商客服 API - 响应模型")


# ══════════════════════════════════════════════════════════════
# 1. 基础响应模型——过滤敏感字段
# ══════════════════════════════════════════════════════════════

# 模拟数据库中的用户模型（含敏感字段）
class UserInDB(BaseModel):
    username: str
    password_hash: str  # ← 绝对不能返回给客户端！
    full_name: str
    email: str
    role: str
    salary: float  # ← 内部字段，不应暴露


# WHY: 响应模型只包含可以公开的字段
class UserPublic(BaseModel):
    """对外公开的用户信息。"""
    username: str
    full_name: str
    email: str
    role: str


@app.get("/user/{username}", response_model=UserPublic)
def get_user(username: str):
    """
    查询用户信息。
    WHY: response_model=UserPublic 确保 password_hash 和 salary 不会返回给客户端。
         即使函数返回了包含敏感字段的 UserInDB，FastAPI 也会自动过滤。
    """
    # 模拟数据库查询——返回完整对象包含敏感字段
    user_from_db = UserInDB(
        username="zhangwei",
        password_hash="$2b$12$LJ3m...secret",
        full_name="张伟",
        email="zhangwei@haomai.com",
        role="客服主管",
        salary=15000.0,
    )
    return user_from_db  # ← FastAPI 自动过滤，只返回 UserPublic 的字段


# ══════════════════════════════════════════════════════════════
# 2. 列表响应模型
# ══════════════════════════════════════════════════════════════

class TicketSummary(BaseModel):
    """工单摘要——列表中的每个元素。"""
    ticket_id: str
    title: str
    status: str
    created_at: datetime


# WHY: List[TicketSummary] 表示返回的是 TicketSummary 数组
@app.get("/tickets", response_model=List[TicketSummary])
def list_tickets():
    """
    查询工单列表。
    WHY: response_model=List[TicketSummary] 确保列表中每个元素都被过滤。
    """
    return [
        {
            "ticket_id": "TKT-001",
            "title": "蓝牙耳机杂音问题",
            "status": "处理中",
            "created_at": datetime(2024, 1, 15, 10, 30),
            # WHY: 这里故意多返回一个内部字段——会被 response_model 过滤掉
            "_internal_handler_id": 42,
        },
        {
            "ticket_id": "TKT-002",
            "title": "订单未收到货",
            "status": "待分配",
            "created_at": datetime(2024, 1, 16, 14, 20),
            "priority_score": 85,  # ← 内部优先级评分，不对外暴露
        },
    ]


# ══════════════════════════════════════════════════════════════
# 3. response_model_exclude——排除特定字段
# ══════════════════════════════════════════════════════════════

class OrderDetail(BaseModel):
    order_id: str
    product: str
    price: float
    cost_price: float  # 成本价——通常不对外
    supplier: str  # 供应商——内部信息


@app.get(
    "/order/{order_id}",
    # WHY: response_model_exclude 在路由层面排除指定字段
    #      比单独建一个 response model 更灵活
    response_model=OrderDetail,
    response_model_exclude={"cost_price", "supplier"},
)
def get_order(order_id: str):
    """查询订单——排除成本和供应商字段。"""
    return OrderDetail(
        order_id=order_id,
        product="漫步者 W820NB",
        price=299,
        cost_price=180,
        supplier="深圳声学科技",
    )


# ══════════════════════════════════════════════════════════════
# 4. response_model_include——只包含指定字段
# ══════════════════════════════════════════════════════════════

@app.get(
    "/agent/{agent_id}",
    response_model=UserPublic,
    # WHY: include 只保留指定字段——快速出轻量版接口
    response_model_include={"username", "role"},
)
def get_agent(agent_id: str):
    """查询客服信息——只返回用户名和角色。"""
    return UserPublic(
        username="li_xiaomei",
        full_name="李小美",
        email="lixiaomei@haomai.com",
        role="客服",
    )


# ══════════════════════════════════════════════════════════════
# 5. response_model_exclude_none——去掉 None 值
# ══════════════════════════════════════════════════════════════

class ProductInfo(BaseModel):
    name: str
    price: float
    discount_price: Optional[float] = None
    description: Optional[str] = None
    spec_url: Optional[str] = None


@app.get(
    "/product/{product_id}",
    response_model=ProductInfo,
    # WHY: exclude_none=True 自动去掉值为 None 的字段
    #      减小响应体积，前端不需要处理 null 字段
    response_model_exclude_none=True,
)
def get_product(product_id: int):
    """查询商品——None 字段不返回。"""
    return ProductInfo(
        name="漫步者 W820NB",
        price=299,
        # discount_price, description, spec_url 都是 None
        # → 不会出现在响应中
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
