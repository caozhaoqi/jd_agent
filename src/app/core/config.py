from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

import os

current_file_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))

# 拼接 .env 路径
ENV_PATH = os.path.join(project_root, ".env")

print(f"🔧 [Config] Loading .env from: {ENV_PATH}")

class Settings(BaseSettings):
    """
    系统配置类
    自动读取 .env 文件中的变量，如果 .env 中没有，则使用代码中的默认值
    """

    # --- 基础配置 ---
    PROJECT_NAME: str = "AI Interview Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # --- CORS 设置 (跨域) ---
    # 允许跨域请求的域名列表，生产环境建议设置为具体的域名
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # --- LLM 模型配置 (核心) ---
    # 必填项：如果没有在 .env 中设置，程序启动会报错
    OPENAI_API_KEY: str

    # 选填项：默认连接 OpenAI 官方
    # 如果使用 DeepSeek，这里需要改为: https://api.deepseek.com
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # 模型名称: gpt-3.5-turbo, gpt-4, deepseek-chat 等
    MODEL_NAME: str = "gpt-3.5-turbo"

    # 温度系数: 0-1，越低越严谨，越高越发散
    TEMPERATURE: float = 0.7

    # --- LangChain Tracing (可选 - 用于调试) ---
    # 如果你想在 LangSmith 后台看到链的执行过程，开启这些配置
    LANGCHAIN_TRACING_V2: str = "false"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "interview-agent-dev"

    AUDIO_API_KEY: Optional[str] = None
    AUDIO_API_BASE: Optional[str] = None
    ASR_MODEL: str = "whisper-1"
    TTS_MODEL: str = "tts-1"

    @property
    def effective_audio_key(self):
        return self.AUDIO_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_audio_base(self):
        return self.AUDIO_API_BASE or self.OPENAI_API_BASE

    # --- Pydantic 配置 ---
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,  # 指定读取的文件名
        env_file_encoding="utf-8",  # 编码
        case_sensitive=True,  # 大小写敏感
        extra="ignore"  # 忽略 .env 中多余的字段，不报错
    )


# 实例化配置对象，单例模式
settings = Settings()