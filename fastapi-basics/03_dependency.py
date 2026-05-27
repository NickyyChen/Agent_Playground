# -*- coding: utf-8 -*-
"""
03_dependency.py — 依赖注入：服务层解耦、鉴权、数据库连接
=========================================================

【概念】
依赖注入（Dependency Injection, DI）是 FastAPI 最强大的特性之一。
不做 DI：每个路由函数内部 new 一个 Service → 紧耦合、不可测试
做 DI：路由声明"我需要 X 服务"，FastAPI 自动注入 → 松耦合、可替换

FastAPI 的 Depends() 可以用在任何地方：
  - 路由参数：def route(db: Session = Depends(get_db))
  - 鉴权校验：def route(user: User = Depends(get_current_user))
  - 路径装饰器：@app.get("/", dependencies=[Depends(verify_token)])

【在智能客服中的应用】
- 鉴权：每个 API 调用都必须验证 JWT Token
- 共享资源：数据库连接池整个应用共享一个实例
- 业务逻辑复用：多个路由都需要"获取当前客服信息"

【pip install】
pip install fastapi uvicorn

【ASCII 架构图】

  HTTP 请求
     │
     ▼
  ┌──────────────────────────────────────┐
  │         FastAPI 依赖解析链             │
  │                                       │
  │  @app.get("/order/{id}")             │
  │  def get_order(                      │
  │      order_id: str,                  │
  │      db: DB = Depends(get_db),       │  ← ① 注入数据库连接
  │      user: User = Depends(auth),     │  ← ② 注入当前用户(鉴权)
  │      svc: OrderService = Depends(),  │  ← ③ 注入业务服务
  │  )                                   │
  │                                       │
  │  依赖可以嵌套:                          │
  │  OrderService → 需要 DB 连接            │
  │  auth → 需要验证 Header 中的 Token      │
  │  FastAPI 自动解析整个依赖树             │
  └──────────────────────────────────────┘
"""

import uvicorn
from fastapi import FastAPI, Depends, Header, HTTPException
from typing import Optional


app = FastAPI(title="依赖注入学习")


# ══════════════════════════════════════════════════════════════
# 1. 简单依赖 —— 共享的配置/连接
# WHY: 用 Depends 注入比在每个函数里 import + 初始化更灵活——
#      测试时可以替换为 Mock 对象，且只需改一处。
# ══════════════════════════════════════════════════════════════

def get_db():
    """
    模拟数据库连接。
    WHY: 生产环境这里返回真正的数据库 session，
         测试环境返回内存 SQLite——Depends 让替换变得简单。
    """
    db = {
        "ORD001": {"product": "耳机", "price": 299},
        "ORD002": {"product": "手机壳", "price": 49},
    }
    try:
        yield db  # WHY: yield 保证 finally 中的清理逻辑一定执行
    finally:
        pass  # 生产环境: db.close()


@app.get("/item/{order_id}")
def get_item(order_id: str, db: dict = Depends(get_db)):
    """
    通过 Depends(get_db) 注入数据库连接。
    路由函数不需要知道 db 怎么来的——只管用。
    """
    item = db.get(order_id)
    if not item:
        raise HTTPException(status_code=404, detail="找不到")
    return item


# ══════════════════════════════════════════════════════════════
# 2. 鉴权依赖 —— 请求级的状态校验
# WHY: 鉴权是"几乎每个接口都需要"的逻辑——
#      用 Depends 复用，不用在每个路由里重复 if token_valid()。
# ══════════════════════════════════════════════════════════════

# ─── 模拟用户数据库 ──────────────────────────────
VALID_TOKENS = {
    "token-admin-001": {"user_id": "U1", "role": "admin", "name": "管理员"},
    "token-agent-002": {"user_id": "U2", "role": "agent", "name": "客服小王"},
}

def get_current_user(authorization: str = Header(None)) -> dict:
    """
    从 HTTP Header 中提取 Token 并验证。
    WHY: Header(None) 表示从请求头 Authorization 字段取值，允许为空。
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证 Token")

    # WHY: "Bearer xxx" → 去掉 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    user = VALID_TOKENS.get(token)

    if not user:
        raise HTTPException(status_code=403, detail="Token 无效或已过期")

    return user


@app.get("/me")
def whoami(user: dict = Depends(get_current_user)):
    """需要鉴权的接口——不写一行鉴权逻辑，Depends 自动搞定"""
    return {"authenticated": True, **user}


@app.get("/admin/dashboard")
def admin_only(user: dict = Depends(get_current_user)):
    """
    管理员专属接口。
    WHY: 鉴权由 Depends 统一处理，这里只需检查角色——
         "鉴权"和"授权"分离，两者都是可复用的 Depends。
    """
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可访问")
    return {"message": f"欢迎 {user['name']}", "stats": {"total_orders": 1234}}


# ══════════════════════════════════════════════════════════════
# 3. 类作为依赖 —— 业务服务注入
# WHY: 复杂的业务逻辑封装在 Service 类中——
#      路由函数通过 Depends 拿到 Service 实例，
#      业务逻辑和 HTTP 层彻底分离。
# ══════════════════════════════════════════════════════════════

class OrderService:
    """
    订单业务服务——封装所有订单相关的逻辑。
    WHY: 把业务逻辑从路由函数中抽出来——
         路由只负责 HTTP 层（解析参数、返回响应），
         Service 只负责业务层（查数据、算金额、校验规则）。
    """
    def __init__(self, db: dict = Depends(get_db)):
        # WHY: Service 也通过 Depends 拿到 DB——
        #      FastAPI 自动解析嵌套依赖链！
        self.db = db

    def get_detail(self, order_id: str) -> dict:
        order = self.db.get(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")
        return order

    def list_all(self) -> list[dict]:
        return [{"order_id": k, **v} for k, v in self.db.items()]


@app.get("/orders/{order_id}")
def get_order_svc(order_id: str, svc: OrderService = Depends()):
    """
    通过 Depends() 注入 Service 实例。
    FastAPI 自动解析 OrderService.__init__ 的依赖链 (Depends(get_db))。
    """
    return svc.get_detail(order_id)


@app.get("/orders")
def list_orders_svc(svc: OrderService = Depends()):
    return {"orders": svc.list_all()}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="info")
