# -*- coding: utf-8 -*-
"""
25_testing.py — FastAPI 测试
===============================

【概念】FastAPI 测试
FastAPI 基于 Starlette 的 TestClient，可以**不启动服务器**直接测试 API。
测试覆盖：
  - 单元测试：测试单个路由/函数的逻辑
  - 集成测试：测试完整的请求-响应流程
  - 端到端测试：模拟真实客户端行为

TestClient 本质上是 ASGI 协议的模拟客户端——不经过网络，直接调用应用。

【在智能客服中解决什么问题】
客服 API 需要保证：
  - 订单查询返回正确的数据结构
  - 退款申请在非法参数时返回 422
  - 认证接口正确拒绝无 token 的请求
  - 权限检查正确拦截非管理员

【核心流程】

  TestClient(app)  ← 包装 FastAPI 应用
      │
      ▼
  client.get("/order/ORD001")     →  response.status_code, response.json()
  client.post("/refund", json={})  →  验证 422 校验
  client.post("/login", data={})   →  验证 token 返回

  ★ 不需要 uvicorn.run()，不需要端口——直接 Python 调用！

【测试案例】
  # 方式1：直接运行文件（自动执行内置测试套件）
  python fastapi-basics/25_testing.py
  # → 输出 5 组共 19 个测试结果，全部通过后自动启动服务器

  # 方式2：用 TestClient 手动测试（Python 交互式）
  python -c "
  from fastapi.testclient import TestClient
  import importlib.util
  spec = importlib.util.spec_from_file_location('m', 'fastapi-basics/25_testing.py')
  mod = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(mod)
  c = TestClient(mod.app)
  # GET 正常请求
  print(c.get('/order/ORD001').json())
  # → {'order_id': 'ORD001', 'product': '蓝牙耳机', ...}
  # GET 404
  print(c.get('/order/NOTEXIST').status_code)
  # → 404
  # POST 正常请求
  print(c.post('/refund', json={'order_id':'ORD001','reason':'质量问题需要退货','amount':299}).json())
  # → {'ticket_id': 'TKT-ORD001', ...}
  # POST 校验失败 → 422
  print(c.post('/refund', json={'order_id':'ORD001'}).status_code)
  # → 422
  # 无 token → 401
  print(c.get('/me').status_code)
  # → 401
  # 有效 token → 200
  print(c.get('/me', headers={'Authorization': 'Bearer admin'}).json())
  # → {'username': 'admin', 'role': 'admin'}
  "

  # 方式3：用 pytest（需要 pip install pytest httpx）
  # python -m pytest fastapi-basics/25_testing.py -v

【pip install】
pip install fastapi uvicorn httpx
"""

import uvicorn
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# 1. 构建被测试的应用（与前面各 demo 逻辑一致）
# ══════════════════════════════════════════════════════════════

app = FastAPI(title="好买电商客服 API - 测试")

# 模拟数据
db_orders = {
    "ORD001": {"product": "蓝牙耳机", "price": 299, "status": "已签收"},
    "ORD002": {"product": "手机壳", "price": 29.9, "status": "待付款"},
}

# 认证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)

fake_users = {"admin": {"username": "admin", "role": "admin"}}


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    if not token:
        return None
    payload = token  # 简化：token 直接当用户名
    return fake_users.get(payload)


# Pydantic 模型
class RefundRequest(BaseModel):
    order_id: str = Field(..., min_length=5, max_length=20)
    reason: str = Field(..., min_length=5, max_length=500)
    amount: float = Field(..., gt=0)


# 路由
@app.get("/order/{order_id}")
def get_order(order_id: str):
    """查询订单。"""
    order = db_orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"订单 {order_id} 不存在")
    return {"order_id": order_id, **order}


@app.post("/refund")
def create_refund(refund: RefundRequest):
    """提交退款。"""
    if refund.order_id not in db_orders:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "ticket_id": f"TKT-{refund.order_id}",
        "status": "已受理",
        "amount": refund.amount,
    }


