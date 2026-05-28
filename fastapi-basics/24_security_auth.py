# -*- coding: utf-8 -*-
"""
24_security_auth.py — FastAPI 安全认证
=========================================

【概念】FastAPI 安全认证
FastAPI 提供了 fastapi.security 模块，内置多种认证方案：

  认证方式              适用场景
  ─────────────────────────────────────────────
  OAuth2PasswordBearer   前后端分离的 token 认证（最常用）
  OAuth2AuthorizationCode 第三方登录（微信/企业微信）
  APIKeyHeader           服务间调用（API Key）
  HTTPBasic              简单场景（Base64 编码，不推荐）
  HTTPBearer             自定义 Bearer token

【在智能客服中解决什么问题】
  - 客服登录：OAuth2 密码模式 + JWT token
  - 内部服务调用：API Key 认证
  - 权限分级：普通客服 / 客服主管 / 管理员

【核心流程】

  OAuth2 Password 流程：
  ┌──────────┐                         ┌──────────┐
  │  客户端   │                         │  API 服务 │
  └────┬─────┘                         └────┬─────┘
       │  POST /login                       │
       │  username + password               │
       ├───────────────────────────────────►│
       │                                    │ 验证密码
       │  {"access_token": "eyJ...",        │ 生成 JWT
       │   "token_type": "bearer"}          │
       │◄───────────────────────────────────┤
       │                                    │
       │  GET /tickets                      │
       │  Authorization: Bearer eyJ...       │
       ├───────────────────────────────────►│
       │                                    │ 校验 JWT → 解析用户信息
       │  [...工单数据...]                   │
       │◄───────────────────────────────────┤

JWT (JSON Web Token) 结构：
  eyJhbGciOi... . eyJzdWIiOi... . SflKxwR...
  └─ Header ──┘   └─ Payload ─┘   └─ Signature ─┘
                    {user, role,
                     exp(过期时间)}

【测试案例】
  # 启动服务器
  python fastapi-basics/24_security_auth.py

  # ── OAuth2 密码登录流程 ──

  # 1. 登录获取 token（客服李小美）
  curl -X POST http://localhost:8000/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=lixiaomei&password=agent123"
  # → {"access_token":"ey...","token_type":"bearer","expires_in":1800}
  #   ★ 记下 access_token 的值，后续请求用

  # 2. 用 token 查看个人信息
  TOKEN="<上面获取的 access_token>"
  curl http://localhost:8000/me \
    -H "Authorization: Bearer $TOKEN"
  # → {"username":"lixiaomei","full_name":"李小美","role":"agent"}

  # 3. 无 token → 401
  curl http://localhost:8000/me
  # → 401 Unauthorized

  # 4. 查看工单列表（需要登录）
  curl http://localhost:8000/tickets \
    -H "Authorization: Bearer $TOKEN"
  # → {"operator":"李小美","role":"agent","items":[...]}

  # ── 权限分级 ──

  # 管理员张伟登录
  curl -X POST http://localhost:8000/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=zhangwei&password=admin123"
  # → 获取管理员 token

  # 管理员查看所有用户
  ADMIN_TOKEN="<管理员 token>"
  curl http://localhost:8000/admin/users \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  # → {"users":[{...},{...}]}

  # 客服访问管理接口 → 403
  curl http://localhost:8000/admin/users \
    -H "Authorization: Bearer $TOKEN"
  # → 403 Forbidden（不是管理员）

  # ── API Key 认证（服务间调用）──

  # 用 CRM 系统的 API Key 访问内部订单接口
  curl http://localhost:8000/internal/orders \
    -H "X-API-Key: hm-crm-2024-secret"
  # → {"caller":"CRM系统","permissions":["read_orders"],"orders":[...]}

  # 错误的 API Key → 403
  curl http://localhost:8000/internal/orders \
    -H "X-API-Key: wrong-key"
  # → 403 Forbidden

  # ── 公开接口（无需认证）──
  curl http://localhost:8000/public/faq
  # → 返回 FAQ 列表

【pip install】
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] python-multipart
"""

import uvicorn
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    APIKeyHeader,
)
from pydantic import BaseModel

app = FastAPI(title="好买电商客服 API - 安全认证")


# ══════════════════════════════════════════════════════════════
# 1. 模拟用户数据库
# ══════════════════════════════════════════════════════════════

# WHY: 实际项目中密码存哈希值（bcrypt），这里为演示简化
fake_users_db = {
    "zhangwei": {
        "username": "zhangwei",
        "password": "admin123",  # ← 实际项目用 bcrypt 哈希
        "full_name": "张伟",
        "role": "admin",
    },
    "lixiaomei": {
        "username": "lixiaomei",
        "password": "agent123",
        "full_name": "李小美",
        "role": "agent",
    },
}


# ══════════════════════════════════════════════════════════════
# 2. JWT 工具函数（简化版）
# ══════════════════════════════════════════════════════════════

# WHY: 简化版 JWT 实现——实际项目用 python-jose 库
#      这里用简单编码模拟 JWT 流程，避免额外依赖
import base64
import json

