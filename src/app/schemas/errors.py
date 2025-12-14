from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import HTTPException as FastAPIHTTPException


# 统一错误响应格式
class ErrorResponse(BaseModel):
    """统一的错误响应模型"""
    status: str = Field(default="error", description="响应状态")
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default=None, description="错误详情")
    request_id: Optional[str] = Field(default=None, description="请求ID")


# 自定义HTTP异常类
class APIException(FastAPIHTTPException):
    """自定义API异常类，支持统一错误响应格式"""
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.details = details
        super().__init__(
            status_code=status_code,
            detail={
                "status": "error",
                "code": code,
                "message": message,
                "details": details,
            },
            headers=headers,
        )


# 定义常用错误代码
class ErrorCode:
    """错误代码常量定义"""
    # 通用错误
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # 业务错误
    JD_PARSE_ERROR = "JD_PARSE_ERROR"
    AGENT_WORKFLOW_ERROR = "AGENT_WORKFLOW_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    FILE_PROCESSING_ERROR = "FILE_PROCESSING_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
