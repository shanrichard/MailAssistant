"""
优化搜索端点单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from backend.app.api.gmail import (
    search_emails_optimized,
    get_recent_emails_optimized,
    get_unread_emails_optimized,
    get_messages_by_sender_optimized,
    SearchRequest
)
from backend.app.models.user import User


class TestOptimizedSearchEndpoints:
    """测试优化的搜索端点"""
    
    @pytest.fixture
    def mock_user(self):
        """创建Mock用户"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_search_request(self):
        """创建Mock搜索请求"""
        request = Mock(spec=SearchRequest)
        request.query = "test query"
        request.max_results = 50
        return request
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_search_emails_optimized_enabled(self, mock_execute, mock_config, mock_user, mock_search_request):
        """测试优化启用时的/search端点"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_messages = [{"id": "1", "subject": "Test Email"}]
        mock_execute.return_value = mock_messages
        
        # 执行测试
        result = await search_emails_optimized(request=mock_search_request, current_user=mock_user)
        
        # 验证使用了优化版本的搜索方法
        mock_execute.assert_called_once()
        mock_config.is_search_optimization_enabled.assert_called_once()
        
        # 验证响应格式保持一致
        assert result == mock_messages
        assert len(result) == 1
        assert result[0]["subject"] == "Test Email"
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.asyncio.to_thread')
    @patch('backend.app.api.gmail.gmail_service')
    @pytest.mark.asyncio
    async def test_search_emails_optimized_disabled(self, mock_gmail_service, mock_to_thread, mock_config, mock_user, mock_search_request):
        """测试优化禁用时的/search端点"""
        # Mock配置禁用优化
        mock_config.is_search_optimization_enabled.return_value = False
        
        # Mock原版方法返回结果
        mock_messages = [{"id": "2", "subject": "Legacy Search"}]
        mock_to_thread.return_value = mock_messages
        
        # 执行测试
        result = await search_emails_optimized(request=mock_search_request, current_user=mock_user)
        
        # 验证使用了原版search_messages方法
        mock_to_thread.assert_called_once_with(
            mock_gmail_service.search_messages,
            mock_user,
            query=mock_search_request.query,
            max_results=mock_search_request.max_results
        )
        
        # 验证向后兼容性
        assert result == mock_messages
        assert len(result) == 1
        assert result[0]["subject"] == "Legacy Search"
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_recent_emails_optimized(self, mock_execute, mock_config, mock_user):
        """测试优化的/recent端点"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_messages = [
            {"id": "1", "subject": "Recent Email 1"},
            {"id": "2", "subject": "Recent Email 2"}
        ]
        mock_execute.return_value = mock_messages
        
        # 执行测试
        result = await get_recent_emails_optimized(days=3, max_results=20, current_user=mock_user)
        
        # 验证使用了优化版本
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args[0][2] is True  # use_optimized=True
        
        # 验证响应格式
        assert result == mock_messages
        assert len(result) == 2
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_unread_emails_optimized(self, mock_execute, mock_config, mock_user):
        """测试优化的/unread端点"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_messages = [
            {"id": "1", "subject": "Unread Email 1", "is_unread": True},
            {"id": "2", "subject": "Unread Email 2", "is_unread": True}
        ]
        mock_execute.return_value = mock_messages
        
        # 执行测试
        result = await get_unread_emails_optimized(max_results=50, current_user=mock_user)
        
        # 验证使用了优化版本
        mock_execute.assert_called_once()
        
        # 验证响应格式
        assert result == mock_messages
        assert len(result) == 2
        assert all(msg["is_unread"] for msg in result)
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_sender_emails_optimized(self, mock_execute, mock_config, mock_user):
        """测试优化的/sender/{email}端点"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_messages = [
            {"id": "1", "subject": "From Sender 1", "from": "sender@example.com"},
            {"id": "2", "subject": "From Sender 2", "from": "sender@example.com"}
        ]
        mock_execute.return_value = mock_messages
        
        # 执行测试
        result = await get_messages_by_sender_optimized(
            sender_email="sender@example.com",
            max_results=20,
            current_user=mock_user
        )
        
        # 验证使用了优化版本
        mock_execute.assert_called_once()
        
        # 验证响应格式
        assert result == mock_messages
        assert len(result) == 2
        assert all(msg["from"] == "sender@example.com" for msg in result)
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @patch('backend.app.api.gmail.APIErrorHandler')
    @pytest.mark.asyncio
    async def test_search_endpoints_error_handling(self, mock_error_handler, mock_execute, mock_config, mock_user, mock_search_request):
        """测试搜索端点的错误处理"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock execute_with_fallback抛出异常
        test_error = Exception("Gmail search error")
        mock_execute.side_effect = test_error
        
        # Mock错误处理器
        mock_http_error = HTTPException(status_code=500, detail="Handled error")
        mock_error_handler.handle_search_error.return_value = mock_http_error
        
        # 执行测试并验证异常
        with pytest.raises(HTTPException):
            await search_emails_optimized(request=mock_search_request, current_user=mock_user)
        
        # 验证错误处理器被正确调用
        mock_error_handler.handle_search_error.assert_called_once_with(test_error, "search_emails")
    
    @patch('backend.app.utils.api_optimization.SyncPerformanceMonitor')
    @patch('backend.app.utils.api_optimization.settings')
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_search_endpoints_performance_monitoring(self, mock_execute, mock_config, mock_settings, mock_monitor_class, mock_user, mock_search_request):
        """测试搜索端点的性能监控"""
        # Mock设置启用性能监控
        mock_settings.enable_api_performance_monitoring = True
        mock_settings.api_performance_report_threshold = 1.0
        
        # Mock性能监控器
        mock_monitor = Mock()
        mock_monitor.get_report.return_value = {'total_duration': 0.3}
        mock_monitor_class.return_value = mock_monitor
        
        # Mock配置和执行
        mock_config.is_search_optimization_enabled.return_value = True
        mock_execute.return_value = [{"id": "1", "subject": "Test"}]
        
        # 执行测试
        result = await search_emails_optimized(request=mock_search_request, current_user=mock_user)
        
        # 验证性能监控装饰器被应用
        mock_monitor.start_monitoring.assert_called_once()
        mock_monitor.start_stage.assert_called_once_with("search_emails")
        mock_monitor.end_stage.assert_called_once_with("search_emails")
        mock_monitor.get_report.assert_called_once()
        
        # 验证函数正常返回
        assert len(result) == 1


class TestSearchEndpointIntegration:
    """测试搜索端点集成"""
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_search_optimization_integration(self, mock_execute, mock_config):
        """测试搜索优化集成"""
        # Mock配置
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock搜索结果
        mock_execute.return_value = [{"id": "1", "subject": "Integration Test"}]
        
        # Mock用户和请求
        mock_user = Mock(spec=User)
        mock_request = Mock(spec=SearchRequest)
        mock_request.query = "integration test"
        mock_request.max_results = 10
        
        # 执行测试
        result = await search_emails_optimized(request=mock_request, current_user=mock_user)
        
        # 验证集成正确
        assert len(result) == 1
        assert result[0]["subject"] == "Integration Test"
        mock_execute.assert_called_once()
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_fallback_error_recovery(self, mock_execute, mock_config):
        """测试错误恢复的回退机制"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock优化版本失败，但回退成功
        mock_execute.return_value = [{"id": "1", "subject": "Recovered Result"}]
        
        # Mock用户
        mock_user = Mock(spec=User)
        
        # 执行测试
        result = await get_recent_emails_optimized(days=1, max_results=10, current_user=mock_user)
        
        # 验证回退机制工作
        assert len(result) == 1
        assert result[0]["subject"] == "Recovered Result"
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.asyncio.to_thread')
    @pytest.mark.asyncio
    async def test_legacy_mode_compatibility(self, mock_to_thread, mock_config):
        """测试传统模式兼容性"""
        # Mock配置禁用优化
        mock_config.is_search_optimization_enabled.return_value = False
        
        # Mock传统方法
        mock_to_thread.return_value = [{"id": "1", "subject": "Legacy Mode"}]
        
        # Mock用户
        mock_user = Mock(spec=User)
        
        # 执行测试
        result = await get_unread_emails_optimized(max_results=20, current_user=mock_user)
        
        # 验证使用传统方法
        assert len(result) == 1
        assert result[0]["subject"] == "Legacy Mode"
        mock_to_thread.assert_called()


