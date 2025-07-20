"""
错误分类和处理系统
"""
from enum import Enum
from typing import Optional, Dict, Any
from ..core.logging import get_logger

logger = get_logger(__name__)


class ErrorCategory(Enum):
    """错误分类，用于确定处理策略"""
    TEMPORARY = "temporary"          # 暂时性错误，可重试
    AUTHENTICATION = "auth"          # 认证错误
    VALIDATION = "validation"        # 输入验证错误
    SYSTEM = "system"               # 系统错误
    NETWORK = "network"             # 网络错误
    DATABASE = "database"           # 数据库错误
    UNKNOWN = "unknown"             # 未知错误


class AppError(Exception):
    """应用级错误基类，提供用户友好的错误信息"""
    def __init__(self, 
                 message: str,
                 category: ErrorCategory,
                 user_message: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None,
                 retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.user_message = user_message or self._get_default_user_message()
        self.details = details or {}
        self.retryable = retryable
        
        # 记录错误日志
        logger.error(
            f"AppError: {message}",
            category=category.value,
            user_message=self.user_message,
            details=self.details,
            retryable=retryable
        )
        
    def _get_default_user_message(self) -> str:
        """根据错误类型返回默认的用户友好消息"""
        messages = {
            ErrorCategory.TEMPORARY: "服务暂时不可用，请稍后重试",
            ErrorCategory.AUTHENTICATION: "认证失败，请重新登录",
            ErrorCategory.VALIDATION: "输入有误，请检查后重试",
            ErrorCategory.SYSTEM: "系统错误，我们正在修复",
            ErrorCategory.NETWORK: "网络连接失败，请检查网络",
            ErrorCategory.DATABASE: "数据处理错误，请稍后重试",
            ErrorCategory.UNKNOWN: "出现了意外错误，请稍后重试"
        }
        return messages.get(self.category, "操作失败")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应"""
        return {
            "type": "agent_error",
            "error": self.user_message,
            "error_code": self.category.value,
            "retryable": self.retryable,
            "details": self.details
        }


def translate_error(exception: Exception) -> AppError:
    """将各种异常转换为用户友好的错误"""
    # KeyError - 通常是缓存相关问题
    if isinstance(exception, KeyError):
        key_str = str(exception).strip("'\"")
        # 检查是否是用户ID格式的键
        if key_str.startswith("user_") or len(key_str) == 36:  # UUID长度
            return AppError(
                message=f"Cache key not found: {key_str}",
                category=ErrorCategory.TEMPORARY,
                user_message="系统正在初始化，请稍后重试",
                details={"key": key_str},
                retryable=True
            )
        else:
            return AppError(
                message=str(exception),
                category=ErrorCategory.VALIDATION,
                user_message="请求参数有误，请检查后重试",
                retryable=False
            )
    
    # 网络相关错误
    elif isinstance(exception, (ConnectionError, TimeoutError)):
        return AppError(
            message=str(exception),
            category=ErrorCategory.NETWORK,
            user_message="网络连接失败，请检查网络后重试",
            retryable=True
        )
    
    # 数据库相关错误
    elif hasattr(exception, '__module__') and 'sqlalchemy' in exception.__module__:
        return AppError(
            message=str(exception),
            category=ErrorCategory.DATABASE,
            user_message="数据处理失败，请稍后重试",
            details={"db_error": type(exception).__name__},
            retryable=True
        )
    
    # 认证相关错误
    elif isinstance(exception, (PermissionError, ValueError)) and 'auth' in str(exception).lower():
        return AppError(
            message=str(exception),
            category=ErrorCategory.AUTHENTICATION,
            user_message="认证失败，请重新登录",
            retryable=False
        )
    
    # 验证错误
    elif isinstance(exception, ValueError):
        return AppError(
            message=str(exception),
            category=ErrorCategory.VALIDATION,
            user_message="输入参数有误，请检查后重试",
            retryable=False
        )
    
    # 其他未知错误
    else:
        return AppError(
            message=str(exception),
            category=ErrorCategory.UNKNOWN,
            user_message="抱歉，出现了意外错误，请稍后重试",
            details={"error_type": type(exception).__name__},
            retryable=True
        )


def handle_error(func):
    """
    错误处理装饰器（异步版本）
    自动捕获异常并转换为用户友好的错误消息
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except AppError as e:
            # 已经是AppError，直接抛出
            raise
        except Exception as e:
            # 转换为AppError
            app_error = translate_error(e)
            raise app_error from e
    
    return wrapper


def handle_error_sync(func):
    """
    错误处理装饰器（同步版本）
    自动捕获异常并转换为用户友好的错误消息
    """
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            # 已经是AppError，直接抛出
            raise
        except Exception as e:
            # 转换为AppError
            app_error = translate_error(e)
            raise app_error from e
    
    return wrapper