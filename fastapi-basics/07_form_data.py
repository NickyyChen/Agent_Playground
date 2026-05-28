# -*- coding: utf-8 -*-
"""
07_form_data.py — FastAPI 表单数据
======================================

【概念】表单数据 vs JSON 请求体
JSON 请求体：Content-Type: application/json → 用于前后端分离的 API
表单数据：   Content-Type: application/x-www-form-urlencoded → 用于传统 HTML 表单

FastAPI 用 Form() 声明表单字段，需要 pip install python-multipart。

【在智能客服中解决什么问题】
客服管理后台是传统 HTML 页面，登录、提交工单都用 <form> 表单提交。
FastAPI 同时支持 JSON API（给 App 调用）和表单提交（给后台页面）。

【核心流程】

  HTML <form>                                      FastAPI
  ──────────────────────────────────────────────────────

  <form action="/login" method="POST">
    用户名: <input name="username" />
    密码:   <input name="password" type="password" />
    <button>登录</button>
  </form>
      │
      │ POST /login
      │ Content-Type: application/x-www-form-urlencoded
      │ username=admin&password=123456
      ▼
  ┌───────────────────────────────────┐
  │ @app.post("/login")               │
  │ def login(                        │
  │   username: str = Form(...),      │  ← Form() 从表单数据提取
  │   password: str = Form(...)       │
  │ )                                 │
  └───────────────────────────────────┘

  ★ JSON 和表单可以混用！同一个接口可以同时有 Form 字段和 File 字段。

【测试案例】
  # 启动服务器
  python fastapi-basics/07_form_data.py

  # 表单登录（--data-urlencode 模拟 HTML form 提交）
  curl -X POST http://localhost:8000/login \
    -d "username=admin&password=admin123"
  # → {"message":"欢迎回来，admin","token":"session-admin-001"}

  # 错误密码 → 401
  curl -X POST http://localhost:8000/login \
    -d "username=admin&password=wrong"
  # → 401 密码错误

  # 创建工单——表单+文件上传（用 -F 模拟 multipart/form-data）
  curl -X POST http://localhost:8000/ticket/create \
    -F "customer_name=张伟" \
    -F "order_id=ORD001" \
    -F "complaint=蓝牙耳机有杂音" \
    -F "screenshot=@/path/to/screenshot.png"
  # → {"message":"工单创建成功","ticket_id":"TKT-20240120-001",...}

  # 提交评分反馈（可选字段 comment 不传）
  curl -X POST http://localhost:8000/feedback \
    -d "score=5&anonymous=false"
  # → {"message":"感谢您的评价！","feedback":{"score":5,"anonymous":false}}

【pip install】
pip install fastapi uvicorn python-multipart
"""

import uvicorn
from typing import Optional, List

from fastapi import FastAPI, Form, File, UploadFile, HTTPException

app = FastAPI(title="好买电商客服管理后台 - 表单处理")

# WHY: 模拟用户数据库——实际存数据库中并加密密码
fake_admin_users = {
    "admin": "admin123",
    "zhang": "password",
}


# ══════════════════════════════════════════════════════════════
# 1. 基础表单提交（登录）
# ══════════════════════════════════════════════════════════════

@app.post("/login")
def login(
    username: str = Form(..., description="用户名"),
    password: str = Form(..., description="密码"),
):
    """
    客服管理后台登录。
    Form(...) 中 ... 表示必填——FastAPI 从 form-data 中提取对应字段。
    WHY: 管理后台用 session/cookie 认证，表单提交是最自然的方式。
    """
    if username not in fake_admin_users:
        raise HTTPException(status_code=401, detail="用户名不存在")
    if fake_admin_users[username] != password:
        raise HTTPException(status_code=401, detail="密码错误")
    return {"message": f"欢迎回来，{username}", "token": f"session-{username}-001"}


# ══════════════════════════════════════════════════════════════
# 2. 表单 + 文件上传（客服工单带截图）
# ══════════════════════════════════════════════════════════════

@app.post("/ticket/create")
async def create_ticket(
    customer_name: str = Form(..., description="顾客姓名"),
    order_id: str = Form(..., description="关联订单号"),
    complaint: str = Form(..., description="投诉内容"),
    # WHY: UploadFile 用于上传文件——比 bytes 更好，支持大文件流式传输
    screenshot: Optional[UploadFile] = File(None, description="问题截图"),
    # WHY: List[UploadFile] 支持一次上传多个文件
    attachments: List[UploadFile] = File(default_factory=list, description="附件"),
):
    """
    创建售后工单——表单 + 文件混合提交。
    WHY: 客服处理投诉时，顾客会传截图证明商品问题，
         Form 和 File 可以同在一个请求中。
    """
    info = {
        "customer": customer_name,
        "order_id": order_id,
        "complaint": complaint,
    }

    if screenshot and screenshot.filename:
        # WHY: await read() 读取文件内容，filename 是原始文件名
        content = await screenshot.read()
        info["screenshot"] = {
            "filename": screenshot.filename,
            "size": len(content),
            "content_type": screenshot.content_type,
        }

    if attachments:
        info["attachments"] = [
            {
                "filename": f.filename,
                "content_type": f.content_type,
            }
            for f in attachments
        ]

    return {
        "message": "工单创建成功",
        "ticket_id": "TKT-20240120-001",
        "detail": info,
    }


# ══════════════════════════════════════════════════════════════
# 3. 可选表单字段
# ══════════════════════════════════════════════════════════════

@app.post("/feedback")
def submit_feedback(
    score: int = Form(..., ge=1, le=5, description="评分 1-5"),
    comment: Optional[str] = Form(None, description="评价文字（可选）"),
    anonymous: bool = Form(False, description="是否匿名"),
):
    """
    顾客评价。
    score 带校验：ge=1（>=1），le=5（<=5）
    comment 可选：Form(None) 表示可以不传
    anonymous 有默认值：Form(False) 表示默认不匿名
    """
    result = {"score": score, "anonymous": anonymous}
    if comment:
        result["comment"] = comment
    return {"message": "感谢您的评价！", "feedback": result}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
