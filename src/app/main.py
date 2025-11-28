import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# 导入日志和中间件
from app.core.middleware import LogMiddleware
from app.utils.logger import logger

# 🔴 导入路由和数据库初始化函数
from app.api.endpoints import router as api_router
from app.core.db_auth import create_db_and_tables

# 加载 .env
load_dotenv()


# --- 生命周期管理器 (推荐的 FastAPI 新写法) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动时：初始化数据库表结构
    logger.info("🚀 System Startup: Initializing Database...")
    create_db_and_tables()
    logger.success("✅ Database tables created successfully.")

    yield

    # 2. 关闭时 (可选)
    logger.info("🛑 System Shutdown.")


# 初始化 APP
app = FastAPI(
    title="AI Interview Agent API",
    description="基于 LangChain 的智能面试准备助手",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan  # 挂载 lifespan
)

# CORS 配置
origins = [
    "http://localhost",
    "http://localhost:3000",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册日志中间件
app.add_middleware(LogMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api/v1", tags=["Interview"])


@app.get("/", tags=["System"])
async def root():
    return {
        "status": "online",
        "message": "Welcome to AI Interview Agent API. Visit /docs for Swagger UI."
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)