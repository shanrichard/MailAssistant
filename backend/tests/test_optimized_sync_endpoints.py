"""
优化同步端点单元测试
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.api.gmail import (
    sync_today_emails_optimized,
    sync_week_emails_optimized,
    sync_month_emails_optimized
)
from backend.app.models.user import User


class TestOptimizedSyncEndpoints:
    """测试优化的同步端点"""
    
    @pytest.fixture
    def mock_user(self):
        """创建Mock用户"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user
    
    @pytest.fixture
    def mock_db(self):
        """创建Mock数据库会话"""
        return Mock()
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @patch('backend.app.api.gmail.email_sync_service')
    @pytest.mark.asyncio
    async def test_sync_today_optimized_enabled(self, mock_sync_service, mock_execute, mock_config, mock_user, mock_db):
        """测试优化启用时的/sync/today端点"""
        # Mock配置启用优化
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock智能同步返回有结果（不需要补充查询）
        mock_execute.return_value = {'new': 5, 'updated': 2, 'errors': 0}
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证调用了优化方法
        assert mock_execute.call_count == 1  # 只有智能同步
        mock_config.is_sync_optimization_enabled.assert_called_once()
        
        # 验证响应格式保持兼容
        assert result["success"] is True
        assert "成功同步了" in result["message"]
        assert "stats" in result
        assert result["stats"]["new"] == 5
        assert result["stats"]["updated"] == 2
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.asyncio.to_thread')
    @patch('backend.app.api.gmail.email_sync_service')
    @pytest.mark.asyncio
    async def test_sync_today_optimized_disabled(self, mock_sync_service, mock_to_thread, mock_config, mock_user, mock_db):
        """测试优化禁用时的/sync/today端点"""
        # Mock配置禁用优化
        mock_config.is_sync_optimization_enabled.return_value = False
        
        # Mock原版方法返回结果
        mock_to_thread.return_value = {'new': 3, 'updated': 1, 'errors': 0}
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证调用了原版sync_emails_by_timerange方法
        mock_to_thread.assert_called_once_with(
            mock_sync_service.sync_emails_by_timerange,
            mock_db, mock_user, "today", 500
        )
        
        # 验证向后兼容性
        assert result["success"] is True
        assert result["stats"]["new"] == 3
        assert result["stats"]["updated"] == 1
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_sync_today_with_fallback_query(self, mock_execute, mock_config, mock_user, mock_db):
        """测试智能同步无结果时的查询回退"""
        # Mock配置启用优化
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock智能同步返回空结果，补充查询返回结果
        mock_execute.side_effect = [
            {'new': 0, 'updated': 0, 'errors': 0},  # 智能同步无结果
            {'new': 3, 'updated': 1, 'errors': 0}   # 补充查询有结果
        ]
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证自动调用查询方式补充
        assert mock_execute.call_count == 2
        
        # 验证结果正确合并
        assert result["stats"]["new"] == 3
        assert result["stats"]["updated"] == 1
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_sync_week_optimized(self, mock_execute, mock_config, mock_user, mock_db):
        """测试优化的/sync/week端点"""
        # Mock配置启用优化
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_execute.return_value = {'new': 10, 'updated': 5, 'errors': 0}
        
        # 执行测试
        result = await sync_week_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证使用了week查询（newer_than:7d）
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        # 验证lambda函数会调用正确的参数
        assert call_args[0][2] is True  # use_optimized=True
        
        # 验证响应格式
        assert result["success"] is True
        assert result["stats"]["new"] == 10
        assert result["stats"]["updated"] == 5
    
    @patch('backend.app.api.gmail.OptimizationConfig')  
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_sync_month_optimized(self, mock_execute, mock_config, mock_user, mock_db):
        """测试优化的/sync/month端点"""
        # Mock配置启用优化
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock优化方法返回结果
        mock_execute.return_value = {'new': 20, 'updated': 10, 'errors': 0}
        
        # 执行测试
        result = await sync_month_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证使用了month查询（newer_than:30d）
        mock_execute.assert_called_once()
        
        # 验证响应格式
        assert result["success"] is True
        assert result["stats"]["new"] == 20
        assert result["stats"]["updated"] == 10
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @patch('backend.app.api.gmail.APIErrorHandler')
    @pytest.mark.asyncio
    async def test_sync_endpoints_error_handling(self, mock_error_handler, mock_execute, mock_config, mock_user, mock_db):
        """测试同步端点的错误处理"""
        # Mock配置启用优化
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock execute_with_fallback抛出异常
        test_error = Exception("Gmail API error")
        mock_execute.side_effect = test_error
        
        # Mock错误处理器
        mock_http_error = HTTPException(status_code=500, detail="Handled error")
        mock_error_handler.handle_sync_error.return_value = mock_http_error
        
        # 执行测试并验证异常
        with pytest.raises(HTTPException):
            await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证错误处理器被正确调用
        mock_error_handler.handle_sync_error.assert_called_once_with(test_error, "sync_today")
    
    @patch('backend.app.utils.api_optimization.SyncPerformanceMonitor')
    @patch('backend.app.utils.api_optimization.settings')
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_sync_endpoints_performance_monitoring(self, mock_execute, mock_config, mock_settings, mock_monitor_class, mock_user, mock_db):
        """测试同步端点的性能监控"""
        # Mock设置启用性能监控
        mock_settings.enable_api_performance_monitoring = True
        mock_settings.api_performance_report_threshold = 1.0
        
        # Mock性能监控器
        mock_monitor = Mock()
        mock_monitor.get_report.return_value = {'total_duration': 0.5}
        mock_monitor_class.return_value = mock_monitor
        
        # Mock配置和执行
        mock_config.is_sync_optimization_enabled.return_value = True
        mock_execute.return_value = {'new': 3, 'updated': 1, 'errors': 0}
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证性能监控装饰器被应用
        mock_monitor.start_monitoring.assert_called_once()
        mock_monitor.start_stage.assert_called_once_with("sync_today")
        mock_monitor.end_stage.assert_called_once_with("sync_today")
        mock_monitor.get_report.assert_called_once()
        
        # 验证函数正常返回
        assert result["success"] is True


class TestSyncEndpointIntegration:
    """测试同步端点集成"""
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.execute_with_fallback')
    @pytest.mark.asyncio
    async def test_smart_sync_integration(self, mock_execute, mock_config):
        """测试智能同步集成"""
        # Mock配置
        mock_config.is_sync_optimization_enabled.return_value = True
        
        # Mock智能同步成功
        mock_execute.return_value = {'new': 5, 'updated': 2, 'errors': 0}
        
        # Mock用户和数据库
        mock_user = Mock(spec=User)
        mock_db = Mock()
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证集成正确
        assert result["success"] is True
        assert mock_execute.called
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.api.gmail.asyncio.to_thread')
    @pytest.mark.asyncio  
    async def test_legacy_fallback_integration(self, mock_to_thread, mock_config):
        """测试传统方法回退集成"""
        # Mock配置禁用优化
        mock_config.is_sync_optimization_enabled.return_value = False
        
        # Mock传统方法
        mock_to_thread.return_value = {'new': 3, 'updated': 1, 'errors': 0}
        
        # Mock用户和数据库
        mock_user = Mock(spec=User)
        mock_db = Mock()
        
        # 执行测试
        result = await sync_today_emails_optimized(current_user=mock_user, db=mock_db)
        
        # 验证回退到传统方法
        assert result["success"] is True
        mock_to_thread.assert_called()
        assert "sync_emails_by_timerange" in str(mock_to_thread.call_args)