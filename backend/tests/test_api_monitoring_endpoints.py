"""
API监控端点单元测试
"""
import pytest
import time
from unittest.mock import Mock, patch
from fastapi import HTTPException

from backend.app.api.gmail import (
    optimization_health_check,
    get_performance_stats
)
from backend.app.models.user import User


class TestAPIMonitoringEndpoints:
    """测试API监控端点"""
    
    @pytest.fixture
    def mock_user(self):
        """创建Mock用户"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @pytest.mark.asyncio
    async def test_optimization_health_check(self, mock_config):
        """测试优化功能健康检查端点"""
        # Mock配置状态
        mock_status = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": True,
            "performance_monitoring_enabled": True,
            "performance_threshold": 1.0,
            "version": "3.14.6"
        }
        mock_config.get_optimization_status.return_value = mock_status
        
        # 执行测试
        result = await optimization_health_check()
        
        # 验证返回正确的配置状态
        assert result == mock_status
        assert result["sync_optimization_enabled"] is True
        assert result["search_optimization_enabled"] is True
        assert result["performance_monitoring_enabled"] is True
        assert result["performance_threshold"] == 1.0
        assert result["version"] == "3.14.6"
        
        # 验证响应格式和字段完整性
        expected_fields = [
            "sync_optimization_enabled",
            "search_optimization_enabled", 
            "performance_monitoring_enabled",
            "performance_threshold",
            "version"
        ]
        for field in expected_fields:
            assert field in result
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.core.config.settings')
    @pytest.mark.asyncio
    async def test_performance_stats_endpoint_debug_mode(self, mock_settings, mock_config, mock_user):
        """测试调试模式下的性能统计端点"""
        # Mock debug=True
        mock_settings.debug = True
        
        # Mock配置状态
        mock_config.is_performance_monitoring_enabled.return_value = True
        mock_config.get_performance_threshold.return_value = 2.0
        mock_status = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": False,
            "performance_monitoring_enabled": True,
            "performance_threshold": 2.0,
            "version": "3.14.6"
        }
        mock_config.get_optimization_status.return_value = mock_status
        
        # 执行测试
        result = await get_performance_stats(current_user=mock_user)
        
        # 验证端点可访问并返回正确信息
        assert "message" in result
        assert result["monitoring_enabled"] is True
        assert result["threshold"] == 2.0
        assert result["optimization_status"] == mock_status
        assert "timestamp" in result
        assert isinstance(result["timestamp"], float)
        
        # 验证时间戳合理性（应该接近当前时间）
        current_time = time.time()
        assert abs(result["timestamp"] - current_time) < 1.0  # 误差在1秒内
    
    @patch('backend.app.core.config.settings')
    @pytest.mark.asyncio
    async def test_performance_stats_endpoint_production_mode(self, mock_settings, mock_user):
        """测试生产模式下的性能统计端点"""
        # Mock debug=False
        mock_settings.debug = False
        
        # 执行测试并验证404异常
        with pytest.raises(HTTPException) as exc_info:
            await get_performance_stats(current_user=mock_user)
        
        # 验证端点返回404（安全考虑）
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @pytest.mark.asyncio
    async def test_health_check_with_different_configs(self, mock_config):
        """测试不同配置下的健康检查"""
        # 测试案例：各种配置组合
        test_configs = [
            {
                "sync_optimization_enabled": True,
                "search_optimization_enabled": True,
                "performance_monitoring_enabled": True,
                "performance_threshold": 1.0,
                "version": "3.14.6"
            },
            {
                "sync_optimization_enabled": False,
                "search_optimization_enabled": True,
                "performance_monitoring_enabled": False,
                "performance_threshold": 0.5,
                "version": "3.14.6"
            },
            {
                "sync_optimization_enabled": True,
                "search_optimization_enabled": False,
                "performance_monitoring_enabled": True,
                "performance_threshold": 3.0,
                "version": "3.14.6"
            }
        ]
        
        for config in test_configs:
            mock_config.get_optimization_status.return_value = config
            
            # 执行测试
            result = await optimization_health_check()
            
            # 验证状态报告的准确性
            assert result == config
            assert result["sync_optimization_enabled"] == config["sync_optimization_enabled"]
            assert result["search_optimization_enabled"] == config["search_optimization_enabled"]
            assert result["performance_monitoring_enabled"] == config["performance_monitoring_enabled"]
            assert result["performance_threshold"] == config["performance_threshold"]
            assert result["version"] == config["version"]
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.core.config.settings')
    @pytest.mark.asyncio
    async def test_performance_stats_comprehensive_info(self, mock_settings, mock_config, mock_user):
        """测试性能统计端点的全面信息"""
        # Mock debug模式
        mock_settings.debug = True
        
        # Mock详细配置
        mock_config.is_performance_monitoring_enabled.return_value = True
        mock_config.get_performance_threshold.return_value = 1.5
        mock_detailed_status = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": True,
            "performance_monitoring_enabled": True,
            "performance_threshold": 1.5,
            "version": "3.14.6"
        }
        mock_config.get_optimization_status.return_value = mock_detailed_status
        
        # 执行测试
        result = await get_performance_stats(current_user=mock_user)
        
        # 验证所有字段存在且正确
        required_fields = [
            "message",
            "monitoring_enabled", 
            "threshold",
            "optimization_status",
            "timestamp"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
        
        # 验证具体值
        assert result["message"] == "Performance stats available in logs"
        assert result["monitoring_enabled"] is True
        assert result["threshold"] == 1.5
        assert result["optimization_status"] == mock_detailed_status
        assert isinstance(result["timestamp"], float)
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @pytest.mark.asyncio
    async def test_health_check_api_contract(self, mock_config):
        """测试健康检查API契约"""
        # Mock基础状态
        mock_config.get_optimization_status.return_value = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": False,
            "performance_monitoring_enabled": True,
            "performance_threshold": 1.0,
            "version": "3.14.6"
        }
        
        # 执行测试
        result = await optimization_health_check()
        
        # 验证API契约：返回的数据类型和结构
        assert isinstance(result, dict)
        assert isinstance(result["sync_optimization_enabled"], bool)
        assert isinstance(result["search_optimization_enabled"], bool)
        assert isinstance(result["performance_monitoring_enabled"], bool)
        assert isinstance(result["performance_threshold"], (int, float))
        assert isinstance(result["version"], str)
        
        # 验证版本格式
        assert result["version"].startswith("3.14.")


class TestMonitoringEndpointsIntegration:
    """测试监控端点集成"""
    
    @pytest.fixture
    def mock_user(self):
        """创建Mock用户"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        return user
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @pytest.mark.asyncio
    async def test_health_check_reflects_real_config(self, mock_config):
        """测试健康检查反映真实配置"""
        # Mock真实的配置管理器调用
        mock_config.get_optimization_status.return_value = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": True,
            "performance_monitoring_enabled": True,
            "performance_threshold": 1.0,
            "version": "3.14.6"
        }
        
        # 执行测试
        result = await optimization_health_check()
        
        # 验证调用了配置管理器
        mock_config.get_optimization_status.assert_called_once()
        
        # 验证返回了正确的状态
        assert result["sync_optimization_enabled"] is True
        assert result["search_optimization_enabled"] is True
        assert result["performance_monitoring_enabled"] is True
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.core.config.settings')
    @pytest.mark.asyncio
    async def test_performance_stats_security_check(self, mock_settings, mock_config, mock_user):
        """测试性能统计端点的安全检查"""
        # 测试生产环境安全限制
        mock_settings.debug = False
        
        with pytest.raises(HTTPException) as exc_info:
            await get_performance_stats(current_user=mock_user)
        
        assert exc_info.value.status_code == 404
        
        # 测试开发环境正常访问
        mock_settings.debug = True
        mock_config.is_performance_monitoring_enabled.return_value = True
        mock_config.get_performance_threshold.return_value = 1.0
        mock_config.get_optimization_status.return_value = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": True,
            "performance_monitoring_enabled": True,
            "performance_threshold": 1.0,
            "version": "3.14.6"
        }
        
        result = await get_performance_stats(current_user=mock_user)
        assert "message" in result
        assert "optimization_status" in result
    
    @patch('backend.app.api.gmail.OptimizationConfig')
    @patch('backend.app.core.config.settings')
    @pytest.mark.asyncio
    async def test_monitoring_endpoints_consistency(self, mock_settings, mock_config, mock_user):
        """测试监控端点的一致性"""
        # Mock相同的配置状态
        consistent_status = {
            "sync_optimization_enabled": True,
            "search_optimization_enabled": False,
            "performance_monitoring_enabled": True,
            "performance_threshold": 2.0,
            "version": "3.14.6"
        }
        
        mock_settings.debug = True
        mock_config.get_optimization_status.return_value = consistent_status
        mock_config.is_performance_monitoring_enabled.return_value = True
        mock_config.get_performance_threshold.return_value = 2.0
        
        # 测试健康检查端点
        health_result = await optimization_health_check()
        
        # 测试性能统计端点
        stats_result = await get_performance_stats(current_user=mock_user)
        
        # 验证两个端点返回的配置状态一致
        assert health_result == consistent_status
        assert stats_result["optimization_status"] == consistent_status
        assert stats_result["monitoring_enabled"] == consistent_status["performance_monitoring_enabled"]
        assert stats_result["threshold"] == consistent_status["performance_threshold"]