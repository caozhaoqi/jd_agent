"""
统一错误处理工具模块
提供全局统一的错误抛出、捕获和处理机制
"""
from typing import Optional, Dict, Any
from app.schemas.errors import APIException, ErrorCode
from loguru import logger


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    log_error: bool = True,
) -> None:
    """
    抛出统一格式的API错误
    
    Args:
        status_code: HTTP状态码
        code: 错误代码
        message: 错误消息
        details: 错误详情
        headers: 响应头
        log_error: 是否记录错误日志
    """
    if log_error:
        logger.error(f"[API Error] {code}: {message} - Details: {details}")
    
    raise APIException(
        status_code=status_code,
        code=code,
        message=message,
        details=details,
        headers=headers
    )


def raise_internal_error(
    message: str = "服务器内部错误",
    details: Optional[Dict[str, Any]] = None,
    exc: Optional[Exception] = None
) -> None:
    """
    抛出内部服务器错误
    
    Args:
        message: 错误消息
        details: 错误详情
        exc: 原始异常
    """
    if exc:
        logger.exception(f"[Internal Error] {message}")
        if details is None:
            details = {"error": str(exc)}
        else:
            details["original_error"] = str(exc)
    
    raise_api_error(
        status_code=500,
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=message,
        details=details
    )


def raise_bad_request(
    message: str = "请求参数错误",
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    抛出请求参数错误
    
    Args:
        message: 错误消息
        details: 错误详情
    """
    raise_api_error(
        status_code=400,
        code=ErrorCode.BAD_REQUEST,
        message=message,
        details=details
    )


def raise_unauthorized(
    message: str = "未授权访问",
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    抛出未授权错误
    
    Args:
        message: 错误消息
        details: 错误详情
    """
    raise_api_error(
        status_code=401,
        code=ErrorCode.UNAUTHORIZED,
        message=message,
        details=details
    )


def raise_forbidden(
    message: str = "访问被拒绝",
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    抛出禁止访问错误
    
    Args:
        message: 错误消息
        details: 错误详情
    """
    raise_api_error(
        status_code=403,
        code=ErrorCode.FORBIDDEN,
        message=message,
        details=details
    )


def raise_not_found(
    message: str = "资源不存在",
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    抛出资源不存在错误
    
    Args:
        message: 错误消息
        details: 错误详情
    """
    raise_api_error(
        status_code=404,
        code=ErrorCode.NOT_FOUND,
        message=message,
        details=details
    )


def raise_validation_error(
    message: str = "请求参数验证失败",
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    抛出参数验证错误
    
    Args:
        message: 错误消息
        details: 错误详情
    """
    raise_api_error(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details
    )


def handle_exception(
    exc: Exception,
    message: str = "处理请求时发生错误",
    status_code: int = 500,
    code: str = ErrorCode.INTERNAL_SERVER_ERROR
) -> APIException:
    """
    处理异常并转换为统一的APIException
    
    Args:
        exc: 原始异常
        message: 错误消息
        status_code: HTTP状态码
        code: 错误代码
    
    Returns:
        APIException: 统一格式的API异常
    """
    logger.exception(f"[Exception Handled] {message}")
    
    return APIException(
        status_code=status_code,
        code=code,
        message=message,
        details={"error": str(exc)}
    )
