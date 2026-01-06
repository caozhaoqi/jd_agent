import uvicorn
import os
import sys
# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prometheus_client import (
    generate_latest,
    Counter,
    Histogram,
    Gauge,
    CONTENT_TYPE_LATEST,
)

# ===== 添加在文件最开头 =====
# 设置HuggingFace国内镜像源和缓存目录
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 使用 HF_HOME 作为唯一的缓存目录，兼容新版 transformers
os.environ["HF_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".huggingface_cache")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sentence_transformers")


print("=" * 50)
print("🎯 HuggingFace配置信息:")
print(f"🔗 镜像源: {os.environ.get('HF_ENDPOINT')}")
print(f"📁 缓存目录 (HF_HOME): {os.environ.get('HF_HOME')}")
print("=" * 50)

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# 导入日志和中间件
from core.middleware import LogMiddleware
from utils.logger import logger
from core.monitoring import start_system_monitor

# 🔴 导入路由和数据库初始化函数
from core.db_auth import create_db_and_tables
from api.api_v1 import api_router
from api.api_v2 import api_router as api_router_v2
from api.routers.knowledge_graph import router as knowledge_graph_router
from api.routers.interview_style import router as interview_style_router
from api.routers.team import router as team_router
from api.routers.report_export import router as report_export_router

# 加载 .env
load_dotenv()


# --- 生命周期管理器 (推荐的 FastAPI 新写法) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 启动时：初始化数据库表结构
    logger.info("🚀 System Startup: Initializing Database...")
    create_db_and_tables()
    logger.success("✅ Database tables created successfully.")

    # 2. 启动系统资源监控
    logger.info("📊 System Startup: Starting System Resource Monitoring...")
    start_system_monitor()
    logger.success("✅ System Resource Monitoring started successfully.")

    yield

    # 3. 关闭时 (可选)
    logger.info("🛑 System Shutdown.")


# 初始化 APP
app = FastAPI(
    title="AI Interview Agent API",
    description="基于 LangChain 的智能面试准备助手",
    version="3.1.0",
    docs_url="/docs",
    lifespan=lifespan,  # 挂载 lifespan
)

# CORS 配置
origins = [
    "http://localhost",
    "http://localhost:3000",
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
    from schemas import ErrorResponse, ErrorCode

    request_id = getattr(request.state, "request_id", "")

    error_response = ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="请求参数验证失败",
        details={"errors": exc.errors(), "body": exc.body},
        request_id=request_id,
    )

    return JSONResponse(status_code=422, content=error_response.model_dump())


# 注册HTTP异常处理器（包括APIException）
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常，包括自定义APIException"""
    from schemas import ErrorResponse, ErrorCode, APIException

    request_id = getattr(request.state, "request_id", "")

    if isinstance(exc, APIException):
        error_response = ErrorResponse(
            code=exc.code,
            message=exc.detail["message"],
            details=exc.details,
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )
    elif (
        hasattr(exc, "detail")
        and isinstance(exc.detail, dict)
        and "status" in exc.detail
    ):
        error_response = ErrorResponse(
            code=exc.detail.get("code", ErrorCode.INTERNAL_SERVER_ERROR),
            message=exc.detail.get("message", "服务器内部错误"),
            details=exc.detail.get("details"),
            request_id=request_id,
        )
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    error_response = ErrorResponse(
        code=(
            ErrorCode.INTERNAL_SERVER_ERROR
            if exc.status_code >= 500
            else ErrorCode.BAD_REQUEST
        ),
        message=exc.detail if isinstance(exc.detail, str) else "服务器内部错误",
        details=None,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump()
    )


# 注册通用异常处理器
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    from schemas import ErrorResponse, ErrorCode

    request_id = getattr(request.state, "request_id", "")

    error_response = ErrorResponse(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="服务器内部错误",
        details={"error": str(exc)},
        request_id=request_id,
    )
    return JSONResponse(status_code=500, content=error_response.model_dump())


# 注册路由
app.include_router(api_router, prefix="/api/v1", tags=["Interview v1"])
app.include_router(api_router_v2, prefix="/api/v2", tags=["Interview v2"])
app.include_router(knowledge_graph_router, prefix="/api/v1/knowledge", tags=["Knowledge Graph"])
app.include_router(interview_style_router, prefix="/api/v1/interview", tags=["Interview Style"])
app.include_router(team_router, prefix="/api/v1/teams", tags=["Team Management"])
app.include_router(report_export_router, prefix="/api/v1/reports", tags=["Report Export"])


@app.get("/", tags=["System"])
async def root():
    return {
        "status": "online",
        "message": "Welcome to AI Interview Agent API. Visit /docs for Swagger UI.",
    }


@app.get("/health", tags=["System"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "message": "Service is running normally",
        "timestamp": str(__import__('datetime').datetime.now())
    }

# 性能监控端点
@app.get("/api/v1/monitoring/metrics", tags=["Monitoring"])
async def get_metrics():
    """获取Prometheus格式的监控指标"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/api/v1/monitoring/system", tags=["Monitoring"])
async def get_system_metrics():
    """获取系统资源监控指标"""
    import psutil
    import os
    
    return {
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        },
        "memory": {
            "total_bytes": psutil.virtual_memory().total,
            "available_bytes": psutil.virtual_memory().available,
            "used_bytes": psutil.virtual_memory().used,
            "percent": psutil.virtual_memory().percent
        },
        "disk": {
            "total_bytes": psutil.disk_usage("/").total,
            "used_bytes": psutil.disk_usage("/").used,
            "free_bytes": psutil.disk_usage("/").free,
            "percent": psutil.disk_usage("/").percent
        },
        "process": {
            "memory_rss_bytes": psutil.Process(os.getpid()).memory_info().rss,
            "cpu_percent": psutil.Process(os.getpid()).cpu_percent(interval=1),
            "num_threads": psutil.Process(os.getpid()).num_threads()
        }
    }

@app.get("/api/v1/monitoring/performance", tags=["Monitoring"])
async def get_performance_metrics():
    """获取应用性能指标"""
    from core.monitoring import (
        api_requests_total, api_request_duration_seconds,
        cache_hits, cache_misses, llm_calls_total, llm_call_duration_seconds
    )
    
    return {
        "api": {
            "total_requests": sum(api_requests_total._metrics.values()),
            "avg_duration": api_request_duration_seconds.observe if hasattr(api_request_duration_seconds, 'observe') else 0
        },
        "cache": {
            "hits": cache_hits._value.get() if hasattr(cache_hits, '_value') else 0,
            "misses": cache_misses._value.get() if hasattr(cache_misses, '_value') else 0
        },
        "llm": {
            "total_calls": sum(llm_calls_total._metrics.values()),
            "avg_duration": llm_call_duration_seconds.observe if hasattr(llm_call_duration_seconds, 'observe') else 0
        }
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Expose Prometheus metrics"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_config=None)
