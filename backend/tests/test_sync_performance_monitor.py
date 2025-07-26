"""
测试同步性能监控组件（任务3-14-4）
"""
import pytest
import time
from unittest.mock import Mock, patch
from typing import Dict, Any

from app.utils.sync_performance_monitor import SyncPerformanceMonitor


class TestSyncPerformanceMonitor:
    """同步性能监控器测试"""
    
    @pytest.fixture
    def monitor(self):
        """创建性能监控器实例"""
        return SyncPerformanceMonitor()
    
    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor.total_start_time is None
        assert monitor.api_calls == 0
        assert monitor.stages == {}
        assert monitor.errors == []
        assert monitor.metadata == {}
    
    def test_start_monitoring(self, monitor):
        """测试开始监控"""
        with patch('time.time', return_value=1000.0):
            monitor.start_monitoring()
            
        assert monitor.total_start_time == 1000.0
        assert monitor.api_calls == 0
        assert monitor.stages == {}
    
    def test_stage_timing_basic(self, monitor):
        """测试基础阶段计时功能"""
        with patch('time.time', side_effect=[1000.0, 1002.5]):
            monitor.start_stage('fetch_history')
            monitor.end_stage('fetch_history')
            
        assert 'fetch_history' in monitor.stages
        stage_info = monitor.stages['fetch_history']
        assert stage_info['duration'] == 2.5
        assert stage_info['start_time'] == 1000.0
        assert stage_info['end_time'] == 1002.5
    
    def test_stage_timing_multiple_stages(self, monitor):
        """测试多个阶段的计时"""
        with patch('time.time', side_effect=[1000.0, 1002.0, 1002.5, 1005.0]):
            # 第一个阶段
            monitor.start_stage('fetch_history')
            monitor.end_stage('fetch_history')
            
            # 第二个阶段
            monitor.start_stage('batch_fetch')
            monitor.end_stage('batch_fetch')
            
        assert len(monitor.stages) == 2
        assert monitor.stages['fetch_history']['duration'] == 2.0
        assert monitor.stages['batch_fetch']['duration'] == 2.5
    
    def test_stage_timing_nested_not_supported(self, monitor):
        """测试嵌套阶段处理（不支持，后开始的会覆盖）"""
        with patch('time.time', side_effect=[1000.0, 1001.0, 1002.0]):
            monitor.start_stage('outer')
            monitor.start_stage('inner')  # 这会覆盖outer的开始时间
            monitor.end_stage('inner')
            
            # outer阶段现在无法结束，因为当前阶段已经是None
            with pytest.raises(ValueError, match="Stage 'outer' was not started"):
                monitor.end_stage('outer')
            
        # 应该只有inner阶段被正确记录
        assert 'inner' in monitor.stages
        assert monitor.stages['inner']['duration'] == 1.0
        
        # outer阶段不应该存在
        assert 'outer' not in monitor.stages
    
    def test_end_stage_without_start_raises_error(self, monitor):
        """测试结束未开始的阶段会抛出错误"""
        with pytest.raises(ValueError, match="Stage 'nonexistent' was not started"):
            monitor.end_stage('nonexistent')
    
    def test_api_call_counting(self, monitor):
        """测试API调用计数"""
        assert monitor.api_calls == 0
        
        monitor.record_api_call()
        assert monitor.api_calls == 1
        
        monitor.record_api_call(count=5)
        assert monitor.api_calls == 6
        
        # 测试批量记录
        monitor.record_api_calls(['call1', 'call2', 'call3'])
        assert monitor.api_calls == 9
    
    def test_error_recording(self, monitor):
        """测试错误记录功能"""
        error1 = Exception("Test error 1")
        error2 = ValueError("Test error 2")
        
        monitor.record_error('fetch_stage', error1)
        monitor.record_error('process_stage', error2, details={'user_id': '123'})
        
        assert len(monitor.errors) == 2
        
        error_record1 = monitor.errors[0]
        assert error_record1['stage'] == 'fetch_stage'
        assert error_record1['error_type'] == 'Exception'
        assert error_record1['error_message'] == 'Test error 1'
        assert 'timestamp' in error_record1
        
        error_record2 = monitor.errors[1]
        assert error_record2['stage'] == 'process_stage'
        assert error_record2['error_type'] == 'ValueError'
        assert error_record2['details'] == {'user_id': '123'}
    
    def test_metadata_management(self, monitor):
        """测试元数据管理"""
        monitor.set_metadata('user_id', 'test-user-123')
        monitor.set_metadata('sync_type', 'incremental')
        monitor.set_metadata('message_count', 50)
        
        assert monitor.metadata['user_id'] == 'test-user-123'
        assert monitor.metadata['sync_type'] == 'incremental'
        assert monitor.metadata['message_count'] == 50
        
        # 测试批量设置
        monitor.set_metadata_batch({
            'start_history_id': '12345',
            'end_history_id': '12350'
        })
        
        assert monitor.metadata['start_history_id'] == '12345'
        assert monitor.metadata['end_history_id'] == '12350'
    
    def test_performance_report_generation(self, monitor):
        """测试性能报告生成"""
        # 设置测试数据 - 足够的时间值（包括get_report()中的调用）
        time_values = [1000.0, 1002.0, 1003.0, 1008.0, 1010.0, 1012.0]
        with patch('time.time', side_effect=time_values):
            monitor.start_monitoring()
            
            monitor.start_stage('fetch_changes')
            monitor.end_stage('fetch_changes')
            
            monitor.start_stage('batch_fetch')
            monitor.end_stage('batch_fetch')
            
            monitor.record_api_call(count=3)
            monitor.set_metadata('user_id', 'test-user')
            monitor.set_metadata('message_count', 25)
            
            # 生成报告
            report = monitor.get_report()
        
        # 验证报告结构
        assert report['total_duration'] == 12.0  # 1012.0 - 1000.0
        assert report['api_calls'] == 3
        assert report['stages_count'] == 2
        assert report['errors_count'] == 0
        
        # 验证阶段信息
        stages = report['stages']
        assert len(stages) == 2
        assert stages['fetch_changes']['duration'] == 1.0  # 1003.0 - 1002.0
        assert stages['batch_fetch']['duration'] == 2.0    # 1010.0 - 1008.0
        
        # 验证元数据
        assert report['metadata']['user_id'] == 'test-user'
        assert report['metadata']['message_count'] == 25
        
        # 验证性能指标
        metrics = report['performance_metrics']
        assert metrics['avg_api_response_time'] == 12.0 / 3  # total_time / api_calls
        assert metrics['messages_per_second'] == 25 / 12.0  # message_count / total_time
    
    def test_performance_report_with_errors(self, monitor):
        """测试包含错误的性能报告"""
        with patch('time.time', side_effect=[1000.0, 1005.0]):
            monitor.start_monitoring()
            
        monitor.record_error('test_stage', Exception("Test error"))
        monitor.record_api_call(count=2)
        
        with patch('time.time', return_value=1010.0):
            report = monitor.get_report()
        
        assert report['errors_count'] == 1
        assert len(report['errors']) == 1
        assert report['errors'][0]['error_message'] == 'Test error'
    
    def test_performance_report_not_started(self, monitor):
        """测试未开始监控时生成报告"""
        with patch('time.time', return_value=1000.0):
            report = monitor.get_report()
        
        assert report['total_duration'] is None
        assert report['api_calls'] == 0
        assert report['stages_count'] == 0
        assert report['errors_count'] == 0
    
    def test_performance_metrics_calculation(self, monitor):
        """测试性能指标计算"""
        with patch('time.time', side_effect=[1000.0, 1020.0]):
            monitor.start_monitoring()
            
            monitor.record_api_call(count=5)
            monitor.set_metadata('message_count', 100)
            
            report = monitor.get_report()
        
        metrics = report['performance_metrics']
        assert metrics['avg_api_response_time'] == 20.0 / 5  # 4.0 seconds per API call
        assert metrics['messages_per_second'] == 100 / 20.0  # 5.0 messages per second
        assert metrics['api_calls_per_second'] == 5 / 20.0  # 0.25 calls per second
    
    def test_stage_timing_precision(self, monitor):
        """测试阶段计时精度"""
        # 测试毫秒级精度
        with patch('time.time', side_effect=[1000.123456, 1000.987654]):
            monitor.start_stage('precise_timing')
            monitor.end_stage('precise_timing')
        
        duration = monitor.stages['precise_timing']['duration']
        # 验证精度保持（差值应该是0.864198）
        assert abs(duration - 0.864198) < 0.000001
    
    def test_concurrent_stage_handling(self, monitor):
        """测试并发阶段处理（当前实现不支持真正并发）"""
        # 当前实现是简单的单阶段跟踪，测试行为
        with patch('time.time', side_effect=[1000.0, 1001.0, 1002.0]):
            monitor.start_stage('stage1')
            monitor.start_stage('stage2')  # 这会重置当前阶段
            monitor.end_stage('stage2')
            
        # stage1不应该有正确的记录，因为被stage2覆盖了
        assert 'stage2' in monitor.stages
        assert monitor.stages['stage2']['duration'] == 1.0
    
    def test_reset_functionality(self, monitor):
        """测试重置功能"""
        # 设置一些数据
        with patch('time.time', side_effect=[1000.0, 1001.0, 1002.0]):
            monitor.start_monitoring()
            monitor.start_stage('test')
            monitor.end_stage('test')
            
            monitor.record_api_call(count=3)
            monitor.set_metadata('test', 'value')
            monitor.record_error('test', Exception('test'))
            
            # 重置
            monitor.reset()
        
        # 验证所有数据被清除
        assert monitor.total_start_time is None
        assert monitor.api_calls == 0
        assert monitor.stages == {}
        assert monitor.errors == []
        assert monitor.metadata == {}


