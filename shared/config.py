"""
集中管理 DeepSeek LLM 的连接配置。
为什么不直接写在 demo 里：避免每个 demo 重复 API Key/Base URL 的读取逻辑，
后续只需改这一个文件就能切换模型或密钥。
"""
import os
from dotenv import load_dotenv

# 自动加载项目根目录的 .env 文件
_ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_ENV_FILE):
    load_dotenv(_ENV_FILE)

# DeepSeek-v4-pro 配置（兼容 OpenAI SDK）
# API Key 通过环境变量 DEEPSEEK_API_KEY 设置，不硬编码
LLM_CONFIG = {
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
}
