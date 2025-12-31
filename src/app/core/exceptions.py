"""
统一异常处理系统
解决当前项目中异常处理不统一的问题
"""

from typing import Dict, Any, Optional
from loguru import logger
import traceback
import sys


class JDAgentError(Exception):
    """基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str = None, 
        details: Dict[str, Any] = None,
        cause: Exception = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        
        # 记录异常
        logger.error(f"[{self.error_code}] {message}", extra={
            "error_code": self.error_code,
            "details": self.details,
            "traceback": traceback.format_exc()
        })
        
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于API响应"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class ConfigurationError(JDAgentError):
    """配置相关错误"""
    pass


class VectorStoreError(JDAgentError):
    """向量数据库相关错误"""
    pass


class VectorStoreConnectionError(VectorStoreError):
    """向量数据库连接错误"""
    pass


class VectorStoreQueryError(VectorStoreError):
    """向量数据库查询错误"""
    pass


class VectorStoreInitializationError(VectorStoreError):
    """向量数据库初始化错误"""
    pass


class CrawlerError(JDAgentError):
    """爬虫相关错误"""
    pass


class CrawlerNetworkError(CrawlerError):
    """网络请求错误"""
    pass


class CrawlerParsingError(CrawlerError):
    """页面解析错误"""
    pass


class CrawlerAuthenticationError(CrawlerError):
    """认证错误（如需要登录）"""
    pass


class RAGError(JDAgentError):
    """RAG系统相关错误"""
    pass


class RAGRetrievalError(RAGError):
    """检索相关错误"""
    pass


class RAGGenerationError(RAGError):
    """生成相关错误"""
    pass


class DataProcessingError(JDAgentError):
    """数据处理相关错误"""
    pass


class CacheError(JDAgentError):
    """缓存相关错误"""
    pass


class ValidationError(JDAgentError):
    """数据验证错误"""
    pass


class APIError(JDAgentError):
    """API相关错误"""
    pass


class ExternalServiceError(JDAgentError):
    """外部服务错误"""
    pass


class ModelError(JDAgentError):
    """模型相关错误"""
    pass


class ModelLoadingError(ModelError):
    """模型加载错误"""
    pass


class ModelInferenceError(ModelError):
    """模型推理错误"""
    pass


class TaskQueueError(JDAgentError):
    """任务队列相关错误"""
    pass


class MonitoringError(JDAgentError):
    """监控相关错误"""
    pass


class SecurityError(JDAgentError):
    """安全相关错误"""
    pass


class RateLimitError(SecurityError):
    """频率限制错误"""
    pass


class AuthenticationError(SecurityError):
    """认证错误"""
    pass


class AuthorizationError(SecurityError):
    """授权错误"""
    pass


# 错误代码常量
ERROR_CODES = {
    # 配置错误
    "CONFIGURATION_ERROR": "配置错误",
    "CONFIGURATION_MISSING": "配置缺失",
    "CONFIGURATION_INVALID": "配置无效",
    
    # 向量数据库错误
    "VECTOR_STORE_ERROR": "向量数据库错误",
    "VECTOR_STORE_CONNECTION_ERROR": "向量数据库连接失败",
    "VECTOR_STORE_QUERY_ERROR": "向量数据库查询失败",
    "VECTOR_STORE_INITIALIZATION_ERROR": "向量数据库初始化失败",
    
    # 爬虫错误
    "CRAWLER_ERROR": "爬虫错误",
    "CRAWLER_NETWORK_ERROR": "网络请求失败",
    "CRAWLER_PARSING_ERROR": "页面解析失败",
    "CRAWLER_AUTHENTICATION_ERROR": "需要登录认证",
    "CRAWLER_RATE_LIMIT": "爬虫频率限制",
    "CRAWLER_TIMEOUT": "爬虫超时",
    
    # RAG系统错误
    "RAG_ERROR": "RAG系统错误",
    "RAG_RETRIEVAL_ERROR": "检索失败",
    "RAG_GENERATION_ERROR": "生成失败",
    "RAG_EMPTY_CONTEXT": "上下文为空",
    
    # 数据处理错误
    "DATA_PROCESSING_ERROR": "数据处理错误",
    "DATA_VALIDATION_ERROR": "数据验证失败",
    "DATA_CONVERSION_ERROR": "数据转换失败",
    "DATA_CORRUPTION": "数据损坏",
    
    # 缓存错误
    "CACHE_ERROR": "缓存错误",
    "CACHE_CONNECTION_ERROR": "缓存连接失败",
    "CACHE_MISS": "缓存未命中",
    "CACHE_OVERFLOW": "缓存溢出",
    
    # 模型错误
    "MODEL_ERROR": "模型错误",
    "MODEL_LOADING_ERROR": "模型加载失败",
    "MODEL_INFERENCE_ERROR": "模型推理失败",
    "MODEL_UNAVAILABLE": "模型不可用",
    
    # API错误
    "API_ERROR": "API错误",
    "API_REQUEST_ERROR": "API请求失败",
    "API_RESPONSE_ERROR": "API响应错误",
    "API_RATE_LIMIT": "API频率限制",
    
    # 外部服务错误
    "EXTERNAL_SERVICE_ERROR": "外部服务错误",
    "EXTERNAL_SERVICE_UNAVAILABLE": "外部服务不可用",
    "EXTERNAL_SERVICE_TIMEOUT": "外部服务超时",
    
    # 安全错误
    "SECURITY_ERROR": "安全错误",
    "RATE_LIMIT_ERROR": "频率限制",
    "AUTHENTICATION_ERROR": "认证失败",
    "AUTHORIZATION_ERROR": "授权失败",
    
    # 任务队列错误
    "TASK_QUEUE_ERROR": "任务队列错误",
    "TASK_QUEUE_FULL": "任务队列已满",
    "TASK_EXECUTION_ERROR": "任务执行失败",
    
    # 监控错误
    "MONITORING_ERROR": "监控错误",
    "MONITORING_DATA_ERROR": "监控数据错误",
    "MONITORING_ALERT_ERROR": "监控告警失败",
}


class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_error(
        error: Exception, 
        context: str = "", 
        details: Dict[str, Any] = None,
        reraise: bool = True
    ) -> Optional[JDAgentError]:
        """
        统一错误处理
        
        Args:
            error: 原始异常
            context: 错误上下文
            details: 额外详细信息
            reraise: 是否重新抛出异常
            
        Returns:
            处理后的异常对象
        """
        # 如果已经是JDAgentError，直接处理
        if isinstance(error, JDAgentError):
            if context:
                error.details["context"] = context
            if details:
                error.details.update(details)
            
            logger.error(f"[{context}] {error.message}", extra={
                "error_code": error.error_code,
                "details": error.details
            })
            
            if reraise:
                raise error
            return error
        
        # 转换标准异常为JDAgentError
        error_mapping = {
            ConnectionError: VectorStoreConnectionError,
            TimeoutError: CrawlerNetworkError,
            ValueError: ValidationError,
            KeyError: ValidationError,
            FileNotFoundError: DataProcessingError,
            PermissionError: SecurityError,
        }
        
        # 根据异常类型选择合适的错误类
        error_class = error_mapping.get(type(error), JDAgentError)
        
        # 构建错误信息
        error_details = details or {}
        if context:
            error_details["context"] = context
        if hasattr(error, '__cause__') and error.__cause__:
            error_details["cause"] = str(error.__cause__)
        
        # 创建新的错误对象
        jd_error = error_class(
            message=str(error),
            error_code=error.__class__.__name__,
            details=error_details,
            cause=error
        )
        
        if reraise:
            raise jd_error
        return jd_error
    
    @staticmethod
    def safe_execute(func, *args, **kwargs):
        """安全执行函数，返回结果或None"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            ErrorHandler.handle_error(e, f"safe_execute_{func.__name__}")
            return None
    
    @staticmethod
    def log_and_return(error: Exception, default_value=None):
        """记录错误并返回默认值"""
        ErrorHandler.handle_error(error, reraise=False)
        return default_value


