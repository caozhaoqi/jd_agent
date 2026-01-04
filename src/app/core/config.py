from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from loguru import logger
import os

current_file_dir = os.path.dirname(os.path.abspath(__file__))

project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))

# 拼接 .env 路径
ENV_PATH = os.path.join(project_root, ".env")

logger.debug(f"🔧 [Config] Loading .env from: {ENV_PATH}")


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

    # --- 安全配置 (高优先级) ---
    # 必填项：如果没有在 .env 中设置，程序启动会因 Pydantic 校验失败而报错
    SECRET_KEY: str

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

    # --- 向量数据库配置 ---
    VECTOR_DB_PATH: str = "/Users/caozhaoqi/PycharmProjects/JD_agent/src/app/data/vector_db"
    VECTOR_DB_COLLECTION: str = "jd_agent_knowledge"

    # --- 嵌入模型配置 ---
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"
    EMBEDDING_MODEL_NAME: str = "shibing624/text2vec-base-chinese"

    # --- 爬虫配置 ---
    CRAWLER_DELAY_MIN: float = 2.0
    CRAWLER_DELAY_MAX: float = 5.0
    CRAWLER_MAX_RETRIES: int = 3

    # --- 缓存配置 ---
    CACHE_TTL: int = 3600
    CACHE_MAX_SIZE: int = 1000

    # --- HuggingFace 配置 ---
    HF_ENDPOINT: str = "https://hf-mirror.com"

    # --- 日志配置 ---
    LOG_LEVEL: str = "INFO"

    # --- 模型配置 ---
    MODEL_MAX_TOKENS: int = 1000
    MODEL_TEMPERATURE: float = 0.1

    @property
    def effective_audio_key(self):
        return self.AUDIO_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_audio_base(self):
        return self.AUDIO_API_BASE or self.OPENAI_API_BASE

    # --- Redis 配置 ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Redis 性能优化配置
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5  # 连接超时时间
    REDIS_SOCKET_TIMEOUT: int = 30  # 读写超时时间
    REDIS_MAX_CONNECTIONS: int = 50  # 最大连接数
    REDIS_RETRY_ON_TIMEOUT: bool = True  # 超时后重试

    # 缓存过期时间配置（秒）
    CACHE_EXPIRATION_DEFAULT: int = 3600  # 默认缓存过期时间（1小时）
    CACHE_EXPIRATION_SHORT: int = 300  # 短时间缓存（5分钟）
    CACHE_EXPIRATION_LONG: int = 604800  # 长时间缓存（7天）
    CACHE_EXPIRATION_LLM: int = 259200  # LLM结果缓存（3天）
    CACHE_EXPIRATION_COMPANY_RESEARCH: int = 604800  # 公司研究缓存（7天）

    @property
    def effective_redis_url(self):
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- Confluence 配置 ---
    CONFLUENCE_URL: Optional[str] = None  # Confluence服务器地址
    CONFLUENCE_USERNAME: Optional[str] = None  # 用户名/邮箱
    CONFLUENCE_PASSWORD: Optional[str] = None  # 密码/API令牌
    CONFLUENCE_SPACE_KEYS: List[str] = []  # 要同步的空间key列表
    CONFLUENCE_PAGE_SIZE: int = 50  # 每次请求的页面数量
    CONFLUENCE_MAX_RETRIES: int = 3  # 请求重试次数

    # --- Pydantic 配置 ---
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,  # 指定读取的文件名
        env_file_encoding="utf-8",  # 编码
        case_sensitive=True,  # 大小写敏感
        extra="ignore",  # 忽略 .env 中多余的字段，不报错
    )


# 实例化配置对象，单例模式
settings = Settings()
