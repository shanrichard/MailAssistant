"""
测试重试机制
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
import time
from datetime import datetime

from app.core.retry import (
    RetryPolicy, DEFAULT_RETRY_POLICY, CONVERSATION_RETRY_POLICY,
    DATABASE_RETRY_POLICY, with_retry, RetryContext
)
from app.core.errors import AppError, ErrorCategory


class TestRetryPolicy:
    """测试重试策略"""
    
    def test_default_policy(self):
        """测试默认策略"""
        policy = DEFAULT_RETRY_POLICY
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
    
    def test_is_retryable_exceptions(self):
        """测试异常是否可重试"""
        policy = RetryPolicy()
        
        # 可重试的异常
        assert policy.is_retryable(KeyError("test"))
        assert policy.is_retryable(ConnectionError("test"))
        assert policy.is_retryable(TimeoutError("test"))
        
        # 不可重试的异常（ValueError会被转换为VALIDATION类型，不可重试）
        assert not policy.is_retryable(ValueError("test"))
        # TypeError会被转换为UNKNOWN类型，默认是可重试的
        assert policy.is_retryable(TypeError("test"))
    
    def test_is_retryable_app_errors(self):
        """测试AppError是否可重试"""
        policy = RetryPolicy()
        
        # 可重试的AppError
        temp_error = AppError("test", ErrorCategory.TEMPORARY, retryable=True)
        assert policy.is_retryable(temp_error)
        
        network_error = AppError("test", ErrorCategory.NETWORK)
        assert policy.is_retryable(network_error)
        
        # 不可重试的AppError
        auth_error = AppError("test", ErrorCategory.AUTHENTICATION, retryable=False)
        assert not policy.is_retryable(auth_error)
    
    def test_calculate_delay(self):
        """测试延迟计算"""
        policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, max_delay=10.0)
        
        # 第0次重试：1秒
        delay0 = policy.calculate_delay(0)
        assert 0.9 <= delay0 <= 1.1  # 考虑抖动
        
        # 第1次重试：2秒
        delay1 = policy.calculate_delay(1)
        assert 1.8 <= delay1 <= 2.2
        
        # 第2次重试：4秒
        delay2 = policy.calculate_delay(2)
        assert 3.6 <= delay2 <= 4.4
        
        # 超过最大延迟
        delay_max = policy.calculate_delay(10)
        assert delay_max <= 10.0 * 1.1  # 最大延迟 + 抖动


class TestWithRetryDecorator:
    """测试重试装饰器"""
    
    @pytest.mark.asyncio
    async def test_async_success_first_try(self):
        """测试第一次就成功的情况"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_attempts=3))
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_then_success(self):
        """测试重试后成功的情况"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary error")
            return "success"
        
        start = time.time()
        result = await test_func()
        elapsed = time.time() - start
        
        assert result == "success"
        assert call_count == 3
        assert elapsed >= 0.2  # 至少经过了两次重试延迟
    
    @pytest.mark.asyncio
    async def test_async_all_retries_fail(self):
        """测试所有重试都失败的情况"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("persistent error")
        
        with pytest.raises(AppError) as exc_info:
            await test_func()
        
        assert call_count == 3
        assert exc_info.value.category == ErrorCategory.NETWORK
        assert exc_info.value.retryable is True
    
    @pytest.mark.asyncio
    async def test_non_retryable_error(self):
        """测试不可重试的错误"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_attempts=3))
        async def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("non-retryable error")
        
        with pytest.raises(AppError) as exc_info:
            await test_func()
        
        assert call_count == 1  # 不应该重试
        assert exc_info.value.category == ErrorCategory.VALIDATION
    
    def test_sync_retry(self):
        """测试同步函数重试"""
        call_count = 0
        
        @with_retry(RetryPolicy(max_attempts=3, base_delay=0.1))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("timeout")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert call_count == 2


class TestRetryContext:
    """测试重试上下文管理器"""
    
    @pytest.mark.asyncio
    async def test_retry_context_success(self):
        """测试上下文管理器成功执行"""
        async def test_operation(value):
            return f"result: {value}"
        
        async with RetryContext(RetryPolicy(max_attempts=3)) as retry:
            result = await retry.execute(test_operation, "test")
            assert result == "result: test"
    
    @pytest.mark.asyncio
    async def test_retry_context_with_retries(self):
        """测试上下文管理器重试"""
        call_count = 0
        
        async def test_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("temp error")
            return "success"
        
        async with RetryContext(RetryPolicy(max_attempts=3, base_delay=0.1)) as retry:
            result = await retry.execute(test_operation)
            assert result == "success"
            assert call_count == 2


class TestSpecializedPolicies:
    """测试特定的重试策略"""
    
    def test_conversation_retry_policy(self):
        """测试对话处理重试策略"""
        policy = CONVERSATION_RETRY_POLICY
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 0.5
        assert policy.max_delay == 10.0
        
        # 测试可重试的错误类型
        assert policy.is_retryable(KeyError("test"))
        assert policy.is_retryable(
            AppError("test", ErrorCategory.TEMPORARY)
        )
    
    def test_database_retry_policy(self):
        """测试数据库重试策略"""
        policy = DATABASE_RETRY_POLICY
        
        assert policy.max_attempts == 2
        assert policy.base_delay == 2.0
        assert policy.max_delay == 30.0
        
        # 只有数据库错误可重试
        assert policy.is_retryable(
            AppError("test", ErrorCategory.DATABASE)
        )
        assert not policy.is_retryable(
            AppError("test", ErrorCategory.NETWORK)
        )


if __name__ == "__main__":
    # 运行基本测试
    test = TestWithRetryDecorator()
    asyncio.run(test.test_async_retry_then_success())
    print("Retry mechanism tests passed!")