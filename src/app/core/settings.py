"""
统一配置管理系统
解决当前项目中硬编码严重的问题
"""

import os
from typing import List, Dict, Any
from pathlib import Path
from pydantic_settings import BaseSettings
from loguru import logger


class Settings(BaseSettings):
    """统一配置管理类"""
    
    # 项目基本信息
    PROJECT_NAME: str = "JD Agent"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # OpenAI配置（可选，支持多种LLM提供商）
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    MODEL_NAME: str = "gpt-3.5-turbo"
    MODEL_MAX_TOKENS: int = 1000
    MODEL_TEMPERATURE: float = 0.1
    
    # 向量数据库配置
    VECTOR_DB_PATH: str = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/data/vector_db"
    VECTOR_DB_COLLECTION: str = "jd_agent_knowledge"
    
    # 模型配置
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"
    EMBEDDING_MODEL_NAME: str = "shibing624/text2vec-base-chinese"
    
    # 爬虫配置
    CRAWLER_DELAY_MIN: float = 2.0
    CRAWLER_DELAY_MAX: float = 5.0
    CRAWLER_MAX_RETRIES: int = 3
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 1000
    CACHE_EXPIRATION_LLM: int = 259200  # LLM结果缓存（3天）
    
    # HuggingFace镜像配置
    HF_ENDPOINT: str = "https://hf-mirror.com"
    
    # 其他项目配置（兼容性）
    model_name: str = ""
    tavily_api_key: str = ""
    audio_api_key: str = ""
    audio_api_base: str = ""
    asr_model: str = ""
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    confluence_url: str = ""
    confluence_username: str = ""
    confluence_password: str = ""
    confluence_api_token: str = ""
    secret_key: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略.env中未定义的字段


# 全局配置实例
settings = Settings()

# 设置环境变量
os.environ["HF_ENDPOINT"] = settings.HF_ENDPOINT

# 创建必要的目录
Path(settings.VECTOR_DB_PATH).mkdir(parents=True, exist_ok=True)

# 验证配置
def validate_settings():
    """验证配置的有效性"""
    issues = []
    
    # 检查必要目录
    required_paths = [
        settings.VECTOR_DB_PATH,
    ]
    
    for path in required_paths:
        if not Path(path).exists():
            issues.append(f"目录不存在: {path}")
    
    # 检查API密钥（可选，根据实际需求配置）
    # OPENAI_API_KEY现在为可选，因为用户可能使用其他LLM提供商
    
    # 检查模型配置
    if not settings.EMBEDDING_MODEL_NAME:
        issues.append("未设置嵌入模型名称")
    
    if issues:
        logger.warning("配置验证发现问题:")
        for issue in issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("✅ 配置验证通过")
    
    return len(issues) == 0

# 初始化配置
if __name__ == "__main__":
    validate_settings()
    print("配置信息:")
    print(f"向量数据库路径: {settings.VECTOR_DB_PATH}")
    print(f"嵌入模型: {settings.EMBEDDING_MODEL_NAME}")
    print(f"日志级别: {settings.LOG_LEVEL}")