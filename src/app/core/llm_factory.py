from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm(temperature=0.7):
    # 这里可以配置 DeepSeek 的 Base URL
    return ChatOpenAI(
        model_name=settings.MODEL_NAME, # e.g., "gpt-4" or "deepseek-chat"
        openai_api_key=settings.OPENAI_API_KEY,
        openai_api_base=settings.OPENAI_API_BASE,
        temperature=temperature
    )