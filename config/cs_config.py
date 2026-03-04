import os
import httpx
from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel, set_tracing_disabled

set_tracing_disabled(disabled=True)

PROXY = os.getenv("HTTP_PROXY", "http://127.0.0.1:7890")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-94c7b08efae54206904c861468206305")

openai_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    http_client=httpx.AsyncClient(proxy=PROXY, timeout=60),
)

model = OpenAIChatCompletionsModel(
    model="deepseek-chat",
    openai_client=openai_client
)
