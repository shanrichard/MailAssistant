"""
同步性能监控组件（任务3-14-4）

提供邮件同步过程的性能监控和统计功能
"""
import time
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class SyncPerformanceMonitor:
    """同步性能监控器
    
    用于监控邮件同步过程的各个阶段的性能指标，包括：
    - 各阶段耗时统计
    - API调用次数统计
    - 错误记录
    - 性能指标计算
    """
    
    def __init__(self):
        """初始化性能监控器"""
        self.reset()
    
    def reset(self):
        """重置所有监控数据"""
        self.total_start_time: Optional[float] = None
        self.api_calls: int = 0
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.errors: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self._current_stage: Optional[str] = None
        self._current_stage_start: Optional[float] = None
    
    def start_monitoring(self):
        """开始整体监控"""
        self.total_start_time = time.time()
        logger.debug("Performance monitoring started")
    
    def start_stage(self, stage_name: str):
        """开始一个阶段的计时
        
        Args:
            stage_name: 阶段名称，如 'fetch_history', 'batch_fetch', 'db_update'
        """
        current_time = time.time()
        self._current_stage = stage_name
        self._current_stage_start = current_time
        
        logger.debug(f"Started stage: {stage_name}")
    
    def end_stage(self, stage_name: str):
        """结束一个阶段的计时
        
        Args:
            stage_name: 阶段名称，必须与start_stage的名称匹配
            
        Raises:
            ValueError: 如果阶段未开始或名称不匹配
        """
        if self._current_stage != stage_name:
            if self._current_stage is None:
                raise ValueError(f"Stage '{stage_name}' was not started")
            else:
                logger.warning(f"Stage name mismatch: expected '{self._current_stage}', got '{stage_name}'")
        
        if self._current_stage_start is None:
            raise ValueError(f"Stage '{stage_name}' was not started")
        
        end_time = time.time()
        duration = end_time - self._current_stage_start
        
        self.stages[stage_name] = {
            'start_time': self._current_stage_start,
            'end_time': end_time,
            'duration': duration
        }
        
        logger.debug(f"Completed stage: {stage_name}, duration: {duration:.3f}s")
        
        # 清除当前阶段状态
        self._current_stage = None
        self._current_stage_start = None
    
    def record_api_call(self, count: int = 1):
        """记录API调用次数
        
        Args:
            count: API调用次数，默认为1
        """
        self.api_calls += count
        logger.debug(f"Recorded {count} API call(s), total: {self.api_calls}")
    
    def record_api_calls(self, calls: List[Any]):
        """批量记录API调用
        
        Args:
            calls: API调用列表，根据列表长度统计调用次数
        """
        count = len(calls) if calls else 0
        self.record_api_call(count)
    
    def record_error(self, stage: str, error: Exception, details: Optional[Dict[str, Any]] = None):
        """记录错误信息
        
        Args:
            stage: 发生错误的阶段
            error: 错误对象
            details: 额外的错误详情
        """
        error_record = {
            'stage': stage,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        self.errors.append(error_record)
        logger.debug(f"Recorded error in stage '{stage}': {error}")
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据
        
        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
        logger.debug(f"Set metadata: {key} = {value}")
    
    def set_metadata_batch(self, metadata: Dict[str, Any]):
        """批量设置元数据
        
        Args:
            metadata: 元数据字典
        """
        self.metadata.update(metadata)
        logger.debug(f"Set batch metadata: {metadata}")
    
    def get_report(self) -> Dict[str, Any]:
        """生成性能报告
        
        Returns:
            包含完整性能统计的字典
        """
        current_time = time.time()
        
        # 计算总耗时
        total_duration = None
        if self.total_start_time is not None:
            total_duration = current_time - self.total_start_time
        
        # 计算性能指标
        performance_metrics = self._calculate_performance_metrics(total_duration)
        
        # 生成报告
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': total_duration,
            'api_calls': self.api_calls,
            'stages_count': len(self.stages),
            'errors_count': len(self.errors),
            'stages': dict(self.stages),  # 创建副本
            'errors': list(self.errors),  # 创建副本
            'metadata': dict(self.metadata),  # 创建副本
            'performance_metrics': performance_metrics
        }
        
        duration_str = f"{total_duration:.3f}s" if total_duration is not None else "not_started"
        logger.info(f"Generated performance report: {duration_str} total, "
                   f"{self.api_calls} API calls, {len(self.stages)} stages, "
                   f"{len(self.errors)} errors")
        
        return report
    
    def _calculate_performance_metrics(self, total_duration: Optional[float]) -> Dict[str, Any]:
        """计算性能指标
        
        Args:
            total_duration: 总耗时（秒）
            
        Returns:
            性能指标字典
        """
        metrics = {}
        
        if total_duration and total_duration > 0:
            # API调用平均响应时间
            if self.api_calls > 0:
                metrics['avg_api_response_time'] = total_duration / self.api_calls
            else:
                metrics['avg_api_response_time'] = 0
            
            # 每秒API调用次数
            metrics['api_calls_per_second'] = self.api_calls / total_duration
            
            # 每秒处理邮件数（如果有邮件数量元数据）
            message_count = self.metadata.get('message_count') or self.metadata.get('messages_processed')
            if message_count:
                metrics['messages_per_second'] = message_count / total_duration
            
            # 各阶段耗时占比
            if self.stages:
                stage_percentages = {}
                for stage_name, stage_info in self.stages.items():
                    percentage = (stage_info['duration'] / total_duration) * 100
                    stage_percentages[stage_name] = round(percentage, 2)
                metrics['stage_time_percentages'] = stage_percentages
        else:
            metrics['avg_api_response_time'] = 0
            metrics['api_calls_per_second'] = 0
        
        return metrics
    
    def log_summary(self, level: int = logging.INFO):
        """记录性能摘要到日志
        
        Args:
            level: 日志级别
        """
        report = self.get_report()
        
        # 构建摘要信息
        summary_parts = []
        if report['total_duration']:
            summary_parts.append(f"Total: {report['total_duration']:.3f}s")
        
        summary_parts.append(f"API calls: {report['api_calls']}")
        summary_parts.append(f"Stages: {report['stages_count']}")
        
        if report['errors_count'] > 0:
            summary_parts.append(f"Errors: {report['errors_count']}")
        
        # 添加主要阶段信息
        if report['stages']:
            stage_info = []
            for name, info in report['stages'].items():
                stage_info.append(f"{name}:{info['duration']:.3f}s")
            summary_parts.append(f"Stages({', '.join(stage_info)})")
        
        summary = " | ".join(summary_parts)
        logger.log(level, f"Sync Performance Summary: {summary}")
    
    def __str__(self) -> str:
        """字符串表示"""
        if self.total_start_time:
            duration = time.time() - self.total_start_time
            return f"SyncPerformanceMonitor(duration={duration:.3f}s, api_calls={self.api_calls}, stages={len(self.stages)})"
        else:
            return f"SyncPerformanceMonitor(not_started, api_calls={self.api_calls}, stages={len(self.stages)})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return self.__str__()