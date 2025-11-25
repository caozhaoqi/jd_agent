import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# 1. 加载 .env 环境变量
# 确保在导入其他依赖之前加载，这样 Settings 才能读到 Key
load_dotenv()

# 导入我们的路由模块
# 注意：确保你的目录结构里有 app/api/endpoints.py
from src.app.api.endpoints import router as api_router

# 2. 初始化 FastAPI 应用
app = FastAPI(
    title="AI Interview Agent API",
    description="基于 LangChain 的智能面试准备助手",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 地址
    redoc_url="/redoc"
)

# 3. 配置 CORS (跨域)
# 如果你要对接前端 (React/Vue)，这一步是必须的
origins = [
    "http://localhost",
    "http://localhost:3000", # 常见的前端端口
    "http://localhost:8080",
    "*", # 开发环境允许所有来源，生产环境请改为具体域名
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 注册路由
# 我们将 api 路由挂载到 /api/v1 前缀下
# 访问地址变为: POST http://localhost:8000/api/v1/generate-guide
app.include_router(api_router, prefix="/api/v1", tags=["Interview"])

# 5. 健康检查接口 (Health Check)
@app.get("/", tags=["System"])
async def root():
    return {
        "status": "online",
        "message": "Welcome to AI Interview Agent API. Visit /docs for Swagger UI."
    }

# 6. 启动入口 (可选)
# 这样你可以直接运行 `python app/main.py` 启动，也可以用命令启动
if __name__ == "__main__":
    # reload=True 表示代码修改后自动重启，仅用于开发环境
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)