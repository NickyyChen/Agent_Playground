# -*- coding: utf-8 -*-
"""
23_static_files.py — FastAPI 静态文件
=======================================

【概念】静态文件服务
FastAPI 可以像传统 Web 服务器一样直接返回静态文件（HTML/CSS/JS/图片等）。
使用 StaticFiles 挂载目录，前端资源无需额外 Nginx。

挂载方式：
  app.mount("/static", StaticFiles(directory="static"), name="static")

访问：
  /static/style.css    → 返回 static/style.css
  /static/logo.png     → 返回 static/logo.png

【在智能客服中解决什么问题】
  - 客服后台的 React/Vue 打包产物直接由 FastAPI 服务
  - 商品图片、工单附件等静态资源
  - API 文档之外的简单 HTML 管理页面

  前端部署方案对比：
  ┌──────────────────┬───────────────────────────┐
  │ 方案              │ 适用场景                    │
  ├──────────────────┼───────────────────────────┤
  │ Nginx + FastAPI   │ 生产环境——Nginx 专门服务静态 │
  │ FastAPI 独立服务  │ 开发/演示——一个服务搞定一切  │
  │ CDN + FastAPI     │ 大规模——静态资源走 CDN      │
  └──────────────────┴───────────────────────────┘

【核心流程】

  浏览器
      │
      ├── GET /api/orders ──────→ FastAPI 路由处理（动态数据）
      │
      ├── GET /static/logo.png ─→ StaticFiles 中间件（静态文件）
      │
      └── GET /                → HTML 页面（客服后台）

【测试案例】
  # 启动服务器
  python fastapi-basics/23_static_files.py

  # 浏览器访问客服后台页面
  open http://localhost:8000/
  # → 展示带 CSS 样式的工单管理页面

  # 静态 CSS 文件
  curl http://localhost:8000/static/css/style.css
  # → 返回 CSS 内容

  # 静态 JS 文件
  curl http://localhost:8000/static/js/app.js
  # → 返回 JS 内容（console.log 在浏览器控制台可见）

  # 工单 API（供前端 JS fetch 调用）
  curl http://localhost:8000/tickets/api
  # → {"total":3,"items":[{...},{...},{...}]}

  # 服务器状态（检查静态文件是否存在）
  curl http://localhost:8000/api/status
  # → {"status":"running","static_dir":"...","css_exists":true,"js_exists":true}

  # ★ API 路由和静态文件路由共存：
  #   /static/xxx → 静态文件（StaticFiles 中间件）
  #   /tickets/api → 动态 API（FastAPI 路由）

【pip install】
pip install fastapi uvicorn aiofiles
"""

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="好买电商客服 API - 静态文件")


# ══════════════════════════════════════════════════════════════
# 1. 创建静态文件目录
# ══════════════════════════════════════════════════════════════

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
CSS_DIR = os.path.join(STATIC_DIR, "css")
JS_DIR = os.path.join(STATIC_DIR, "js")
IMG_DIR = os.path.join(STATIC_DIR, "img")

# WHY: 创建目录结构——确保挂载前目录存在
for d in [STATIC_DIR, CSS_DIR, JS_DIR, IMG_DIR]:
    os.makedirs(d, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# 2. 生成示例静态文件
# ══════════════════════════════════════════════════════════════

# WHY: 创建演示用的 CSS 和 JS 文件——让示例可以直接跑
with open(os.path.join(CSS_DIR, "style.css"), "w", encoding="utf-8") as f:
    f.write("""
body { font-family: 'Microsoft YaHei', sans-serif; margin: 40px; background: #f5f5f5; }
h1 { color: #1a73e8; }
.ticket { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.status { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 12px; }
.status.processing { background: #fff3cd; color: #856404; }
.status.done { background: #d4edda; color: #155724; }
""")

with open(os.path.join(JS_DIR, "app.js"), "w", encoding="utf-8") as f:
    f.write("""
console.log('好买电商客服系统 - 静态资源加载成功');
document.addEventListener('DOMContentLoaded', function() {
    fetch('/tickets/api')
        .then(r => r.json())
        .then(data => {
            console.log('工单数据:', data);
        });
});
""")


# ══════════════════════════════════════════════════════════════
# 3. 挂载静态文件目录
# ══════════════════════════════════════════════════════════════

# WHY: app.mount() 将整个目录映射到 URL 路径
#      所有 /static/xxx 请求都会从 static/ 目录查找文件
#      StaticFiles 自动处理 Content-Type、缓存头、404 等
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")


# ══════════════════════════════════════════════════════════════
# 4. 客服后台 HTML 页面（引用静态资源）
# ══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def admin_dashboard():
    """
    客服管理后台首页。
    引用了 /static/css/style.css 和 /static/js/app.js。
    """
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>好买电商 - 客服管理后台</title>
        <!-- WHY: 引用挂载的静态 CSS 文件 -->
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <h1>📋 客服工单管理后台</h1>

        <div class="ticket">
            <strong>TKT-001</strong>: 蓝牙耳机杂音问题
            <span class="status processing">处理中</span>
        </div>
        <div class="ticket">
            <strong>TKT-002</strong>: 订单未收到货
            <span class="status processing">待分配</span>
        </div>
        <div class="ticket">
            <strong>TKT-003</strong>: 退款咨询
            <span class="status done">已完成</span>
        </div>

        <p style="margin-top: 20px; color: #666;">
            ✅ 静态资源加载测试:
            <a href="/static/css/style.css">CSS</a> |
            <a href="/static/js/app.js">JavaScript</a>
        </p>

        <!-- WHY: 引用挂载的静态 JS 文件 -->
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    """


# ══════════════════════════════════════════════════════════════
# 5. API 路由（与静态文件共存）
# ══════════════════════════════════════════════════════════════

@app.get("/tickets/api")
def tickets_api():
    """
    工单 API——供 JS fetch() 调用。
    WHY: API 路由和静态文件路由可以共存——
         /static/xxx → 静态文件
         /tickets/api → API
    """
    return {
        "total": 3,
        "items": [
            {"id": "TKT-001", "title": "蓝牙耳机杂音问题", "status": "处理中"},
            {"id": "TKT-002", "title": "订单未收到货", "status": "待分配"},
            {"id": "TKT-003", "title": "退款咨询", "status": "已完成"},
        ],
    }


@app.get("/api/status")
def api_status():
    """
    服务器状态。
    WHY: 展示静态文件和动态 API 可以部署在同一服务中。
    """
    return {
        "status": "running",
        "static_dir": STATIC_DIR,
        "static_url": "/static",
        "css_exists": os.path.exists(os.path.join(CSS_DIR, "style.css")),
        "js_exists": os.path.exists(os.path.join(JS_DIR, "app.js")),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
