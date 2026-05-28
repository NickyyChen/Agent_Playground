# -*- coding: utf-8 -*-
"""
17_custom_response.py — FastAPI 自定义响应
============================================

【概念】自定义响应
除了返回 dict（自动转 JSON），FastAPI 提供了多种响应类型来满足不同场景：

  响应类型              用途
  ─────────────────────────────────────────────
  JSONResponse         自定义 JSON（设置 headers/cookies）
  HTMLResponse         返回 HTML 页面
  PlainTextResponse    返回纯文本
  RedirectResponse     重定向到另一个 URL
  StreamingResponse    流式响应（SSE、大文件）
  FileResponse         返回文件下载
  Response             最原始的响应——完全手动控制

【在智能客服中解决什么问题】
  - 客服后台返回 HTML 页面
  - 导出工单为 CSV 文件下载
  - 流式输出 AI 回复（ChatGPT 式逐字输出）
  - 重定向旧接口到新地址

【测试案例】
  # 启动服务器
  python fastapi-basics/17_custom_response.py

  # 自定义 JSON 响应头
  curl -i http://localhost:8000/api/data
  # → 200 OK，响应头含 X-API-Version: 2.0, X-Response-Time: 12ms

  # HTML 页面（客服后台）
  curl http://localhost:8000/admin
  # → 返回 HTML 页面（浏览器打开 http://localhost:8000/admin 查看渲染效果）

  # API 版本迁移重定向
  curl -L http://localhost:8000/v1/order/ORD001
  # → 自动重定向到 /v2/order/ORD001

  # AI 流式回复（逐字输出效果在终端可见）
  curl -N "http://localhost:8000/ai/chat?message=耳机有杂音"
  # → 逐字流式输出回复内容

  # 导出工单为 CSV 文件下载
  curl http://localhost:8000/export/tickets
  # → 下载 工单导出.csv 文件

  # 纯文本健康检查（监控系统专用）
  curl http://localhost:8000/health/plain
  # → OK\nuptime: 72h\nrequests: 152340

  # 原始 XML 响应（对接老旧系统）
  curl http://localhost:8000/custom
  # → XML 格式响应

【pip install】
pip install fastapi uvicorn aiofiles
"""

import uvicorn
import asyncio
import time
from fastapi import FastAPI
from fastapi.responses import (
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
    FileResponse,
    Response,
)

app = FastAPI(title="好买电商客服 API - 自定义响应")


# ══════════════════════════════════════════════════════════════
# 1. JSONResponse——自定义 JSON 响应
# ══════════════════════════════════════════════════════════════

@app.get("/api/data")
def get_data_via_json_response():
    """
    自定义 JSON 响应——设置特定的状态码和响应头。
    WHY: JSONResponse 比直接 return dict 多了手动控制 Headers 的能力。
    """
    content = {"order_id": "ORD001", "status": "已签收"}
    return JSONResponse(
        content=content,
        status_code=200,
        # WHY: 自定义 Header 用于调试、版本标记、缓存控制等
        headers={
            "X-API-Version": "2.0",
            "X-Response-Time": "12ms",
            "Cache-Control": "no-cache",
        },
    )


# ══════════════════════════════════════════════════════════════
# 2. HTMLResponse——返回客服后台页面
# ══════════════════════════════════════════════════════════════

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    """
    客服管理后台 HTML 页面。
    WHY: response_class=HTMLResponse 告诉 FastAPI 返回的是 HTML 而非 JSON。
         浏览器会自动渲染 HTML。
    """
    return """
    <!DOCTYPE html>
    <html>
    <head><title>好买电商 - 客服管理后台</title></head>
    <body>
        <h1>📋 客服工单管理</h1>
        <p>待处理工单: 5 | 今日已处理: 23</p>
        <ul>
            <li>TKT-001: 蓝牙耳机杂音问题 - <b>处理中</b></li>
            <li>TKT-002: 物流信息未更新 - <b>待分配</b></li>
        </ul>
    </body>
    </html>
    """


# ══════════════════════════════════════════════════════════════
# 3. RedirectResponse——旧接口重定向
# ══════════════════════════════════════════════════════════════

@app.get("/v1/order/{order_id}")
def old_api(order_id: str):
    """
    旧版 API 重定向到新版。
    WHY: RedirectResponse 用于 API 版本迁移——客户端可能还请求旧 URL。
    """
    return RedirectResponse(url=f"/v2/order/{order_id}")


@app.get("/v2/order/{order_id}")
def new_api(order_id: str):
    """新版 API。"""
    return {"version": "v2", "order_id": order_id, "status": "已签收"}


# ══════════════════════════════════════════════════════════════
# 4. StreamingResponse——模拟 AI 流式回复
# ══════════════════════════════════════════════════════════════

async def ai_reply_generator(message: str):
    """
    模拟 AI 逐字生成回复。
    WHY: async generator 逐个 yield 数据块——
         客户端可以实时看到 AI 回复"打字"效果，不用等全部生成完。
    """
    reply = f"您好，关于「{message}」的问题，我们已记录并安排专员处理。"
    for char in reply:
        yield char  # 每次返回一个字符
        await asyncio.sleep(0.05)  # 模拟 AI 生成延迟


@app.get("/ai/chat")
async def ai_chat(message: str):
    """
    模拟 AI 流式对话。
    WHY: StreamingResponse 适合 ChatGPT 式逐字输出、大文件下载等场景。
    media_type="text/event-stream" 是 SSE（Server-Sent Events）格式。
    """
    return StreamingResponse(
        ai_reply_generator(message),
        media_type="text/plain; charset=utf-8",
        headers={"X-AI-Model": "gpt-4-simulated"},
    )


# ══════════════════════════════════════════════════════════════
# 5. FileResponse——文件下载
# ══════════════════════════════════════════════════════════════

@app.get("/export/tickets")
def export_tickets():
    """
    导出工单为 CSV 文件下载。
    WHY: FileResponse 直接返回文件——浏览器自动触发下载。
         实际项目中先生成 CSV 文件，再用 FileResponse 返回。
    """
    import tempfile, os

    # 创建临时 CSV 文件
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write("工单号,标题,状态,创建时间\n")
    tmp.write("TKT-001,耳机杂音,处理中,2024-01-15\n")
    tmp.write("TKT-002,未收到货,待分配,2024-01-16\n")
    tmp.write("TKT-003,退款咨询,已完成,2024-01-17\n")
    tmp.close()

    return FileResponse(
        path=tmp.name,
        filename="工单导出.csv",
        # WHY: media_type 告诉浏览器这是 CSV 文件，触发下载而非预览
        media_type="text/csv; charset=utf-8-sig",
    )


# ══════════════════════════════════════════════════════════════
# 6. PlainTextResponse 和 Response
# ══════════════════════════════════════════════════════════════

@app.get("/health/plain", response_class=PlainTextResponse)
def health_plain():
    """
    返回纯文本健康检查。
    WHY: 监控系统（如 Prometheus）常需要纯文本格式而非 JSON。
    """
    return "OK\nuptime: 72h\nrequests: 152340"


@app.get("/custom")
def custom_raw_response():
    """
    完全手动的 Response。
    WHY: 当你需要完全控制响应体、编码、MIME 类型时使用。
    """
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<response>
    <status>success</status>
    <message>XML 格式响应（用于对接老旧系统）</message>
</response>"""
    return Response(
        content=xml_content,
        media_type="application/xml; charset=utf-8",
        status_code=200,
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
