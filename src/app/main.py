import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# 导入日志和中间件
from app.core.middleware import LogMiddleware
from app.utils.logger import logger

# 🔴 导入路由和数据库初始化函数
from app.core.db_auth import create_db_and_tables
from app.api.api_v1 import api_router

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
    version="3.1.0",
    docs_url="/docs",
    lifespan=lifespan  # 挂载 lifespan
)

# CORS 配置
origins = [
    "http://localhost",
    "http://localhost:3000",
    # "http://localhost:3001"
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

# 注册请求验证错误处理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误，返回统一的错误响应格式"""
    from app.schemas import ErrorResponse, ErrorCode
    
    request_id = getattr(request.state, 'request_id', '')
    
    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="请求参数验证失败",
        details={
            "errors": exc.errors(),
            "body": exc.body
        },
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump()
    )

# 注册HTTP异常处理器（包括APIException）
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常，包括自定义APIException"""
    from app.schemas import ErrorResponse, ErrorCode, APIException
    
    request_id = getattr(request.state, 'request_id', '')
    
    if isinstance(exc, APIException):
        # 处理自定义API异常
        error_response = ErrorResponse(
            code=exc.code,
            message=exc.detail["message"],
            details=exc.details,
            request_id=request_id
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    elif hasattr(exc, 'detail') and isinstance(exc.detail, dict) and 'status' in exc.detail:
        # 处理已经是统一格式的HTTP异常
        error_response = ErrorResponse(
            code=exc.detail.get("code", ErrorCode.INTERNAL_SERVER_ERROR),
            message=exc.detail.get("message", "服务器内部错误"),
            details=exc.detail.get("details"),
            request_id=request_id
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump()
        )
    
    # 处理标准HTTPException
    error_response = ErrorResponse(
        code=ErrorCode.INTERNAL_SERVER_ERROR if exc.status_code >= 500 else ErrorCode.BAD_REQUEST,
        message=exc.detail if isinstance(exc.detail, str) else "服务器内部错误",
        details=None,
        request_id=request_id
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )

# 注册通用异常处理器
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    from app.schemas import ErrorResponse, ErrorCode
    
    request_id = getattr(request.state, 'request_id', '')
    
    # 其他未处理的异常
    error_response = ErrorResponse(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="服务器内部错误",
        details={"error": str(exc)},
        request_id=request_id
    )
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump()
    )

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