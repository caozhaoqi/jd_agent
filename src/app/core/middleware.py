import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.utils.logger import logger


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host
        url_path = request.url.path

        # 1. 记录请求进入
        logger.info(f"➡️ [REQ] {request.method} {url_path} | IP: {client_ip}")

        try:
            # 执行实际的请求处理
            response = await call_next(request)

            # 2. 计算耗时
            process_time = (time.time() - start_time) * 1000

            # 3. 记录请求成功返回
            logger.info(f"⬅️ [RES] {response.status_code} | Time: {process_time:.2f}ms")

            return response

        except Exception as e:
            # 4. 全局异常捕获 (兜底)
            process_time = (time.time() - start_time) * 1000
            logger.exception(f"❌ [ERR] Request Failed: {str(e)}")

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "error": str(e)}
            )