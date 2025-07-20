"""
智能重试机制
"""
import asyncio
from functools import wraps
from typing import Tuple, Type, Callable, Any, Optional, Union
from datetime import datetime
from ..core.logging import get_logger
from ..core.errors import AppError, ErrorCategory, translate_error

logger = get_logger(__name__)


class RetryPolicy:
    """重试策略配置"""
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
                 retryable_error_categories: Optional[Tuple[ErrorCategory, ...]] = None):
        """
        初始化重试策略
        
        Args:
            max_attempts: 最大重试次数
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数退避的基数
            retryable_exceptions: 可重试的异常类型
            retryable_error_categories: 可重试的错误分类
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions or (
            KeyError, ConnectionError, TimeoutError
        )
        self.retryable_error_categories = retryable_error_categories or (
            ErrorCategory.TEMPORARY, ErrorCategory.NETWORK, ErrorCategory.DATABASE
        )
    
    def is_retryable(self, exception: Exception) -> bool:
        """判断异常是否可重试"""
        # 检查是否是可重试的异常类型
        if isinstance(exception, self.retryable_exceptions):
            return True
        
        # 检查是否是可重试的 AppError
        if isinstance(exception, AppError):
            return exception.retryable or exception.category in self.retryable_error_categories
        
        # 对于其他异常，转换后判断
        try:
            app_error = translate_error(exception)
            return app_error.retryable or app_error.category in self.retryable_error_categories
        except:
            return False
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间（指数退避）"""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        # 添加随机抖动（±10%）避免同时重试
        import random
        jitter = delay * 0.1 * (2 * random.random() - 1)
        return max(0, delay + jitter)


# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy()

# 对话处理专用重试策略（更积极）
CONVERSATION_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    retryable_exceptions=(KeyError, ConnectionError, TimeoutError),
    retryable_error_categories=(ErrorCategory.TEMPORARY, ErrorCategory.NETWORK)
)

# 数据库操作重试策略（更保守）
DATABASE_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=2.0,
    max_delay=30.0,
    retryable_error_categories=(ErrorCategory.DATABASE,)
)


def with_retry(policy: Optional[RetryPolicy] = None):
    """
    装饰器：为异步函数添加重试功能
    
    Args:
        policy: 重试策略，如果为 None 则使用默认策略
    """
    if policy is None:
        policy = DEFAULT_RETRY_POLICY
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            start_time = datetime.now()
            
            for attempt in range(policy.max_attempts):
                try:
                    result = await func(*args, **kwargs)
                    
                    # 成功后记录
                    if attempt > 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        logger.info(
                            f"Retry succeeded for {func.__name__}",
                            function=func.__name__,
                            attempt=attempt + 1,
                            elapsed_seconds=elapsed
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # 检查是否可重试
                    if not policy.is_retryable(e) or attempt >= policy.max_attempts - 1:
                        break
                    
                    # 计算延迟时间
                    delay = policy.calculate_delay(attempt)
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{policy.max_attempts} for {func.__name__}",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=policy.max_attempts,
                        delay_seconds=delay,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                    
                    await asyncio.sleep(delay)
            
            # 所有重试都失败
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"All retry attempts failed for {func.__name__}",
                function=func.__name__,
                attempts=policy.max_attempts,
                elapsed_seconds=elapsed,
                error_type=type(last_exception).__name__
            )
            
            # 如果是 AppError，直接抛出
            if isinstance(last_exception, AppError):
                raise last_exception
            
            # 否则转换为用户友好的错误
            raise translate_error(last_exception) from last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            """同步版本的重试包装器"""
            import time
            last_exception = None
            start_time = datetime.now()
            
            for attempt in range(policy.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        elapsed = (datetime.now() - start_time).total_seconds()
                        logger.info(
                            f"Retry succeeded for {func.__name__}",
                            function=func.__name__,
                            attempt=attempt + 1,
                            elapsed_seconds=elapsed
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if not policy.is_retryable(e) or attempt >= policy.max_attempts - 1:
                        break
                    
                    delay = policy.calculate_delay(attempt)
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{policy.max_attempts} for {func.__name__}",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=policy.max_attempts,
                        delay_seconds=delay,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                    
                    time.sleep(delay)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"All retry attempts failed for {func.__name__}",
                function=func.__name__,
                attempts=policy.max_attempts,
                elapsed_seconds=elapsed,
                error_type=type(last_exception).__name__
            )
            
            if isinstance(last_exception, AppError):
                raise last_exception
            
            raise translate_error(last_exception) from last_exception
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RetryContext:
    """
    上下文管理器版本的重试机制
    
    使用示例：
        async with RetryContext(policy=CONVERSATION_RETRY_POLICY) as retry:
            result = await retry.execute(some_async_function, arg1, arg2)
    """
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or DEFAULT_RETRY_POLICY
        self.attempts = 0
        self.last_exception = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行函数，自动应用重试策略"""
        wrapped_func = with_retry(self.policy)(func)
        return await wrapped_func(*args, **kwargs)