def create_error_response(error: Exception, request_id: str = None) -> Dict[str, Any]:
    """创建标准化的错误响应"""
    if isinstance(error, JDAgentError):
        response = error.to_dict()
    else:
        response = {
            "error_code": error.__class__.__name__,
            "message": str(error),
            "details": {},
            "timestamp": ErrorHandler._get_timestamp()
        }
    
    if request_id:
        response["request_id"] = request_id
    
    return {
        "success": False,
        "error": response
    }


# 装饰器：自动处理异常
def handle_exceptions(context: str = "", reraise: bool = True):
    """异常处理装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                ErrorHandler.handle_error(e, context or func.__name__, reraise=reraise)
                if not reraise:
                    return None
                raise
        return wrapper
    return decorator


# 上下文管理器：自动处理异常
class ErrorContext:
    """错误处理上下文管理器"""
    
    def __init__(self, context: str, details: Dict[str, Any] = None):
        self.context = context
        self.details = details or {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            ErrorHandler.handle_error(exc_val, self.context, self.details, reraise=False)


# 工具函数
def _get_timestamp() -> str:
    """获取当前时间戳"""
    from datetime import datetime
    return datetime.now().isoformat()


def assert_config_exists(config_value: Any, config_name: str, error_class = ConfigurationError):
    """断言配置项存在"""
    if not config_value:
        raise error_class(
            message=f"配置项不存在: {config_name}",
            error_code="CONFIGURATION_MISSING",
            details={"config_name": config_name}
        )


def assert_file_exists(file_path: str, error_class = DataProcessingError):
    """断言文件存在"""
    import os
    if not os.path.exists(file_path):
        raise error_class(
            message=f"文件不存在: {file_path}",
            error_code="DATA_VALIDATION_ERROR",
            details={"file_path": file_path}
        )