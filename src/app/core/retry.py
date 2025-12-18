import asyncio
from functools import wraps
from typing import Callable, Any, Optional
from loguru import logger


def retry_async(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    retry_on_result: Optional[Callable[[Any], bool]] = None,
):
    """
    异步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        exceptions: 触发重试的异常类型
        retry_on_result: 基于结果决定是否重试的函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # 检查结果是否需要重试
                    if retry_on_result and callable(retry_on_result):
                        if retry_on_result(result):
                            logger.warning(
                                f"重试条件满足，尝试 {attempt + 1}/{max_retries + 1}"
                            )
                            if attempt < max_retries:
                                await asyncio.sleep(delay * (backoff**attempt))
                                continue

                    return result

                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"函数 {func.__name__} 尝试 {attempt + 1}/{max_retries + 1} 失败: {str(e)}"
                    )

                    if attempt < max_retries:
                        await asyncio.sleep(delay * (backoff**attempt))
                        continue

            # 所有重试都失败
            logger.error(f"函数 {func.__name__} 超过最大重试次数 {max_retries}")
            raise last_exception

        return wrapper

    return decorator


def retry_sync(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    retry_on_result: Optional[Callable[[Any], bool]] = None,
):
    """
    同步函数重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        exceptions: 触发重试的异常类型
        retry_on_result: 基于结果决定是否重试的函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time

            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查结果是否需要重试
                    if retry_on_result and callable(retry_on_result):
                        if retry_on_result(result):
                            logger.warning(
                                f"重试条件满足，尝试 {attempt + 1}/{max_retries + 1}"
                            )
                            if attempt < max_retries:
                                time.sleep(delay * (backoff**attempt))
                                continue

                    return result

                except exceptions as e:
                    last_exception = e
                    logger.warning(
                        f"函数 {func.__name__} 尝试 {attempt + 1}/{max_retries + 1} 失败: {str(e)}"
                    )

                    if attempt < max_retries:
                        time.sleep(delay * (backoff**attempt))
                        continue

            # 所有重试都失败
            logger.error(f"函数 {func.__name__} 超过最大重试次数 {max_retries}")
            raise last_exception

        return wrapper

    return decorator