class TestSyncPerformanceMonitorIntegration:
    """性能监控器集成测试"""
    
    def test_typical_sync_workflow_monitoring(self):
        """测试典型同步工作流程的监控"""
        monitor = SyncPerformanceMonitor()
        
        # 模拟完整的同步流程
        with patch('time.time', side_effect=[
            1000.0,  # start_monitoring
            1001.0,  # start fetch_history
            1003.0,  # end fetch_history
            1003.0,  # start batch_fetch
            1008.0,  # end batch_fetch
            1008.0,  # start db_update
            1010.0,  # end db_update
            1012.0,  # get_report
        ]):
            # 开始监控
            monitor.start_monitoring()
            monitor.set_metadata_batch({
                'user_id': 'test-user-123',
                'sync_type': 'incremental',
                'start_history_id': '10000'
            })
            
            # 第一阶段：获取历史变更
            monitor.start_stage('fetch_history')
            monitor.record_api_call()  # History API调用
            monitor.end_stage('fetch_history')
            
            # 第二阶段：批量获取邮件详情
            monitor.start_stage('batch_fetch')
            monitor.record_api_call(count=2)  # 2次批量调用
            monitor.set_metadata('messages_fetched', 75)
            monitor.end_stage('batch_fetch')
            
            # 第三阶段：数据库更新
            monitor.start_stage('db_update')
            monitor.set_metadata('messages_processed', 75)
            monitor.end_stage('db_update')
            
            # 生成最终报告
            report = monitor.get_report()
        
        # 验证报告
        assert report['total_duration'] == 12.0
        assert report['api_calls'] == 3
        assert report['stages_count'] == 3
        assert report['errors_count'] == 0
        
        # 验证各阶段耗时
        assert report['stages']['fetch_history']['duration'] == 2.0
        assert report['stages']['batch_fetch']['duration'] == 5.0
        assert report['stages']['db_update']['duration'] == 2.0
        
        # 验证性能指标
        metrics = report['performance_metrics']
        assert metrics['messages_per_second'] == 75 / 12.0
        assert metrics['api_calls_per_second'] == 3 / 12.0
        
        # 验证元数据
        metadata = report['metadata']
        assert metadata['user_id'] == 'test-user-123'
        assert metadata['sync_type'] == 'incremental'
        assert metadata['messages_processed'] == 75
    
    def test_error_handling_in_workflow(self):
        """测试工作流程中的错误处理"""
        monitor = SyncPerformanceMonitor()
        
        with patch('time.time', side_effect=[1000.0, 1001.0, 1002.0, 1003.0, 1005.0, 1006.0]):
            monitor.start_monitoring()
            
            # 模拟第一阶段成功
            monitor.start_stage('fetch_history')
            monitor.record_api_call()
            monitor.end_stage('fetch_history')
            
            # 模拟第二阶段出错
            monitor.start_stage('batch_fetch')
            monitor.record_error('batch_fetch', 
                                Exception("Rate limit exceeded"), 
                                details={'retry_count': 2})
            monitor.end_stage('batch_fetch')
            
            report = monitor.get_report()
        
        assert report['errors_count'] == 1
        assert report['errors'][0]['stage'] == 'batch_fetch'
        assert report['errors'][0]['error_message'] == 'Rate limit exceeded'
        assert report['errors'][0]['details']['retry_count'] == 2