class TestPerformanceOptimizationFeatures:
    """测试性能优化功能特性"""
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_n_plus_one_problem_resolution(self, mock_execute, mock_config):
        """测试N+1问题解决"""
        # Mock配置启用优化
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock批量API调用结果（解决N+1问题）
        mock_execute.return_value = [
            {"id": f"{i}", "subject": f"Batch Email {i}"}
            for i in range(10)
        ]
        
        # Mock用户和请求
        mock_user = Mock(spec=User)
        mock_request = Mock(spec=SearchRequest)
        mock_request.query = "batch test"
        mock_request.max_results = 10
        
        # 执行测试
        result = await search_emails_optimized(request=mock_request, current_user=mock_user)
        
        # 验证批量查询效果
        assert len(result) == 10
        mock_execute.assert_called_once()  # 只调用一次批量方法，而不是N+1次
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_different_search_endpoints_consistency(self, mock_execute, mock_config):
        """测试不同搜索端点的一致性"""
        # Mock配置
        mock_config.is_search_optimization_enabled.return_value = True
        
        # Mock用户
        mock_user = Mock(spec=User)
        
        # 测试不同端点都使用了优化
        test_cases = [
            (get_recent_emails_optimized, {"days": 1, "max_results": 10}),
            (get_unread_emails_optimized, {"max_results": 20}),
            (get_messages_by_sender_optimized, {"sender_email": "test@example.com", "max_results": 15})
        ]
        
        for endpoint_func, kwargs in test_cases:
            mock_execute.reset_mock()
            mock_execute.return_value = [{"id": "1", "subject": "Test"}]
            
            # 执行测试
            result = await endpoint_func(current_user=mock_user, **kwargs)
            
            # 验证都使用了优化
            assert len(result) == 1
            mock_execute.assert_called_once()