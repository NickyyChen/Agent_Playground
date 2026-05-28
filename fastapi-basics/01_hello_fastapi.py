# -*- coding: utf-8 -*-
"""
01_hello_fastapi.py — 第一个 FastAPI 应用
==========================================

【概念】什么是 FastAPI？
FastAPI 是一个现代、高性能的 Python Web 框架，用于构建 RESTful API。
核心优势：
  - 自动生成交互式 API 文档（Swagger UI / ReDoc）
  - 基于 Python 类型注解的数据校验
  - 异步支持，性能媲美 Node.js
  - 符合 OpenAPI 规范

【在智能客服中解决什么问题】
智能客服系统需要对外暴露 HTTP API——用户查询订单、提交退款、查询物流。
FastAPI 用最少的代码，构建出带自动校验、自动文档的生产级 API。

【核心流程】
  1. 创建 FastAPI() 实例 → app
  2. 用 @app.get("/path") 装饰器定义端点
  3. 用 uvicorn 启动 ASGI 服务器
  4. 访问 http://localhost:8000 调用接口

【pip install】
pip install fastapi uvicorn

【ASCII 架构图】

  浏览器 / 客户端
      │  HTTP GET /
      ▼
  ┌──────────────────────┐
  │  uvicorn (ASGI服务器) │  ← 接收 HTTP 请求，转发给 FastAPI
  └──────┬───────────────┘
         │
         ▼
  ┌──────────────────────┐
  │  FastAPI() 实例      │  ← 路由匹配 → 调用对应的函数
  │  @app.get("/")       │
  │  def root()          │
  └──────┬───────────────┘
         │
         ▼
  {"message": "欢迎来到好买电商客服 API"}  ← JSON 响应，自动序列化

  FastAPI 三要素：
  app = FastAPI()  ← 应用实例，注册路由/中间件
  @app.get(...)    ← 路径操作装饰器，声明 HTTP 方法和 URL
  def handler()    ← 路径操作函数，处理请求并返回响应

【测试案例】
  # 启动服务器
  python fastapi-basics/01_hello_fastapi.py

  # 终端用 curl 测试
  curl http://localhost:8000/
  # → {"message":"欢迎来到好买电商客服 API"}

  curl http://localhost:8000/health
  # → {"status":"ok"}

  # 也可浏览器直接访问: http://localhost:8000/docs 进入 Swagger UI 交互式测试
"""

import uvicorn
from fastapi import FastAPI

# WHY: FastAPI() 是整个应用的入口，所有路由和中间件都注册在它上面
# 参数 title/description/version 会出现在自动生成的 Swagger 文档中
app = FastAPI(
    title="好买电商客服 API",
    description="Agent-Playground FastAPI 入门教程 - 01 第一个应用",
    version="1.0.0",
)


# ══════════════════════════════════════════════════════════════
# 路由：@app.get("/") 表示当客户端 GET 请求根路径时，调用这个函数
# WHY: @ 装饰器是 FastAPI 声明路由的方式——告诉框架"这个函数处理这个 URL"
# ══════════════════════════════════════════════════════════════
@app.get("/")
def root():
    """
    根路径——最简单的 API 端点。
    返回一个字典，FastAPI 自动转为 JSON 响应。
    """
    return {"message": "欢迎来到好买电商客服 API"}


# WHY: 另一个端点展示如何组织多个 API
@app.get("/health")
def health_check():
    """健康检查——供监控系统使用"""
    return {"status": "ok"}


# WHY: __name__ == "__main__" 保证只在直接运行此文件时才启动服务器
#      被 import 时不会误启动
if __name__ == "__main__":
    # WHY: uvicorn.run() 启动 ASGI 服务器
    # host="127.0.0.1" 只监听本地，避免对外暴露
    # port=8000 默认端口
    # log_level="info" 控制日志详细程度
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
