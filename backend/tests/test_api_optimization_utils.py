"""
API优化工具模块单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException

from backend.app.utils.api_optimization import (
    monitor_api_performance,
    APIErrorHandler,
    OptimizationConfig,
    execute_with_fallback
)


class TestAPIPerformanceMonitor:
    """测试API性能监控装饰器"""
    
    @patch('backend.app.utils.api_optimization.settings')
    @patch('backend.app.utils.api_optimization.SyncPerformanceMonitor')
    @pytest.mark.asyncio
    async def test_performance_monitor_decorator_enabled(self, mock_monitor_class, mock_settings):
        """测试启用性能监控装饰器"""
        # Mock设置启用监控
        mock_settings.enable_api_performance_monitoring = True
        mock_settings.api_performance_report_threshold = 1.0
        
        # Mock性能监控器
        mock_monitor = Mock()
        mock_monitor.get_report.return_value = {'total_duration': 0.5}
        mock_monitor_class.return_value = mock_monitor
        
        # 创建被装饰的函数
        @monitor_api_performance("test_operation")
        async def test_func():
            return "test_result"
        
        # 执行测试
        result = await test_func()
        
        # 验证结果
        assert result == "test_result"
        mock_monitor.start_monitoring.assert_called_once()
        mock_monitor.start_stage.assert_called_once_with("test_operation")
        mock_monitor.end_stage.assert_called_once_with("test_operation")
        mock_monitor.get_report.assert_called_once()
    
    @patch('backend.app.utils.api_optimization.settings')
    @pytest.mark.asyncio
    async def test_performance_monitor_decorator_disabled(self, mock_settings):
        """测试禁用性能监控装饰器"""
        # Mock设置禁用监控
        mock_settings.enable_api_performance_monitoring = False
        
        # 创建被装饰的函数
        @monitor_api_performance("test_operation")
        async def test_func():
            return "test_result"
        
        # 执行测试
        result = await test_func()
        
        # 验证结果（应该直接调用原函数，无监控开销）
        assert result == "test_result"
    
    @patch('backend.app.utils.api_optimization.settings')
    @patch('backend.app.utils.api_optimization.SyncPerformanceMonitor')
    @pytest.mark.asyncio
    async def test_performance_monitor_decorator_with_error(self, mock_monitor_class, mock_settings):
        """测试性能监控装饰器处理异常"""
        # Mock设置启用监控
        mock_settings.enable_api_performance_monitoring = True
        
        # Mock性能监控器
        mock_monitor = Mock()
        mock_monitor_class.return_value = mock_monitor
        
        # 创建会抛出异常的函数
        @monitor_api_performance("test_operation")
        async def test_func():
            raise ValueError("test error")
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="test error"):
            await test_func()
        
        # 验证错误被记录
        mock_monitor.record_error.assert_called_once()


class TestAPIErrorHandler:
    """测试API错误处理器"""
    
    def test_handle_sync_error_authentication(self):
        """测试API错误处理器 - 认证错误"""
        # 模拟401认证错误
        error = Exception("401 Unauthorized")
        
        # 处理错误
        http_error = APIErrorHandler.handle_sync_error(error, "test_operation")
        
        # 验证返回正确的结构化错误响应
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 401
        assert http_error.detail["error_code"] == "AUTHENTICATION_ERROR"
        assert http_error.detail["operation"] == "test_operation"
        assert "认证已过期" in http_error.detail["message"]
    
    def test_handle_sync_error_rate_limit(self):
        """测试API错误处理器 - 限流错误"""
        # 模拟429限流错误
        error = Exception("quota exceeded")
        
        # 处理错误
        http_error = APIErrorHandler.handle_sync_error(error, "test_operation")
        
        # 验证返回正确的错误码和消息
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 429
        assert http_error.detail["error_code"] == "RATE_LIMIT_ERROR"
        assert "配额已用完" in http_error.detail["message"]
    
    def test_handle_sync_error_timeout(self):
        """测试API错误处理器 - 超时错误"""
        # 模拟超时异常
        error = Exception("timeout occurred")
        
        # 处理错误
        http_error = APIErrorHandler.handle_sync_error(error, "test_operation")
        
        # 验证返回408超时错误响应
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 408
        assert http_error.detail["error_code"] == "TIMEOUT_ERROR"
        assert "超时" in http_error.detail["message"]
    
    def test_handle_sync_error_unknown(self):
        """测试API错误处理器 - 未知错误"""
        # 模拟一般异常
        error = Exception("some unknown error")
        
        # 处理错误
        http_error = APIErrorHandler.handle_sync_error(error, "test_operation")
        
        # 验证返回500内部错误响应
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 500
        assert http_error.detail["error_code"] == "UNKNOWN_ERROR"
        assert "some unknown error" in http_error.detail["message"]
    
    def test_handle_search_error_invalid_query(self):
        """测试搜索错误处理器 - 无效查询"""
        # 模拟查询格式错误
        error = Exception("invalid query syntax")
        
        # 处理错误
        http_error = APIErrorHandler.handle_search_error(error, "search_operation")
        
        # 验证返回400错误响应
        assert isinstance(http_error, HTTPException)
        assert http_error.status_code == 400
        assert http_error.detail["error_code"] == "INVALID_QUERY_ERROR"
        assert "查询格式不正确" in http_error.detail["message"]


class TestOptimizationConfig:
    """测试优化配置管理器"""
    
    @patch('backend.app.utils.api_optimization.settings')
    def test_is_sync_optimization_enabled(self, mock_settings):
        """测试同步优化状态检查"""
        mock_settings.enable_optimized_sync_endpoints = True
        assert OptimizationConfig.is_sync_optimization_enabled() is True
        
        mock_settings.enable_optimized_sync_endpoints = False
        assert OptimizationConfig.is_sync_optimization_enabled() is False
    
    @patch('backend.app.utils.api_optimization.settings')
    def test_is_search_optimization_enabled(self, mock_settings):
        """测试搜索优化状态检查"""
        mock_settings.enable_optimized_search_endpoints = True
        assert OptimizationConfig.is_search_optimization_enabled() is True
        
        mock_settings.enable_optimized_search_endpoints = False
        assert OptimizationConfig.is_search_optimization_enabled() is False
    
    @patch('backend.app.utils.api_optimization.settings')
    def test_is_performance_monitoring_enabled(self, mock_settings):
        """测试性能监控状态检查"""
        mock_settings.enable_api_performance_monitoring = True
        assert OptimizationConfig.is_performance_monitoring_enabled() is True
        
        mock_settings.enable_api_performance_monitoring = False
        assert OptimizationConfig.is_performance_monitoring_enabled() is False
    
    @patch('backend.app.utils.api_optimization.settings')
    def test_get_performance_threshold(self, mock_settings):
        """测试性能阈值获取"""
        mock_settings.api_performance_report_threshold = 2.5
        assert OptimizationConfig.get_performance_threshold() == 2.5
    
    @patch('backend.app.utils.api_optimization.settings')
    def test_get_optimization_status(self, mock_settings):
        """测试优化状态获取"""
        mock_settings.enable_optimized_sync_endpoints = True
        mock_settings.enable_optimized_search_endpoints = False
        mock_settings.enable_api_performance_monitoring = True
        mock_settings.api_performance_report_threshold = 1.0
        
        status = OptimizationConfig.get_optimization_status()
        
        assert status["sync_optimization_enabled"] is True
        assert status["search_optimization_enabled"] is False
        assert status["performance_monitoring_enabled"] is True
        assert status["performance_threshold"] == 1.0
        assert status["version"] == "3.14.6"


class TestExecuteWithFallback:
    """测试兼容性封装函数"""
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_optimized_async(self):
        """测试使用优化版本的异步函数"""
        # Mock异步优化函数
        optimized_func = AsyncMock(return_value="optimized_result")
        legacy_func = Mock()
        
        # 执行测试
        result = await execute_with_fallback(
            optimized_func, legacy_func, True, "arg1", key="value"
        )
        
        # 验证结果
        assert result == "optimized_result"
        optimized_func.assert_called_once_with("arg1", key="value")
        legacy_func.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_optimized_sync(self):
        """测试使用优化版本的同步函数"""
        # Mock同步优化函数
        optimized_func = Mock(return_value="optimized_result")
        legacy_func = Mock()
        
        # 执行测试
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = "optimized_result"
            result = await execute_with_fallback(
                optimized_func, legacy_func, True, "arg1", key="value"
            )
        
        # 验证结果
        assert result == "optimized_result"
        mock_to_thread.assert_called_once_with(optimized_func, "arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_legacy(self):
        """测试使用传统版本的函数"""
        # Mock函数
        optimized_func = Mock()
        legacy_func = Mock(return_value="legacy_result")
        
        # 执行测试（使用传统版本）
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = "legacy_result"
            result = await execute_with_fallback(
                optimized_func, legacy_func, False, "arg1", key="value"
            )
        
        # 验证结果
        assert result == "legacy_result"
        optimized_func.assert_not_called()
        mock_to_thread.assert_called_once_with(legacy_func, "arg1", key="value")
    
    @pytest.mark.asyncio
    async def test_execute_with_fallback_error_recovery(self):
        """测试优化版本失败时的错误恢复"""
        # Mock失败的优化函数和成功的传统函数
        optimized_func = AsyncMock(side_effect=Exception("optimized failed"))
        legacy_func = Mock(return_value="legacy_result")
        
        # 执行测试
        with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = "legacy_result"
            result = await execute_with_fallback(
                optimized_func, legacy_func, True, "arg1", key="value"
            )
        
        # 验证自动回退到传统方法
        assert result == "legacy_result"
        optimized_func.assert_called_once_with("arg1", key="value")
        mock_to_thread.assert_called_once_with(legacy_func, "arg1", key="value")