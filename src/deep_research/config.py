"""
finagent-research 配置中心。

从 .env 读取配置，集中暴露。模型对象用工厂函数延迟创建。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# ===== 大模型 =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 主模型（规划/撰写/审核用，温度适中）
MAIN_MODEL_CONFIG = {
    "model": "deepseek-chat",
    "openai_api_key": DEEPSEEK_API_KEY,
    "openai_api_base": DEEPSEEK_BASE_URL,
    "temperature": 0.5,
}


def get_model():
    """延迟创建 LLM（需要 langchain-openai）。"""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(**MAIN_MODEL_CONFIG)


# ===== 搜索 =====
BOCHAAI_API_KEY = os.getenv("BOCHAAI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "bochaai")

# ===== Redis =====
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1")

# ===== MongoDB（可观测性追踪，与 finagent-core 共用，便于统一监控）=====
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "finagent")

# ===== 服务 =====
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8001"))

# ===== 研究流程参数 =====
DEFAULT_MAX_ITERATIONS = 2          # 审核-修订循环上限（4G 上控制成本/时间）
MAX_SEARCH_QUERIES = 3              # 单轮并发搜索数上限
