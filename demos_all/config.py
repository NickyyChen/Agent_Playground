# -*- coding: utf-8 -*-
"""
统一配置中心。
WHY: 集中管理所有模块的配置参数——LLM密钥、模型画像、窗口限制、重试策略等。
"""

import os
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ─── LLM 连接 (从环境变量读取，不硬编码) ──────────
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
}

# ─── 模型路由画像 (Demo 19) ───────────────────────
MODEL_PROFILES = {
    "fast":    {"temperature": 0.0, "max_tokens": 150, "cost": 0.005},
    "standard":{"temperature": 0.3, "max_tokens": 400, "cost": 0.03},
    "premium": {"temperature": 0.5, "max_tokens": 800, "cost": 0.10},
}

# ─── Context Window (Demo 17) ────────────────────
CONTEXT_WINDOW = {
    "max_tokens": 4000,
    "warning_ratio": 0.7,  # 70% 时预警
    "keep_recent": 6,       # 滑动窗口保留条数
}

# ─── 重试策略 (Demo 18) ──────────────────────────
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,      # 指数退避基础延迟(秒)
    "circuit_threshold": 5, # 熔断器阈值
}

# ─── 安全护栏 (Demo 13) ──────────────────────────
SAFETY_CONFIG = {
    "enable_topic_guard": True,
    "enable_input_guard": True,
    "enable_output_guard": True,
}

# ─── 记忆系统 (Demo 04) ──────────────────────────
MEMORY_CONFIG = {
    "chroma_path": ".chroma_memory",
}

# ─── RAG 知识库 (Demo 05) ────────────────────────
RAG_CONFIG = {
    "chroma_path": ".chroma_rag",
    "chunk_size": 300,
    "chunk_overlap": 50,
    "top_k": 3,
}

# ─── 客服人设 System Prompt ──────────────────────
SYSTEM_PROMPT = """你是"小选"，好买电商平台的智能客服助手。

职责：商品咨询、订单查询、物流追踪、退换货处理
政策速查：
- 退货：签收7天内，商品完好配件齐全，运费平台承担
- 换货：签收15天内，质量问题免费换新，人为损坏不换
- 退款：退货签收后3个工作日内原路退回
- 特殊商品：耳机/内衣/食品拆封后不支持无理由退货

原则：简洁专业、引用政策、不编造数据、不承诺具体赔偿金额"""

# ─── LangSmith 可观测性 (Demo 14 扩展) ──────────
# 设置环境变量 LANGCHAIN_API_KEY 和 LANGCHAIN_PROJECT 后自动启用
# 不设置则使用本地追踪 (默认)
LANGSMITH_CONFIG = {
    "enabled": os.getenv("LANGCHAIN_API_KEY") is not None,
    "project": os.getenv("LANGCHAIN_PROJECT", "agent-playground"),
    "api_key": os.getenv("LANGCHAIN_API_KEY", ""),
    "endpoint": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
}
