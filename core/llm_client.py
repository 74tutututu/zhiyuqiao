import os

from dotenv import load_dotenv
from openai import OpenAI

# 允许从项目根目录的 .env 加载配置
load_dotenv()

# DeepSeek OpenAI-compatible 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# 模型名可通过环境变量覆盖。
# 为了保持向后兼容，默认沿用本项目此前使用的 `deepseek-chat`。
# 如果你的账号/地区不支持该别名，可在 `.env` 中设置 `DEEPSEEK_MODEL` 为你可用的模型名。
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
