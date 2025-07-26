"""
测试邮件同步服务History API增量同步（任务3-14-5）
"""
import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.email_sync_service import email_sync_service
from app.models.user import User


class TestEmailSyncHistoryAPI:
    """邮件同步服务History API增量同步测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user_with_history(self):
        """模拟有historyId的用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-history"
        user.last_history_id = "12345"
        user.last_history_sync = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        return user
    
    @pytest.fixture
    def mock_user_without_history(self):
        """模拟没有historyId的用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-no-history"
        user.last_history_id = None
        user.last_history_sync = None
        return user
    
    @pytest.fixture
    def sample_changed_messages(self):
        """示例变更的邮件数据"""
        return [
            {
                'gmail_id': 'changed_msg1',
                'thread_id': 'thread1',
                'subject': 'Changed Email 1',
                'sender': 'sender1@example.com',
                'snippet': 'This email was changed'
            },
            {
                'gmail_id': 'changed_msg2',
                'thread_id': 'thread2',
                'subject': 'Changed Email 2',
                'sender': 'sender2@example.com',
                'snippet': 'This email was also changed'
            }
        ]
    
    def test_smart_sync_user_emails_optimized_with_history_api_success(
        self, 
        mock_db, 
        mock_user_with_history, 
        sample_changed_messages
    ):
        """测试使用History API的智能同步成功场景"""
        new_history_id = "12350"
        
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch('app.services.gmail_service.gmail_service.get_messages_batch') as mock_batch, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_sync_batch, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock返回值
            mock_fetch.return_value = (['changed_msg1', 'changed_msg2'], new_history_id)
            mock_batch.return_value = sample_changed_messages
            mock_sync_batch.return_value = {'new': 1, 'updated': 1, 'errors': 0}
            
            # 配置性能监控器mock
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 1.0, 'api_calls': 2}
            
            # 执行测试
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=False
            )
            
            # 验证结果
            assert result['new'] == 1
            assert result['updated'] == 1
            assert result['errors'] == 0
            
            # 验证History API被正确调用
            mock_fetch.assert_called_once_with(mock_user_with_history, "12345")
            mock_batch.assert_called_once_with(mock_user_with_history, ['changed_msg1', 'changed_msg2'])
            
            # 验证historyId被更新
            assert mock_user_with_history.last_history_id == new_history_id
            assert mock_user_with_history.last_history_sync is not None
            
            # 验证用户对象被保存
            mock_db.add.assert_called_with(mock_user_with_history)
            mock_db.commit.assert_called()
    
    def test_smart_sync_user_emails_optimized_with_history_api_no_changes(
        self, 
        mock_db, 
        mock_user_with_history
    ):
        """测试History API返回无变更的场景"""
        new_history_id = "12350"
        
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock：无变更
            mock_fetch.return_value = ([], new_history_id)
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 0.5, 'api_calls': 1}
            
            # 执行测试
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=False
            )
            
            # 验证结果
            assert result['new'] == 0
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证historyId仍然被更新
            assert mock_user_with_history.last_history_id == new_history_id
    
    def test_smart_sync_user_emails_optimized_history_api_fallback(
        self, 
        mock_db, 
        mock_user_with_history
    ):
        """测试History API失败时的回退机制"""
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch.object(email_sync_service, 'sync_emails_by_query_with_monitoring') as mock_fallback_sync, \
             patch.object(email_sync_service, 'is_first_sync', return_value=False), \
             patch.object(email_sync_service, '_get_latest_email_timestamp') as mock_latest_time, \
             patch('app.services.gmail_service.gmail_service.get_current_history_id') as mock_current_id, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock：History API失败
            mock_fetch.side_effect = Exception("History API failed")
            mock_latest_time.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_fallback_sync.return_value = {'new': 1, 'updated': 0, 'errors': 0}
            mock_current_id.return_value = "12400"
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 2.0, 'api_calls': 3}
            
            # 执行测试
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=False
            )
            
            # 验证结果
            assert result['new'] == 1
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证回退到时间基础同步
            mock_fallback_sync.assert_called_once()
            
            # 验证新的historyId被获取和设置
            mock_current_id.assert_called_once_with(mock_user_with_history)
            assert mock_user_with_history.last_history_id == "12400"
    
    def test_smart_sync_user_emails_optimized_without_history_id(
        self, 
        mock_db, 
        mock_user_without_history
    ):
        """测试没有historyId的用户同步"""
        with patch.object(email_sync_service, 'is_first_sync', return_value=True) as mock_is_first, \
             patch.object(email_sync_service, '_full_sync_with_optimization') as mock_full_sync, \
             patch('app.services.gmail_service.gmail_service.get_current_history_id') as mock_current_id, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock
            mock_full_sync.return_value = {'new': 50, 'updated': 0, 'errors': 0}
            mock_current_id.return_value = "13000"
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 10.0, 'api_calls': 10}
            
            # 执行测试
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_without_history, force_full=False
            )
            
            # 验证结果
            assert result['new'] == 50
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证调用了全量同步
            mock_full_sync.assert_called_once()
            
            # 验证historyId被设置
            assert mock_user_without_history.last_history_id == "13000"
    
    def test_smart_sync_user_emails_optimized_force_full_sync(
        self, 
        mock_db, 
        mock_user_with_history
    ):
        """测试强制全量同步"""
        with patch.object(email_sync_service, '_full_sync_with_optimization') as mock_full_sync, \
             patch('app.services.gmail_service.gmail_service.get_current_history_id') as mock_current_id, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock
            mock_full_sync.return_value = {'new': 100, 'updated': 20, 'errors': 0}
            mock_current_id.return_value = "14000"
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 15.0, 'api_calls': 20}
            
            # 执行测试（强制全量同步）
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=True
            )
            
            # 验证结果
            assert result['new'] == 100
            assert result['updated'] == 20
            assert result['errors'] == 0
            
            # 验证调用了全量同步，即使用户有historyId
            mock_full_sync.assert_called_once()
    
    def test_smart_sync_user_emails_optimized_incremental_with_timestamp(
        self, 
        mock_db, 
        mock_user_without_history
    ):
        """测试基于时间戳的增量同步"""
        # 设置用户有一些历史邮件（不是首次同步）
        with patch.object(email_sync_service, 'is_first_sync', return_value=False), \
             patch.object(email_sync_service, '_get_latest_email_timestamp') as mock_latest_time, \
             patch.object(email_sync_service, 'sync_emails_by_query_with_monitoring') as mock_query_sync, \
             patch('app.services.gmail_service.gmail_service.get_current_history_id') as mock_current_id, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock
            latest_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_latest_time.return_value = latest_timestamp
            mock_query_sync.return_value = {'new': 5, 'updated': 2, 'errors': 0}
            mock_current_id.return_value = "13500"
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 3.0, 'api_calls': 3}
            
            # 执行测试
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_without_history, force_full=False
            )
            
            # 验证结果
            assert result['new'] == 5
            assert result['updated'] == 2
            assert result['errors'] == 0
            
            # 验证使用了时间基础的查询
            mock_query_sync.assert_called_once()
            call_args = mock_query_sync.call_args[0]
            query = call_args[2]  # 第三个参数是query
            assert "after:" in query
            
            # 验证historyId被设置
            assert mock_user_without_history.last_history_id == "13500"
    
    def test_smart_sync_user_emails_optimized_performance_monitoring_integration(
        self, 
        mock_db, 
        mock_user_with_history, 
        sample_changed_messages
    ):
        """测试智能同步与性能监控的集成"""
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch('app.services.gmail_service.gmail_service.get_messages_batch') as mock_batch, \
             patch.object(email_sync_service, '_sync_messages_batch') as mock_sync_batch, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 配置mock
            mock_fetch.return_value = (['changed_msg1', 'changed_msg2'], "12350")
            mock_batch.return_value = sample_changed_messages
            mock_sync_batch.return_value = {'new': 2, 'updated': 0, 'errors': 0}
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {
                'total_duration': 1.2,
                'api_calls': 2,
                'stages': {'history_sync': {'duration': 1.2}},
                'errors': []
            }
            
            # 执行测试
            email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=False
            )
            
            # 验证性能监控器被正确使用
            mock_monitor_class.assert_called_once()
            mock_monitor.start_monitoring.assert_called_once()
            
            # 验证阶段监控
            mock_monitor.start_stage.assert_called_with('history_sync')
            mock_monitor.end_stage.assert_called_with('history_sync')
            
            # 验证报告生成
            mock_monitor.get_report.assert_called_once()
    
    def test_smart_sync_user_emails_optimized_error_handling(
        self, 
        mock_db, 
        mock_user_with_history
    ):
        """测试智能同步的错误处理"""
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch.object(email_sync_service, 'sync_emails_by_query_with_monitoring') as mock_fallback, \
             patch.object(email_sync_service, 'is_first_sync', return_value=False), \
             patch.object(email_sync_service, '_get_latest_email_timestamp'), \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class:
            
            # 模拟所有步骤都失败的严重错误
            test_error = Exception("Database connection error")
            mock_fetch.side_effect = test_error  # History API失败
            mock_fallback.side_effect = test_error  # 回退同步也失败
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            
            # 执行测试，预期抛出异常
            with pytest.raises(Exception, match="Database connection error"):
                email_sync_service.smart_sync_user_emails_optimized(
                    mock_db, mock_user_with_history, force_full=False
                )
            
            # 验证错误被记录到监控器
            mock_monitor.record_error.assert_called_with('smart_sync', test_error)
    
    def test_smart_sync_user_emails_optimized_history_id_update_failure_handling(
        self, 
        mock_db, 
        mock_user_with_history, 
        sample_changed_messages
    ):
        """测试historyId更新失败的处理（通过时间基础同步）"""
        with patch('app.services.gmail_service.gmail_service.fetch_changed_msg_ids') as mock_fetch, \
             patch.object(email_sync_service, 'sync_emails_by_query_with_monitoring') as mock_query_sync, \
             patch.object(email_sync_service, 'is_first_sync', return_value=False), \
             patch.object(email_sync_service, '_get_latest_email_timestamp') as mock_latest_time, \
             patch('app.services.gmail_service.gmail_service.get_current_history_id') as mock_current_id, \
             patch('app.utils.sync_performance_monitor.SyncPerformanceMonitor') as mock_monitor_class, \
             patch('app.services.email_sync_service.logger') as mock_logger:
            
            # 配置mock：History API失败，回退到时间基础同步，然后historyId更新失败
            mock_fetch.side_effect = Exception("History API failed")
            mock_latest_time.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_query_sync.return_value = {'new': 1, 'updated': 0, 'errors': 0}
            mock_current_id.side_effect = Exception("Failed to get current history ID")
            
            mock_monitor = Mock()
            mock_monitor_class.return_value = mock_monitor
            mock_monitor.get_report.return_value = {'total_duration': 1.0}
            
            # 执行测试（不应该抛出异常）
            result = email_sync_service.smart_sync_user_emails_optimized(
                mock_db, mock_user_with_history, force_full=False
            )
            
            # 验证主要同步仍然成功
            assert result['new'] == 1
            assert result['updated'] == 0
            assert result['errors'] == 0
            
            # 验证警告日志被记录（两次：History API失败 + historyId更新失败）
            assert mock_logger.warning.call_count >= 1