SECRET_KEY = "haomai-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    创建 JWT token。
    WHY: JWT 包含用户信息（sub）和过期时间（exp），
         服务端用密钥签名，防止伪造。
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire.isoformat()})

    # 简化版：base64 编码 payload + 简单签名
    payload_b64 = base64.b64encode(json.dumps(to_encode).encode()).decode()
    signature = base64.b64encode(
        f"{payload_b64}{SECRET_KEY}".encode()
    ).decode()[:16]
    return f"{payload_b64}.{signature}"


def decode_access_token(token: str):
    """
    解码并验证 JWT token。
    WHY: 验证签名防止伪造，检查过期时间防止 token 滥用。
    """
    try:
        payload_b64, signature = token.split(".")
        # 验证签名
        expected_sig = base64.b64encode(
            f"{payload_b64}{SECRET_KEY}".encode()
        ).decode()[:16]
        if signature != expected_sig:
            return None

        payload = json.loads(base64.b64decode(payload_b64).decode())
        expire_time = datetime.fromisoformat(payload["exp"])
        if datetime.utcnow() > expire_time:
            return None  # token 已过期

        return payload
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════
# 3. OAuth2 密码模式 —— 最常用的认证方案
# ══════════════════════════════════════════════════════════════

# WHY: tokenUrl 指向登录接口的路径——Swagger UI 中"Authorize"按钮会跳转到这里
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/login",
    description="请输入用户名和密码获取 token",
)


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    从 token 中解析当前用户——核心认证依赖。
    WHY: 这个函数可以注入到任何需要认证的路由中——
         只需要在函数签名加 user = Depends(get_current_user)。
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效或已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username is None or username not in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 中的用户信息无效",
        )

    return fake_users_db[username]


# ══════════════════════════════════════════════════════════════
# 4. 登录接口 —— 返回 JWT token
# ══════════════════════════════════════════════════════════════

@app.post("/login")
def login(
    # WHY: OAuth2PasswordRequestForm 自动从表单提取 username 和 password
    #      Swagger UI 的 Authorize 按钮用的就是这个格式
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    客服登录——返回 JWT token。
    WHY: OAuth2PasswordRequestForm 是标准登录表单——
         username + password + grant_type(=password)。
    """
    user = fake_users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ══════════════════════════════════════════════════════════════
# 5. API Key 认证 —— 服务间调用
# ══════════════════════════════════════════════════════════════

# WHY: APIKeyHeader 从请求头 X-API-Key 读取 key——适合服务间调用
api_key_scheme = APIKeyHeader(name="X-API-Key", description="服务间调用的 API Key")

# WHY: 模拟合法的 API Key 列表——实际项目存在数据库或配置中
valid_api_keys = {
    "hm-crm-2024-secret": {"service": "CRM系统", "permissions": ["read_orders"]},
    "hm-wms-2024-secret": {"service": "WMS仓库系统", "permissions": ["read_orders", "update_logistics"]},
}


def verify_api_key(api_key: str = Depends(api_key_scheme)):
    """
    验证 API Key——服务间调用的认证。
    """
    service_info = valid_api_keys.get(api_key)
    if not service_info:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无效的 API Key",
        )
    return service_info


# ══════════════════════════════════════════════════════════════
# 6. 需要认证的路由
# ══════════════════════════════════════════════════════════════

@app.get("/me")
def read_current_user(user: dict = Depends(get_current_user)):
    """
    查看当前登录用户信息。
    WHY: user 依赖注入自动完成 token 解析——业务代码无需关心认证细节。
    """
    return {
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


@app.get("/tickets")
def list_tickets(user: dict = Depends(get_current_user)):
    """
    查询工单列表——需要登录。
    WHY: Depends(get_current_user) 保证只有登录用户能访问。
    """
    return {
        "operator": user["full_name"],
        "role": user["role"],
        "items": [
            {"id": "TKT-001", "title": "蓝牙耳机杂音", "status": "处理中"},
            {"id": "TKT-002", "title": "未收到货", "status": "待分配"},
        ],
    }


@app.get("/admin/users")
def list_all_users(user: dict = Depends(get_current_user)):
    """
    查看所有用户——仅管理员。
    WHY: 在路由内做角色检查——只允许 admin 角色。
    """
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"用户 {user['username']} 不是管理员，无权查看所有用户",
        )

    # 返回脱敏后的用户列表（不包含密码）
    return {
        "users": [
            {"username": u["username"], "full_name": u["full_name"], "role": u["role"]}
            for u in fake_users_db.values()
        ]
    }


# API Key 认证的服务间调用
@app.get("/internal/orders")
def internal_get_orders(service: dict = Depends(verify_api_key)):
    """
    内部接口——供 CRM/WMS 系统调用。
    WHY: API Key 认证适合机器间通信——不需要人工登录。
    """
    return {
        "caller": service["service"],
        "permissions": service["permissions"],
        "orders": [
            {"id": "ORD001", "status": "已发货"},
            {"id": "ORD002", "status": "待付款"},
        ],
    }


@app.get("/public/faq")
def public_faq():
    """
    公开接口——不需要认证。
    WHY: 不是所有接口都需要认证，公开信息（FAQ/商品详情）可以直接访问。
    """
    return {
        "faq": [
            {"q": "如何申请退款？", "a": "在订单详情页点击'申请退款'..."},
            {"q": "多久能收到退款？", "a": "审核通过后 3-5 个工作日..."},
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
