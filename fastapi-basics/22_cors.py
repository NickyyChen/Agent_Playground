# -*- coding: utf-8 -*-
"""
22_cors.py — FastAPI CORS 跨域
=================================

【概念】什么是 CORS（跨域资源共享）？
浏览器的同源策略（Same-Origin Policy）禁止网页从不同域名/端口请求数据。
CORS 是服务器告诉浏览器"允许跨域请求"的机制。

同源定义（协议 + 域名 + 端口都相同）：
  https://www.haomai.com:443/api   ← 同源
  http://www.haomai.com:80/api     ← 不同源（协议不同）
  https://api.haomai.com/api       ← 不同源（子域名不同）
  https://www.haomai.com:8080/api  ← 不同源（端口不同）

CORS 工作原理：
  浏览器先发 OPTIONS 预检请求 → 服务器返回允许的规则 → 浏览器决定是否发正式请求

【在智能客服中解决什么问题】
智能客服前端（React/Vue）部署在 crm.haomai.com，
API 部署在 api.haomai.com——不同子域名就是跨域。
没有 CORS，客服后台页面无法调用 API。

【核心流程】

  前端 (crm.haomai.com)                    API 服务器 (api.haomai.com)
  ────────────────────────────────────────────────────────────────
      │                                          │
      │  OPTIONS /order/ORD001                   │
      │  Origin: https://crm.haomai.com          │
      │  Access-Control-Request-Method: GET      │  ← 预检请求
      ├─────────────────────────────────────────►│
      │                                          │  检查 Origin 是否在允许列表中
      │  200 OK                                  │
      │  Access-Control-Allow-Origin:            │
      │    https://crm.haomai.com                │
      │  Access-Control-Allow-Methods: GET,POST  │  ← 预检响应
      │◄─────────────────────────────────────────┤
      │                                          │
      │  GET /order/ORD001                       │  ← 正式请求
      ├─────────────────────────────────────────►│
      │  200 OK {order...}                       │  ← 正式响应
      │◄─────────────────────────────────────────┤

CORSMiddleware 参数说明：
  allow_origins      → 允许的域名列表，["*"] 表示全部
  allow_methods       → 允许的 HTTP 方法
  allow_headers       → 允许的请求头
  allow_credentials   → 是否允许携带 Cookie/认证信息
  expose_headers      → 允许 JS 读取的响应头
  max_age             → 预检请求缓存时间（秒）

【测试案例】
  # 启动服务器
  python fastapi-basics/22_cors.py

  # 跨域测试——模拟浏览器发 OPTIONS 预检请求
  curl -X OPTIONS http://localhost:8000/order/ORD001 \
    -H "Origin: https://crm.haomai.com" \
    -H "Access-Control-Request-Method: GET" \
    -i
  # → 200 OK，响应头含 Access-Control-Allow-Origin: *

  # 正常跨域 GET 请求
  curl http://localhost:8000/order/ORD001 \
    -H "Origin: https://crm.haomai.com"
  # → 200 OK（响应头含 Access-Control-Allow-Origin: *）

  # 跨域 POST 请求
  curl -X POST "http://localhost:8000/refund?order_id=ORD001&reason=质量问题" \
    -H "Origin: https://crm.haomai.com"
  # → 200 OK

  # CORS 浏览器测试——打开 http://localhost:8000/cors-test 在控制台执行：
  # fetch('http://localhost:8000/cors-test').then(r=>r.json()).then(console.log)
  # → 跨域请求成功！

  # ★ 生产环境安全配置示例（注释掉的代码）：
  #   allow_origins=["https://crm.haomai.com", "https://www.haomai.com"]
  #   allow_credentials=True
  #   allow_methods=["GET", "POST", "PUT", "DELETE"]
  #   max_age=3600

【pip install】
pip install fastapi uvicorn
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="好买电商客服 API - CORS 跨域")


# ══════════════════════════════════════════════════════════════
# 1. 基础 CORS 配置——允许所有来源（开发环境）
# ══════════════════════════════════════════════════════════════

# WHY: CORS 中间件要放在最外层——最先处理 OPTIONS 预检请求
#      allow_origins=["*"] 允许所有域名（仅开发环境！）
#      生产环境必须指定具体域名，不能用 *
app.add_middleware(
    CORSMiddleware,
    # WHY: ["*"] 表示允许任何域名访问——开发方便，但生产环境有安全风险
    allow_origins=["*"],
    # WHY: allow_credentials=True 时，allow_origins 不能是 ["*"]
    #      因为带 credentials 时浏览器不允许通配符来源
    allow_credentials=False,
    # WHY: ["*"] 允许所有 HTTP 方法
    allow_methods=["*"],
    # WHY: ["*"] 允许所有请求头
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════
# 2. 生产环境 CORS 配置（更安全）
# ══════════════════════════════════════════════════════════════

# 注释掉上面的配置，改用下面这个用于生产环境：

# app.add_middleware(
#     CORSMiddleware,
#     # WHY: 明确列出允许的域名——防止其他网站滥用 API
#     allow_origins=[
#         "https://crm.haomai.com",          # 客服管理后台
#         "https://www.haomai.com",           # 官网
#         "https://m.haomai.com",             # 移动端
#     ],
#     # WHY: allow_credentials=True 允许跨域请求携带 Cookie
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE"],
#     allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
#     # WHY: expose_headers 让前端 JS 能读取这些响应头
#     expose_headers=["X-Request-ID", "X-Process-Time-ms"],
#     # WHY: max_age=3600 预检结果缓存 1 小时——减少 OPTIONS 请求次数
#     max_age=3600,
# )


# ══════════════════════════════════════════════════════════════
# 3. CORS 场景模拟路由
# ══════════════════════════════════════════════════════════════

@app.get("/order/{order_id}")
def get_order(order_id: str):
    """查询订单——允许跨域访问。"""
    return {"order_id": order_id, "product": "蓝牙耳机", "price": 299}


@app.post("/refund")
def create_refund(order_id: str, reason: str):
    """提交退款——允许跨域 POST。"""
    return {"ticket_id": f"TKT-{order_id}", "status": "已受理"}


@app.options("/order/{order_id}")
def options_order(order_id: str):
    """
    手动处理 OPTIONS 预检。
    WHY: CORSMiddleware 会自动处理 OPTIONS，这里只是展示
         如果你需要自定义预检逻辑可以怎么做。
    """
    return {"message": f"预检通过: /order/{order_id}"}


# ══════════════════════════════════════════════════════════════
# 4. CORS 调试端点
# ══════════════════════════════════════════════════════════════

@app.get("/cors-test")
def cors_test():
    """
    CORS 测试端点——在浏览器控制台中用 fetch() 测试：
      fetch('http://localhost:8000/cors-test')
        .then(r => r.json())
        .then(console.log)
    """
    return {
        "message": "CORS 配置成功！如果你在浏览器看到这条消息，说明跨域请求正常工作。",
        "tip": "打开浏览器控制台(F12)并执行 fetch() 验证",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
