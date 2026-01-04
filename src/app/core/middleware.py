import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from utils.logger import logger
from schemas import ErrorResponse, ErrorCode
from core.monitoring import (
    api_requests_total,
    api_request_duration_seconds,
    api_active_connections,
)


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host
        url_path = request.url.path
        request_id = str(uuid.uuid4())

        # 在请求头中添加请求ID
        request.state.request_id = request_id

        # 增加活跃连接数
        api_active_connections.inc()

        # 1. 记录请求进入
        logger.info(
            f"➡️ [REQ] {request.method} {url_path} | IP: {client_ip} | RequestID: {request_id}"
        )

        try:
            # 执行实际的请求处理
            response = await call_next(request)

            # 2. 计算耗时
            process_time = (time.time() - start_time) * 1000

            # 记录请求指标
            api_requests_total.labels(
                method=request.method,
                endpoint=url_path,
                status_code=response.status_code,
            ).inc()

            api_request_duration_seconds.labels(
                method=request.method, endpoint=url_path
            ).observe(
                process_time / 1000
            )  # 转换为秒

            # 3. 记录请求成功返回
            logger.info(
                f"⬅️ [RES] {response.status_code} | Time: {process_time:.2f}ms | RequestID: {request_id}"
            )

            # 减少活跃连接数
            api_active_connections.dec()

            return response

        except Exception as e:
            # 4. 全局异常捕获 (兜底)
            process_time = (time.time() - start_time) * 1000

            # 记录错误指标
            api_requests_total.labels(
                method=request.method, endpoint=url_path, status_code=500
            ).inc()

            api_request_duration_seconds.labels(
                method=request.method, endpoint=url_path
            ).observe(
                process_time / 1000
            )  # 转换为秒

            logger.exception(
                f"❌ [ERR] Request Failed: {str(e)} | RequestID: {request_id}"
            )

            # 减少活跃连接数
            api_active_connections.dec()

            # 使用统一的错误响应格式
            error_response = ErrorResponse(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="服务器内部错误",
                details={"error": str(e)},
                request_id=request_id,
            )

            return JSONResponse(status_code=500, content=error_response.model_dump())
