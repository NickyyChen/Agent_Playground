# -*- coding: utf-8 -*-
"""
06_dependency_injection.py — FastAPI 依赖注入
===============================================

【概念】什么是依赖注入（DI）？
依赖注入是一种设计模式：函数不需要自己创建依赖对象，而是由框架"注入"进来。
FastAPI 用 Depends() 实现依赖注入。

  不用 DI：                  用 DI：
  def handler():             def handler(
    db = connect_db()    →     db = Depends(get_db)
    auth = check_token()      )

【在智能客服中解决什么问题】
智能客服的每个接口都可能需要：
  - 验证用户登录状态（从 Header/Cookie 中读 token）
  - 获取数据库连接
  - 检查权限（普通用户 vs 管理员）
  - 记录日志
如果每个接口都重复写这些代码，会大量重复。DI 让这些公共逻辑"注入"到每个接口。

【核心流程】

  请求进来
      │
      ▼
  ┌──────────────────────────────┐
  │  依赖链（可以多层嵌套）        │
  │                              │
  │  get_db()                    │  1. 获取数据库连接
  │    ↓                         │
  │  get_current_user(token)     │  2. 从 token 解析用户
  │    ↓                         │
  │  check_is_admin(user)        │  3. 检查管理员权限
  │    ↓                         │
  │  注入到路由函数               │
  └──────────────────────────────┘
      │
      ▼
  @app.get("/admin/reports")
  def admin_reports(user = Depends(get_current_user)):
      ...

  ★ 每层依赖独立可复用、可测试！

【测试案例】
  # 启动服务器
  python fastapi-basics/06_dependency_injection.py

  # 查看个人信息——不带 token → 401
  curl http://localhost:8000/me
  # → 401 Unauthorized

  # 带有效 token（客服）
  curl http://localhost:8000/me -H "Authorization: Bearer token-agent-002"
  # → {"message":"你好 李客服！","profile":{"name":"李客服","role":"agent"}}

  # 管理员查看报表
  curl http://localhost:8000/admin/reports -H "Authorization: Bearer token-admin-001"
  # → 管理员张经理可查看报表数据

  # 客服访问管理员接口 → 403
  curl http://localhost:8000/admin/reports -H "Authorization: Bearer token-agent-002"
  # → 403 Forbidden（非管理员）

  # 客服工作台
  curl http://localhost:8000/agent/dashboard -H "Authorization: Bearer token-agent-002"
  # → {"message":"客服 李客服，今日待处理工单：5 单"}

  # 分页查询（使用公共分页依赖）
  curl "http://localhost:8000/orders?page=2&page_size=10"
  # → {"page":2,"page_size":10,"items":[]}

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from typing import Optional
from fastapi import FastAPI, Depends, Header, HTTPException, status

app = FastAPI(title="好买电商客服 API - 依赖注入")


# ══════════════════════════════════════════════════════════════
# 1. 最简单的依赖——公共参数提取
# ══════════════════════════════════════════════════════════════

# WHY: 把分页参数封装成可复用的依赖，任何需要分页的接口直接调用
#      参数声明了默认值(1, 20)，不传时使用默认值
def pagination(page: int = 1, page_size: int = 20):
    """
    分页参数依赖。
    返回一个闭包函数——FastAPI 会自动调用它，注入返回值。
    """
    return {"page": page, "page_size": page_size}


@app.get("/orders")
def list_orders(paging: dict = Depends(pagination)):
    """
    查询订单列表——分页参数由 pagination 依赖注入。
    不需要在函数签名里重复写 page, page_size。
    """
    # 模拟分页查询
    return {"page": paging["page"], "page_size": paging["page_size"], "items": []}


# ══════════════════════════════════════════════════════════════
# 2. 带逻辑的依赖——从 Header 解析用户
# ══════════════════════════════════════════════════════════════

# WHY: 模拟用户数据——实际项目中从数据库查询
fake_users = {
    "token-admin-001": {"name": "张经理", "role": "admin"},
    "token-agent-002": {"name": "李客服", "role": "agent"},
    "token-user-003": {"name": "王小明", "role": "user"},
}


def get_current_user(authorization: Optional[str] = Header(None)):
    """
    从请求头 Authorization 中解析当前用户。
    WHY: 这个依赖可以复用在所有需要登录的接口上——
         只要加上 user = Depends(get_current_user) 就行。
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证 token，请在 Header 中传入 Authorization",
        )
    # 去掉 "Bearer " 前缀
    token = authorization.replace("Bearer ", "")
    user = fake_users.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证 token",
        )
    return user


# ══════════════════════════════════════════════════════════════
# 3. 依赖嵌套——检查管理员权限
# ══════════════════════════════════════════════════════════════

def require_admin(user: dict = Depends(get_current_user)):
    """
    检查当前用户是否是管理员。
    WHY: 这里依赖了 get_current_user——展示依赖的级联使用。
         FastAPI 会自动先解析 get_current_user，再把结果传给这个函数。
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{user['name']} 不是管理员，无权访问",
        )
    return user


# ══════════════════════════════════════════════════════════════
# 4. 带参数的依赖工厂
# ══════════════════════════════════════════════════════════════

# WHY: 有时候依赖需要外部参数——用工厂函数返回闭包
def has_role(required_role: str):
    """
    依赖工厂——根据所需角色创建不同的权限检查器。
    用法：Depends(has_role("admin"))
    """

    def checker(user: dict = Depends(get_current_user)):
        if user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {required_role} 权限",
            )
        return user

    return checker


# ══════════════════════════════════════════════════════════════
# 路由
# ══════════════════════════════════════════════════════════════

@app.get("/me")
def my_profile(user: dict = Depends(get_current_user)):
    """
    查看个人信息——需要登录。
    user 由 get_current_user 依赖自动注入。
    """
    return {"message": f"你好 {user['name']}！", "profile": user}


@app.get("/admin/reports")
def admin_reports(user: dict = Depends(require_admin)):
    """
    查看管理报表——需要管理员。
    WHY: require_admin 内部调用 get_current_user——两层级联依赖。
    """
    return {
        "message": f"管理员 {user['name']}，这是本月报表",
        "reports": {"total_orders": 15420, "refund_rate": "2.3%"},
    }


@app.get("/agent/dashboard")
def agent_dashboard(user: dict = Depends(has_role("agent"))):
    """
    客服工作台——需要客服角色。
    WHY: has_role("agent") 是依赖工厂模式——返回专门检查 agent 角色的闭包。
    """
    return {"message": f"客服 {user['name']}，今日待处理工单：5 单"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
