"""
测试错误处理系统
"""
import pytest
from app.core.errors import (
    ErrorCategory, AppError, translate_error,
    handle_error, handle_error_sync
)


class TestAppError:
    """测试AppError类"""
    
    def test_app_error_creation(self):
        """测试创建AppError"""
        error = AppError(
            message="Test error",
            category=ErrorCategory.TEMPORARY,
            user_message="测试错误消息",
            details={"key": "value"},
            retryable=True
        )
        
        assert str(error) == "Test error"
        assert error.category == ErrorCategory.TEMPORARY
        assert error.user_message == "测试错误消息"
        assert error.details == {"key": "value"}
        assert error.retryable is True
    
    def test_default_user_messages(self):
        """测试默认用户消息"""
        # 测试各种错误类型的默认消息
        test_cases = [
            (ErrorCategory.TEMPORARY, "服务暂时不可用，请稍后重试"),
            (ErrorCategory.AUTHENTICATION, "认证失败，请重新登录"),
            (ErrorCategory.VALIDATION, "输入有误，请检查后重试"),
            (ErrorCategory.SYSTEM, "系统错误，我们正在修复"),
            (ErrorCategory.NETWORK, "网络连接失败，请检查网络"),
            (ErrorCategory.DATABASE, "数据处理错误，请稍后重试"),
            (ErrorCategory.UNKNOWN, "出现了意外错误，请稍后重试"),
        ]
        
        for category, expected_message in test_cases:
            error = AppError(
                message="Test",
                category=category
            )
            assert error.user_message == expected_message
    
    def test_to_dict(self):
        """测试转换为字典"""
        error = AppError(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            user_message="自定义消息",
            details={"field": "email"},
            retryable=False
        )
        
        result = error.to_dict()
        
        assert result["type"] == "agent_error"
        assert result["error"] == "自定义消息"
        assert result["error_code"] == "validation"
        assert result["retryable"] is False
        assert result["details"] == {"field": "email"}


class TestTranslateError:
    """测试错误转换功能"""
    
    def test_translate_key_error_user_id(self):
        """测试转换用户ID相关的KeyError"""
        # 测试用户ID格式的键
        error = KeyError("user_60f2ccbd-d754-4fa0-aa4d-35a7d6551d38")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.TEMPORARY
        assert app_error.user_message == "系统正在初始化，请稍后重试"
        assert app_error.retryable is True
        assert "user_60f2ccbd-d754-4fa0-aa4d-35a7d6551d38" in app_error.details["key"]
    
    def test_translate_key_error_other(self):
        """测试转换其他KeyError"""
        error = KeyError("invalid_key")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.VALIDATION
        assert app_error.user_message == "请求参数有误，请检查后重试"
        assert app_error.retryable is False
    
    def test_translate_connection_error(self):
        """测试转换网络错误"""
        error = ConnectionError("Network unreachable")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.NETWORK
        assert app_error.user_message == "网络连接失败，请检查网络后重试"
        assert app_error.retryable is True
    
    def test_translate_timeout_error(self):
        """测试转换超时错误"""
        error = TimeoutError("Request timeout")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.NETWORK
        assert app_error.retryable is True
    
    def test_translate_value_error_auth(self):
        """测试转换认证相关的ValueError"""
        error = ValueError("Invalid auth token")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.AUTHENTICATION
        assert app_error.user_message == "认证失败，请重新登录"
        assert app_error.retryable is False
    
    def test_translate_value_error_other(self):
        """测试转换其他ValueError"""
        error = ValueError("Invalid input")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.VALIDATION
        assert app_error.user_message == "输入参数有误，请检查后重试"
        assert app_error.retryable is False
    
    def test_translate_unknown_error(self):
        """测试转换未知错误"""
        error = RuntimeError("Something went wrong")
        app_error = translate_error(error)
        
        assert app_error.category == ErrorCategory.UNKNOWN
        assert app_error.user_message == "抱歉，出现了意外错误，请稍后重试"
        assert app_error.retryable is True
        assert app_error.details["error_type"] == "RuntimeError"


class TestErrorDecorators:
    """测试错误处理装饰器"""
    
    @pytest.mark.asyncio
    async def test_handle_error_async(self):
        """测试异步错误处理装饰器"""
        @handle_error
        async def test_function():
            raise KeyError("user_123")
        
        with pytest.raises(AppError) as exc_info:
            await test_function()
        
        assert exc_info.value.category == ErrorCategory.TEMPORARY
        assert exc_info.value.retryable is True
    
    def test_handle_error_sync(self):
        """测试同步错误处理装饰器"""
        @handle_error_sync
        def test_function():
            raise ValueError("Invalid auth")
        
        with pytest.raises(AppError) as exc_info:
            test_function()
        
        assert exc_info.value.category == ErrorCategory.AUTHENTICATION
        assert exc_info.value.retryable is False
    
    @pytest.mark.asyncio
    async def test_handle_error_app_error_passthrough(self):
        """测试AppError直接传递"""
        custom_error = AppError(
            message="Custom error",
            category=ErrorCategory.SYSTEM,
            user_message="自定义系统错误"
        )
        
        @handle_error
        async def test_function():
            raise custom_error
        
        with pytest.raises(AppError) as exc_info:
            await test_function()
        
        assert exc_info.value is custom_error


if __name__ == "__main__":
    # 运行基本测试
    test = TestTranslateError()
    test.test_translate_key_error_user_id()
    test.test_translate_connection_error()
    print("Basic error translation tests passed!")