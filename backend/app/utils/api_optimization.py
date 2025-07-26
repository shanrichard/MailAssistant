"""
API优化工具模块
提供性能监控装饰器、错误处理和配置管理
"""
from functools import wraps
from typing import Dict, Any, Callable
import time
import asyncio
from fastapi import HTTPException

from ..core.config import settings
from ..core.logging import get_logger
from ..utils.sync_performance_monitor import SyncPerformanceMonitor

logger = get_logger(__name__)


def monitor_api_performance(operation_name: str):
    """API性能监控装饰器
    
    Args:
        operation_name: 操作名称，用于标识不同的API端点
        
    Returns:
        装饰器函数
        
    Usage:
        @monitor_api_performance("sync_today")
        async def sync_today_emails(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.enable_api_performance_monitoring:
                return await func(*args, **kwargs)
                
            monitor = SyncPerformanceMonitor()
            monitor.start_monitoring()
            
            try:
                monitor.start_stage(operation_name)
                result = await func(*args, **kwargs)
                monitor.end_stage(operation_name)
                
                # 记录性能报告到日志
                report = monitor.get_report()
                if report['total_duration'] > settings.api_performance_report_threshold:
                    logger.warning(f"API {operation_name} slow performance: {report}")
                else:
                    logger.info(f"API {operation_name} performance: {report['total_duration']:.2f}s")
                
                return result
            except Exception as e:
                monitor.record_error(operation_name, e)
                raise
        return wrapper
    return decorator


class APIErrorHandler:
    """API错误处理器
    
    提供统一的错误处理机制，将不同类型的异常转换为结构化的HTTP响应
    """
    
    @staticmethod
    def handle_sync_error(e: Exception, operation: str) -> HTTPException:
        """处理同步相关错误
        
        Args:
            e: 原始异常
            operation: 操作名称
            
        Returns:
            HTTPException: 结构化的HTTP异常响应
        """
        error_msg = str(e).lower()
        
        if "401" in error_msg or "unauthorized" in error_msg:
            return HTTPException(
                status_code=401,
                detail={
                    "error_code": "AUTHENTICATION_ERROR",
                    "message": "Gmail认证已过期，请重新授权",
                    "operation": operation
                }
            )
        elif "quota" in error_msg or "rate limit" in error_msg:
            return HTTPException(
                status_code=429,
                detail={
                    "error_code": "RATE_LIMIT_ERROR", 
                    "message": "API配额已用完，请稍后重试",
                    "operation": operation
                }
            )
        elif "timeout" in error_msg:
            return HTTPException(
                status_code=408,
                detail={
                    "error_code": "TIMEOUT_ERROR",
                    "message": "请求超时，请稍后重试",
                    "operation": operation
                }
            )
        else:
            return HTTPException(
                status_code=500,
                detail={
                    "error_code": "UNKNOWN_ERROR",
                    "message": f"操作失败: {str(e)}",
                    "operation": operation
                }
            )
    
    @staticmethod
    def handle_search_error(e: Exception, operation: str) -> HTTPException:
        """处理搜索相关错误
        
        Args:
            e: 原始异常
            operation: 操作名称
            
        Returns:
            HTTPException: 结构化的HTTP异常响应
        """
        error_msg = str(e).lower()
        
        if "invalid query" in error_msg or "syntax error" in error_msg:
            return HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_QUERY_ERROR",
                    "message": "搜索查询格式不正确",
                    "operation": operation
                }
            )
        else:
            # 复用同步错误处理逻辑
            return APIErrorHandler.handle_sync_error(e, operation)


class OptimizationConfig:
    """优化配置管理器
    
    提供配置状态检查和验证功能
    """
    
    @staticmethod
    def is_sync_optimization_enabled() -> bool:
        """检查同步优化是否启用"""
        return settings.enable_optimized_sync_endpoints
    
    @staticmethod
    def is_search_optimization_enabled() -> bool:
        """检查搜索优化是否启用"""
        return settings.enable_optimized_search_endpoints
    
    @staticmethod
    def is_performance_monitoring_enabled() -> bool:
        """检查性能监控是否启用"""
        return settings.enable_api_performance_monitoring
    
    @staticmethod
    def get_performance_threshold() -> float:
        """获取性能报告阈值"""
        return settings.api_performance_report_threshold
    
    @staticmethod
    def get_optimization_status() -> Dict[str, Any]:
        """获取优化功能状态"""
        return {
            "sync_optimization_enabled": OptimizationConfig.is_sync_optimization_enabled(),
            "search_optimization_enabled": OptimizationConfig.is_search_optimization_enabled(),
            "performance_monitoring_enabled": OptimizationConfig.is_performance_monitoring_enabled(),
            "performance_threshold": OptimizationConfig.get_performance_threshold(),
            "version": "3.14.6"
        }


# 兼容性封装函数
async def execute_with_fallback(
    optimized_func: Callable,
    legacy_func: Callable,
    use_optimized: bool,
    *args,
    **kwargs
) -> Any:
    """执行优化或传统方法的封装函数
    
    Args:
        optimized_func: 优化版本的函数
        legacy_func: 传统版本的函数
        use_optimized: 是否使用优化版本
        *args: 函数参数
        **kwargs: 函数关键字参数
        
    Returns:
        函数执行结果
    """
    if use_optimized:
        try:
            if asyncio.iscoroutinefunction(optimized_func):
                return await optimized_func(*args, **kwargs)
            else:
                # 同步函数在异步上下文中执行
                return await asyncio.to_thread(optimized_func, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Optimized method failed, falling back to legacy: {e}")
            # 发生错误时自动回退到传统方法
            if asyncio.iscoroutinefunction(legacy_func):
                return await legacy_func(*args, **kwargs)
            else:
                return await asyncio.to_thread(legacy_func, *args, **kwargs)
    else:
        # 直接使用传统方法
        if asyncio.iscoroutinefunction(legacy_func):
            return await legacy_func(*args, **kwargs)
        else:
            return await asyncio.to_thread(legacy_func, *args, **kwargs)