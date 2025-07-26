"""
测试邮件同步服务集成性能监控（任务3-14-5）
"""
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.email_sync_service import email_sync_service
from app.models.user import User
from app.utils.sync_performance_monitor import SyncPerformanceMonitor


class TestEmailSyncWithMonitoring:
    """邮件同步服务集成性能监控测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-monitoring"
        return user
    
    @pytest.fixture
    def sample_gmail_messages(self):
        """示例Gmail消息数据"""
        return [
            {
                'gmail_id': 'msg1',
                'thread_id': 'thread1',
                'subject': 'Test Email 1',
                'sender': 'sender1@example.com',
                'snippet': 'Test email 1 content'
            },
            {
                'gmail_id': 'msg2',
                'thread_id': 'thread2',
                'subject': 'Test Email 2',
                'sender': 'sender2@example.com',
                'snippet': 'Test email 2 content'
            }
        ]
    
    def test_sync_emails_by_query_with_monitoring_basic_functionality(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试带性能监控的邮件同步基本功能"""
        query = "newer_than:1d"
        max_results = 100
        
        # Mock所有依赖的方法
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock返回值
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            # 配置性能监控器mock
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {
                'total_duration': 2.5,
                'api_calls': 2,
                'stages': {'fetch_messages': {'duration': 1.0}, 'sync_to_db': {'duration': 1.5}},
                'errors': []
            }
            
            # 执行测试
            result = email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, max_results
            )
            
            # 验证结果
            assert result['new'] == 2
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证性能监控器的使用
            mock_monitor_class.assert_called_once()
            mock_monitor.start_monitoring.assert_called_once()
            
            # 验证阶段监控
            expected_stage_calls = [
                call('fetch_messages'),
                call('sync_to_db'),
                call('commit_transaction')
            ]
            mock_monitor.start_stage.assert_has_calls(expected_stage_calls)
            
            expected_end_calls = [
                call('fetch_messages'),
                call('sync_to_db'),
                call('commit_transaction')
            ]
            mock_monitor.end_stage.assert_has_calls(expected_end_calls)
            
            # 验证API调用记录
            mock_monitor.record_api_call.assert_called_once_with(count=2)
            
            # 验证元数据设置
            mock_monitor.set_metadata.assert_has_calls([
                call('user_id', str(mock_user.id)),
                call('query', query),
                call('message_count', 2)
            ], any_order=True)
            
            # 验证报告生成
            mock_monitor.get_report.assert_called_once()
    
    def test_sync_emails_by_query_with_monitoring_stages_timing(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试性能监控的阶段计时功能"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 3.0, 'api_calls': 2}
            
            # 执行测试
            email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, 100
            )
            
            # 验证阶段监控的正确顺序
            start_calls = mock_monitor.start_stage.call_args_list
            end_calls = mock_monitor.end_stage.call_args_list
            
            # 验证阶段名称和顺序
            assert len(start_calls) == 3
            assert start_calls[0][0][0] == 'fetch_messages'
            assert start_calls[1][0][0] == 'sync_to_db'
            assert start_calls[2][0][0] == 'commit_transaction'
            
            assert len(end_calls) == 3
            assert end_calls[0][0][0] == 'fetch_messages'
            assert end_calls[1][0][0] == 'sync_to_db'
            assert end_calls[2][0][0] == 'commit_transaction'
    
    def test_sync_emails_by_query_with_monitoring_error_handling(self, mock_db, mock_user):
        """测试带监控的同步错误处理"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 模拟Gmail服务抛出异常
            test_error = Exception("Gmail API error")
            mock_search.side_effect = test_error
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            
            # 执行测试，预期抛出异常
            with pytest.raises(Exception, match="Gmail API error"):
                email_sync_service.sync_emails_by_query_with_monitoring(
                    mock_db, mock_user, query, 100
                )
            
            # 验证错误被记录到监控器
            mock_monitor.record_error.assert_called_once_with('sync_process', test_error)
            
            # 验证数据库回滚
            mock_db.rollback.assert_called_once()
    
    def test_sync_emails_by_query_with_monitoring_performance_logging(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试性能监控的日志记录"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class, \
             patch('app.services.email_sync_service.logger') as mock_logger:
            
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {
                'total_duration': 1.75,
                'api_calls': 2,
                'stages': {'fetch_messages': {'duration': 0.5}, 'sync_to_db': {'duration': 1.0}},
                'errors': []
            }
            
            # 执行测试
            email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, 100
            )
            
            # 验证性能日志被正确记录
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "Sync performance: 1.75s" in log_message
            assert "2 API calls" in log_message
            assert "2 messages" in log_message
    
    def test_sync_emails_by_query_with_monitoring_metadata_collection(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试性能监控的元数据收集"""
        query = "important AND newer_than:7d"
        max_results = 50
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 1, 'updated': 1, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 2.0, 'api_calls': 2}
            
            # 执行测试
            email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, max_results
            )
            
            # 验证元数据设置
            metadata_calls = mock_monitor.set_metadata.call_args_list
            metadata_dict = {call[0][0]: call[0][1] for call in metadata_calls}
            
            assert metadata_dict['user_id'] == str(mock_user.id)
            assert metadata_dict['query'] == query
            assert metadata_dict['message_count'] == 2  # len(sample_gmail_messages)
    
    def test_sync_emails_by_query_with_monitoring_integration_with_optimized_methods(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试性能监控与优化方法的集成"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 1.5, 'api_calls': 2}
            
            # 执行测试
            result = email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, 100
            )
            
            # 验证使用了优化的方法
            mock_search.assert_called_once_with(mock_user, query, 100)
            mock_batch_sync.assert_called_once_with(mock_db, mock_user, sample_gmail_messages)
            
            # 验证结果正确
            assert result['new'] == 2
            assert result['updated'] == 0
            assert result['errors'] == 0
    
    def test_sync_emails_by_query_with_monitoring_empty_results(self, mock_db, mock_user):
        """测试监控下的空结果处理"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 模拟空结果
            mock_search.return_value = []
            mock_batch_sync.return_value = {'new': 0, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 0.5, 'api_calls': 1}
            
            # 执行测试
            result = email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, 100
            )
            
            # 验证结果
            assert result['new'] == 0
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证空结果的元数据记录
            metadata_calls = mock_monitor.set_metadata.call_args_list
            metadata_dict = {call[0][0]: call[0][1] for call in metadata_calls}
            assert metadata_dict['message_count'] == 0
            
            # 验证API调用计数为0（空结果）
            mock_monitor.record_api_call.assert_called_once_with(count=0)
    
    def test_sync_emails_by_query_with_monitoring_transaction_handling(
        self, 
        mock_db, 
        mock_user, 
        sample_gmail_messages
    ):
        """测试监控下事务处理的完整性"""
        query = "newer_than:1d"
        
        with patch('app.services.gmail_service.gmail_service.search_messages_optimized') as mock_search, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_batch_sync, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            mock_search.return_value = sample_gmail_messages
            mock_batch_sync.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock(spec=SyncPerformanceMonitor)
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 2.0, 'api_calls': 2}
            
            # 执行测试
            email_sync_service.sync_emails_by_query_with_monitoring(
                mock_db, mock_user, query, 100
            )
            
            # 验证事务操作被正确监控
            stage_calls = [call[0][0] for call in mock_monitor.start_stage.call_args_list]
            assert 'commit_transaction' in stage_calls
            
            end_calls = [call[0][0] for call in mock_monitor.end_stage.call_args_list]
            assert 'commit_transaction' in end_calls
            
            # 验证数据库提交被调用
            mock_db.commit.assert_called_once()