@app.get("/me")
def read_me(user: dict = Depends(get_current_user)):
    """查看个人信息——需要登录。"""
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return {"username": user["username"], "role": user["role"]}


# ══════════════════════════════════════════════════════════════
# 2. 测试套件
# ══════════════════════════════════════════════════════════════

def run_tests():
    """
    运行所有测试——展示 TestClient 的基本用法。
    WHY: 每个测试函数独立验证一个 API 行为——
         一个失败不影响其他测试。
    """
    # WHY: TestClient(app) 创建测试客户端——不需要启动服务器
    client = TestClient(app)
    passed = 0
    failed = 0

    def test(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}  — FAILED: {detail}")

    print("\n" + "=" * 60)
    print("🧪 开始 FastAPI 测试")
    print("=" * 60)

    # ── 测试 1: 正常查询 ──
    print("\n📦 测试组1: 订单查询")

    response = client.get("/order/ORD001")
    test("GET /order/ORD001 返回 200", response.status_code == 200)
    test("响应包含 product 字段", response.json()["product"] == "蓝牙耳机")
    test("响应包含 status 字段", response.json()["status"] == "已签收")

    # ── 测试 2: 404 错误 ──
    response = client.get("/order/NOTEXIST")
    test("GET /order/NOTEXIST 返回 404", response.status_code == 404)
    test("404 响应包含 detail", "detail" in response.json())

    # ── 测试 3: POST 请求体校验 ──
    print("\n📦 测试组2: 退款申请 + Pydantic 校验")

    # 正常退款
    valid_refund = {"order_id": "ORD001", "reason": "商品有划痕需要退货", "amount": 299}
    response = client.post("/refund", json=valid_refund)
    test("POST /refund 正常返回 200", response.status_code == 200)
    test("退款响应包含 ticket_id", "ticket_id" in response.json())

    # 缺少必填字段
    invalid_refund = {"order_id": "ORD001"}
    response = client.post("/refund", json=invalid_refund)
    test("缺少必填字段返回 422", response.status_code == 422)

    # 金额为负数
    negative_amount = {"order_id": "ORD001", "reason": "质量问题要退款退货", "amount": -100}
    response = client.post("/refund", json=negative_amount)
    test("负数金额返回 422", response.status_code == 422)

    # 原因太短
    short_reason = {"order_id": "ORD001", "reason": "退", "amount": 100}
    response = client.post("/refund", json=short_reason)
    test("退款原因太短返回 422", response.status_code == 422)

    # ── 测试 4: 认证 ──
    print("\n📦 测试组3: 认证与权限")

    # 不带 token
    response = client.get("/me")
    test("无 token 时 /me 返回 401", response.status_code == 401)

    # 带有效 token
    response = client.get("/me", headers={"Authorization": "Bearer admin"})
    test("有效 token 返回 200", response.status_code == 200)
    test("响应包含用户名", response.json()["username"] == "admin")
    test("响应包含角色", response.json()["role"] == "admin")

    # ── 测试 5: 响应结构 ──
    print("\n📦 测试组4: 响应数据结构")

    response = client.get("/order/ORD001")
    data = response.json()
    test("响应是 dict", isinstance(data, dict))
    test("order_id 是字符串", isinstance(data["order_id"], str))
    test("price 是数字", isinstance(data["price"], (int, float)))

    # ── 测试 6: HTTP 方法 ──
    print("\n📦 测试组5: HTTP 方法")

    test("GET 方法正确", client.get("/order/ORD001").status_code == 200)
    test("POST 方法正确", client.post("/refund", json=valid_refund).status_code == 200)

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed + failed} 个测试, {passed} 通过, {failed} 失败")
    print("=" * 60 + "\n")
    return passed, failed


# ══════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # WHY: 直接运行时先跑测试，再启动服务器
    #      也可以 python -m pytest 25_testing.py 运行测试
    p, f = run_tests()
    if f == 0:
        print("✅ 所有测试通过！正在启动服务器...\n")
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    else:
        print(f"⚠️ 有 {f} 个测试失败，请检查后再启动服务器。")
