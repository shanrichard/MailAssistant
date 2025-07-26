"""
测试邮件同步服务批量数据库操作（任务3-14-5）
"""
import pytest
import json
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.services.email_sync_service import email_sync_service
from app.models.user import User
from app.models.email import Email


class TestEmailSyncBatchOperations:
    """邮件同步批量数据库操作测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = Mock(spec=Session)
        return db
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-batch"
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
                'recipients': ['recipient1@example.com'],
                'cc_recipients': [],
                'bcc_recipients': [],
                'body_plain': 'This is test email 1',
                'body_html': '<p>This is test email 1</p>',
                'received_at': datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                'has_attachments': False,
                'labels': ['INBOX', 'UNREAD']
            },
            {
                'gmail_id': 'msg2',
                'thread_id': 'thread2',
                'subject': 'Test Email 2',
                'sender': 'sender2@example.com',
                'recipients': ['recipient2@example.com'],
                'cc_recipients': ['cc@example.com'],
                'bcc_recipients': [],
                'body_plain': 'This is test email 2',
                'body_html': '<p>This is test email 2</p>',
                'received_at': datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
                'has_attachments': True,
                'labels': ['INBOX']
            },
            {
                'gmail_id': 'msg3',
                'thread_id': 'thread3',
                'subject': 'Test Email 3',
                'sender': 'sender3@example.com',
                'recipients': ['recipient3@example.com'],
                'cc_recipients': [],
                'bcc_recipients': ['bcc@example.com'],
                'body_plain': 'This is test email 3',
                'body_html': '<p>This is test email 3</p>',  
                'received_at': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                'has_attachments': False,
                'labels': ['INBOX', 'IMPORTANT']
            }
        ]
    
    def test_sync_messages_batch_all_new_emails(self, mock_db, mock_user, sample_gmail_messages):
        """测试批量同步全部新邮件"""
        # 配置mock：数据库中没有现有邮件
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # 执行测试
        result = email_sync_service._sync_messages_batch(mock_db, mock_user, sample_gmail_messages)
        
        # 验证结果
        assert result['new'] == 3
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # 验证数据库操作
        # 应该查询现有邮件
        mock_db.query.assert_called_once_with(Email)
        mock_query.filter.assert_called_once()
        
        # 应该调用add_all批量添加新邮件
        mock_db.add_all.assert_called_once()
        added_emails = mock_db.add_all.call_args[0][0]
        assert len(added_emails) == 3
        assert all(isinstance(email, Email) for email in added_emails)
        assert added_emails[0].gmail_id == 'msg1'
        assert added_emails[2].gmail_id == 'msg3'
    
    def test_sync_messages_batch_all_existing_emails_no_updates(self, mock_db, mock_user, sample_gmail_messages):
        """测试批量同步全部已存在邮件（无更新）"""
        # 创建现有邮件mock对象
        existing_emails = []
        for i, msg in enumerate(sample_gmail_messages):
            email = Mock(spec=Email)
            email.gmail_id = msg['gmail_id']
            email.is_read = True  # 已读状态
            email.labels = json.dumps(msg['labels'])  # 标签相同
            existing_emails.append(email)
        
        # 配置mock：数据库中有所有邮件
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = existing_emails
        mock_db.query.return_value = mock_query
        
        # Mock _update_email_from_gmail返回False（无更新）
        with patch.object(email_sync_service, '_update_email_from_gmail', return_value=False):
            # 执行测试
            result = email_sync_service._sync_messages_batch(mock_db, mock_user, sample_gmail_messages)
        
        # 验证结果
        assert result['new'] == 0
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # 验证没有调用批量操作
        mock_db.add_all.assert_not_called()
    
    def test_sync_messages_batch_mixed_new_and_updated(self, mock_db, mock_user, sample_gmail_messages):
        """测试批量同步混合场景（新邮件+更新邮件）"""
        # 创建部分现有邮件mock对象（只有msg1和msg3存在）
        existing_emails = []
        for gmail_id in ['msg1', 'msg3']:
            email = Mock(spec=Email)
            email.gmail_id = gmail_id
            email.is_read = False  # 未读状态
            email.labels = json.dumps(['INBOX', 'UNREAD'])
            existing_emails.append(email)
        
        # 配置mock
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = existing_emails
        mock_db.query.return_value = mock_query
        
        # Mock _update_email_from_gmail：msg1需要更新，msg3不需要
        def mock_update_email(email, gmail_message):
            if email.gmail_id == 'msg1':
                return True  # 需要更新
            else:
                return False  # 不需要更新
        
        with patch.object(email_sync_service, '_update_email_from_gmail', side_effect=mock_update_email):
            # 执行测试
            result = email_sync_service._sync_messages_batch(mock_db, mock_user, sample_gmail_messages)
        
        # 验证结果
        assert result['new'] == 1  # msg2是新邮件
        assert result['updated'] == 1  # msg1需要更新
        assert result['errors'] == 0
        
        # 验证批量操作调用
        mock_db.add_all.assert_called_once()  # 添加新邮件msg2
        added_emails = mock_db.add_all.call_args[0][0]
        assert len(added_emails) == 1
        assert added_emails[0].gmail_id == 'msg2'
        
        # 验证更新邮件被添加到会话
        assert mock_db.add.call_count == 1  # msg1被更新
    
    def test_sync_messages_batch_empty_input(self, mock_db, mock_user):
        """测试批量同步空输入"""
        # 执行测试
        result = email_sync_service._sync_messages_batch(mock_db, mock_user, [])
        
        # 验证结果
        assert result['new'] == 0
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # 验证不进行数据库查询
        mock_db.query.assert_not_called()
        mock_db.add_all.assert_not_called()
    
    def test_sync_messages_batch_database_query_optimization(self, mock_db, mock_user, sample_gmail_messages):
        """测试批量数据库查询优化（关键性能测试）"""
        # 配置mock
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # 执行测试
        email_sync_service._sync_messages_batch(mock_db, mock_user, sample_gmail_messages)
        
        # 验证关键优化：只进行1次数据库查询而不是N次
        mock_db.query.assert_called_once_with(Email)
        
        # 验证查询使用了IN操作符批量查询
        filter_call = mock_query.filter.call_args[0][0]
        # 这个断言验证使用了批量查询而不是逐个查询
        assert hasattr(filter_call, 'left')  # SQL表达式有left部分
        assert hasattr(filter_call, 'right')  # SQL表达式有right部分
        
        # 验证只调用一次add_all而不是多次add
        mock_db.add_all.assert_called_once()
    
    def test_sync_messages_batch_creates_email_objects_correctly(self, mock_db, mock_user, sample_gmail_messages):
        """测试批量同步正确创建Email对象"""
        # 配置mock：无现有邮件
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # Mock _create_email_from_gmail来验证调用
        mock_emails = []
        for msg in sample_gmail_messages:
            mock_email = Mock(spec=Email)
            mock_email.gmail_id = msg['gmail_id']
            mock_emails.append(mock_email)
        
        with patch.object(email_sync_service, '_create_email_from_gmail', side_effect=mock_emails):
            # 执行测试
            result = email_sync_service._sync_messages_batch(mock_db, mock_user, sample_gmail_messages)
            
            # 验证每个Gmail消息都调用了_create_email_from_gmail
            assert email_sync_service._create_email_from_gmail.call_count == 3
            
            # 验证调用参数正确
            calls = email_sync_service._create_email_from_gmail.call_args_list
            assert calls[0][0][0] == mock_user  # 第一个参数是用户
            assert calls[0][0][1]['gmail_id'] == 'msg1'  # 第二个参数是Gmail消息
            assert calls[2][0][1]['gmail_id'] == 'msg3'
    
    def test_sync_messages_batch_handles_duplicate_gmail_ids(self, mock_db, mock_user):
        """测试批量同步处理重复的Gmail ID"""
        # 创建包含重复gmail_id的消息列表
        duplicate_messages = [
            {
                'gmail_id': 'msg1',
                'thread_id': 'thread1',
                'subject': 'First Version',
                'sender': 'sender1@example.com',
                'recipients': ['recipient1@example.com'],
                'cc_recipients': [],
                'bcc_recipients': [],
                'body_plain': 'First version',
                'body_html': '<p>First version</p>',
                'received_at': datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                'has_attachments': False,
                'labels': ['INBOX']
            },
            {
                'gmail_id': 'msg1',  # 重复的ID
                'thread_id': 'thread1',
                'subject': 'Second Version',
                'sender': 'sender1@example.com',
                'recipients': ['recipient1@example.com'],
                'cc_recipients': [],
                'bcc_recipients': [],
                'body_plain': 'Second version',
                'body_html': '<p>Second version</p>',
                'received_at': datetime(2024, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
                'has_attachments': False,
                'labels': ['INBOX', 'IMPORTANT']
            }
        ]
        
        # 配置mock：无现有邮件
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # 执行测试
        result = email_sync_service._sync_messages_batch(mock_db, mock_user, duplicate_messages)
        
        # 验证结果：应该只处理1个邮件（去重）
        assert result['new'] == 1
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # 验证只添加了一个邮件对象
        mock_db.add_all.assert_called_once()
        added_emails = mock_db.add_all.call_args[0][0]
        assert len(added_emails) == 1
    
    def test_sync_messages_batch_performance_characteristics(self, mock_db, mock_user):
        """测试批量同步的性能特征"""
        # 创建大量消息数据（100个）
        large_message_set = []
        for i in range(100):
            large_message_set.append({
                'gmail_id': f'msg{i}',
                'thread_id': f'thread{i}',
                'subject': f'Test Email {i}',
                'sender': f'sender{i}@example.com',
                'recipients': [f'recipient{i}@example.com'],
                'cc_recipients': [],
                'bcc_recipients': [],
                'body_plain': f'This is test email {i}',
                'body_html': f'<p>This is test email {i}</p>',
                'received_at': datetime(2024, 1, 1, 10, i % 60, 0, tzinfo=timezone.utc),
                'has_attachments': False,
                'labels': ['INBOX']
            })
        
        # 配置mock：无现有邮件
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        mock_db.query.return_value = mock_query
        
        # 执行测试
        result = email_sync_service._sync_messages_batch(mock_db, mock_user, large_message_set)
        
        # 验证结果
        assert result['new'] == 100
        assert result['updated'] == 0
        assert result['errors'] == 0
        
        # 验证性能特征：无论多少邮件，都只进行1次数据库查询和1次批量插入
        assert mock_db.query.call_count == 1
        assert mock_db.add_all.call_count == 1
        
        # 验证批量插入的邮件数量正确
        added_emails = mock_db.add_all.call_args[0][0]
        assert len(added_emails) == 100