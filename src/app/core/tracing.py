"""
全链路监控配置
使用OpenTelemetry实现分布式追踪和全链路监控
"""

import os
import asyncio
from utils.logger import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from fastapi import FastAPI, Request
from functools import wraps
import redis
import sqlalchemy



# 配置全局变量
TRACE_SERVICE_NAME = os.getenv("TRACE_SERVICE_NAME", "ai-interview-agent")
TRACE_EXPORTER_URL = os.getenv("TRACE_EXPORTER_URL", "http://localhost:4317")
TRACE_SAMPLE_RATE = float(os.getenv("TRACE_SAMPLE_RATE", "1.0"))  # 1.0 = 100%

# 初始化追踪提供器
trace_provider = TracerProvider(
    resource=Resource.create({
        SERVICE_NAME: TRACE_SERVICE_NAME
    })
)

# 设置全局追踪提供器
trace.set_tracer_provider(trace_provider)

# 创建OTLP导出器
otlp_exporter = OTLPSpanExporter(
    endpoint=TRACE_EXPORTER_URL,
    insecure=True  # 开发环境使用不安全连接
)

# 创建批处理导出器处理器
span_processor = BatchSpanProcessor(otlp_exporter)

# 将处理器添加到追踪提供器
trace_provider.add_span_processor(span_processor)

# 创建全局追踪器
tracer = trace.get_tracer(__name__)

# 传播器
trace_propagator = TraceContextTextMapPropagator()


def instrument_fastapi(app: FastAPI):
    """为FastAPI应用添加追踪"""
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✅ FastAPI 追踪已启用")
    except Exception as e:
        logger.error(f"❌ FastAPI 追踪启用失败: {e}")


def instrument_httpx():
    """为HTTPX客户端添加追踪"""
    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("✅ HTTPX 客户端追踪已启用")
    except Exception as e:
        logger.error(f"❌ HTTPX 客户端追踪启用失败: {e}")


def instrument_redis(redis_client: redis.Redis):
    """为Redis客户端添加追踪"""
    try:
        RedisInstrumentor().instrument_client(redis_client)
        logger.info("✅ Redis 客户端追踪已启用")
    except Exception as e:
        logger.error(f"❌ Redis 客户端追踪启用失败: {e}")


def instrument_sqlalchemy(engine: sqlalchemy.Engine):
    """为SQLAlchemy引擎添加追踪"""
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("✅ SQLAlchemy 追踪已启用")
    except Exception as e:
        logger.error(f"❌ SQLAlchemy 追踪启用失败: {e}")


def trace_decorator(operation_name: str):
    """用于装饰函数的追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(operation_name) as span:
                try:
                    # 记录参数信息
                    for i, arg in enumerate(args):
                        if i < 3:  # 只记录前3个参数，避免过多信息
                            span.set_attribute(f"param_{i}", str(arg)[:100])  # 截断过长的参数值
                    
                    # 记录关键字参数
                    for key, value in kwargs.items():
                        if key != "self" and key != "cls":  # 跳过self和cls
                            span.set_attribute(key, str(value)[:100])  # 截断过长的值
                    
                    result = func(*args, **kwargs)
                    
                    # 记录成功结果
                    span.set_attribute("status", "success")
                    return result
                    
                except Exception as e:
                    # 记录错误信息
                    span.set_attribute("status", "error")
                    span.set_attribute("error.message", str(e)[:200])
                    raise
        return wrapper
    return decorator


async def trace_middleware(request: Request, call_next):
    """FastAPI追踪中间件"""
    with tracer.start_as_current_span("http_request") as span:
        # 设置请求属性
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.path", request.url.path)
        span.set_attribute("http.host", request.headers.get("host", "unknown"))
        span.set_attribute("user-agent", request.headers.get("user-agent", "unknown"))
        
        # 从请求头中提取追踪上下文
        try:
            carrier = dict(request.headers)
            ctx = trace_propagator.extract(carrier)
            trace.get_current_span().set_parent(ctx)
        except Exception as e:
            logger.warning(f"❌ 提取追踪上下文失败: {e}")
        
        # 处理请求
        response = await call_next(request)
        
        # 设置响应属性
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.response_content_length", response.headers.get("content-length", "unknown"))
        
        return response


def init_tracing():
    """初始化全链路追踪"""
    try:
        logger.info("📊 初始化全链路追踪...")
        
        # 打印配置信息
        logger.info(f"  服务名称: {TRACE_SERVICE_NAME}")
        logger.info(f"  导出器地址: {TRACE_EXPORTER_URL}")
        logger.info(f"  采样率: {TRACE_SAMPLE_RATE * 100}%")
        
        # 自动检测并Instrument常用库
        instrument_httpx()
        
        logger.info("✅ 全链路追踪初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 全链路追踪初始化失败: {e}")
        return False


def get_current_trace_context():
    """获取当前追踪上下文"""
    span = trace.get_current_span()
    if not span:
        return None
    
    ctx = trace.get_current_span().get_span_context()
    if not ctx.trace_id:
        return None
    
    # 创建载体并注入上下文
    carrier = {}
    trace_propagator.inject(carrier)
    
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
        "trace_flags": ctx.trace_flags,
        "carrier": carrier
    }


def trace_function(func):
    """为异步函数添加追踪的装饰器"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        operation_name = f"{func.__module__}.{func.__name__}"
        with tracer.start_as_current_span(operation_name) as span:
            try:
                # 记录函数信息
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                result = await func(*args, **kwargs)
                span.set_attribute("status", "success")
                return result
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error.message", str(e)[:200])
                raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        operation_name = f"{func.__module__}.{func.__name__}"
        with tracer.start_as_current_span(operation_name) as span:
            try:
                # 记录函数信息
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                result = func(*args, **kwargs)
                span.set_attribute("status", "success")
                return result
            except Exception as e:
                span.set_attribute("status", "error")
                span.set_attribute("error.message", str(e)[:200])
                raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
