"""
测试Gmail History API支持功能（任务3-14-2）
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from googleapiclient.errors import HttpError
from typing import List, Tuple

from app.services.gmail_service import gmail_service
from app.models.user import User


class TestGmailHistoryAPI:
    """Gmail History API功能测试"""
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.get_decrypted_gmail_tokens.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token"
        }
        return user
    
    @pytest.fixture
    def mock_gmail_service(self):
        """模拟Gmail服务"""
        with patch.object(gmail_service, '_get_gmail_service') as mock:
            service = Mock()
            mock.return_value = service
            yield service
    
    def test_fetch_changed_msg_ids_success(self, mock_user, mock_gmail_service):
        """测试成功获取历史变更"""
        # 准备模拟数据
        mock_history_response = {
            'history': [
                {
                    'messagesAdded': [
                        {'message': {'id': 'msg1', 'threadId': 'thread1'}},
                        {'message': {'id': 'msg2', 'threadId': 'thread2'}}
                    ]
                },
                {
                    'labelsAdded': [
                        {'message': {'id': 'msg3', 'threadId': 'thread3'}}
                    ]
                }
            ],
            'historyId': '12345'
        }
        
        # 配置mock - 正确的链式调用
        mock_history_list = Mock()
        mock_history_list.execute.return_value = mock_history_response
        mock_gmail_service.users().history().list.return_value = mock_history_list
        
        # 执行测试
        changed_ids, new_history_id = gmail_service.fetch_changed_msg_ids(
            mock_user, 
            start_history_id='10000'
        )
        
        # 验证结果
        assert len(changed_ids) == 3
        assert 'msg1' in changed_ids
        assert 'msg2' in changed_ids  
        assert 'msg3' in changed_ids
        assert new_history_id == '12345'
        
        # 验证API调用
        mock_gmail_service.users().history().list.assert_called_with(
            userId='me',
            startHistoryId='10000'
        )
    
    def test_fetch_changed_msg_ids_expired_404(self, mock_user, mock_gmail_service):
        """测试historyId过期自动fallback（专家建议）"""
        # 模拟404错误
        http_error = HttpError(
            resp=Mock(status=404),
            content=b'historyId not found'
        )
        mock_history_request = Mock()
        mock_history_request.execute.side_effect = http_error
        mock_gmail_service.users().history().list.return_value = mock_history_request
        
        # 模拟fallback返回
        with patch.object(gmail_service, '_fallback_full_sync') as mock_fallback:
            mock_fallback.return_value = (['msg1', 'msg2'], '99999')
            
            # 执行测试
            changed_ids, new_history_id = gmail_service.fetch_changed_msg_ids(
                mock_user,
                start_history_id='expired_id'
            )
            
            # 验证fallback被调用
            mock_fallback.assert_called_once_with(mock_user)
            assert changed_ids == ['msg1', 'msg2']
            assert new_history_id == '99999'
    
    def test_fetch_changed_msg_ids_other_error_propagates(self, mock_user, mock_gmail_service):
        """测试非404错误正常抛出"""
        # 模拟403错误（权限问题）
        http_error = HttpError(
            resp=Mock(status=403),
            content=b'Forbidden'
        )
        mock_history_request = Mock()
        mock_history_request.execute.side_effect = http_error
        mock_gmail_service.users().history().list.return_value = mock_history_request
        
        # 执行测试，预期抛出异常
        with pytest.raises(HttpError) as exc_info:
            gmail_service.fetch_changed_msg_ids(mock_user, '10000')
        
        assert exc_info.value.resp.status == 403
    
    def test_get_current_history_id_success(self, mock_user, mock_gmail_service):
        """测试获取当前historyId"""
        # 准备模拟数据
        mock_profile = {
            'historyId': '54321',
            'emailAddress': 'test@example.com'
        }
        
        # 配置mock - 正确的链式调用
        mock_profile_request = Mock()
        mock_profile_request.execute.return_value = mock_profile
        mock_gmail_service.users().getProfile.return_value = mock_profile_request
        
        # 执行测试
        history_id = gmail_service.get_current_history_id(mock_user)
        
        # 验证结果
        assert history_id == '54321'
        
        # 验证API调用
        mock_gmail_service.users().getProfile.assert_called_with(userId='me')
    
    def test_extract_message_ids_from_history(self):
        """测试从history响应中提取邮件ID"""
        history_data = [
            {
                'messagesAdded': [
                    {'message': {'id': 'new1'}},
                    {'message': {'id': 'new2'}}
                ]
            },
            {
                'labelsAdded': [
                    {'message': {'id': 'labeled1'}},
                    {'message': {'id': 'labeled2'}}
                ],
                'labelsRemoved': [
                    {'message': {'id': 'unlabeled1'}}
                ]
            },
            {
                'messagesDeleted': [
                    {'message': {'id': 'deleted1'}}
                ]
            }
        ]
        
        # 执行测试
        message_ids = gmail_service._extract_message_ids_from_history(history_data)
        
        # 验证结果 - 应该包含所有变更的邮件ID（去重）
        expected_ids = {'new1', 'new2', 'labeled1', 'labeled2', 'unlabeled1', 'deleted1'}
        assert set(message_ids) == expected_ids
    
    def test_extract_message_ids_empty_history(self):
        """测试空history的处理"""
        # 执行测试
        message_ids = gmail_service._extract_message_ids_from_history([])
        
        # 验证结果
        assert message_ids == []
    
    @patch('app.services.gmail_service.logger')
    def test_fetch_changed_msg_ids_logs_appropriately(self, mock_logger, mock_user, mock_gmail_service):
        """测试日志记录功能"""
        # 准备模拟数据
        mock_history_response = {
            'history': [
                {'messagesAdded': [{'message': {'id': 'msg1'}}]}
            ],
            'historyId': '12345'
        }
        mock_gmail_service.users().history().list().execute.return_value = mock_history_response
        
        # 执行测试
        gmail_service.fetch_changed_msg_ids(mock_user, '10000')
        
        # 验证日志
        mock_logger.info.assert_called()
        mock_logger.warning.assert_not_called()


class TestGmailHistoryAPIIntegration:
    """Gmail History API集成测试"""
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = "test-user-id"
        user.get_decrypted_gmail_tokens.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token"
        }
        return user
    
    @pytest.fixture
    def mock_gmail_service(self):
        """模拟Gmail服务"""
        with patch.object(gmail_service, '_get_gmail_service') as mock:
            service = Mock()
            mock.return_value = service
            yield service
    
    def test_history_api_workflow(self, mock_user, mock_gmail_service):
        """测试完整的History API工作流程"""
        # 1. 获取当前historyId
        mock_profile_request = Mock()
        mock_profile_request.execute.return_value = {'historyId': '20000'}
        mock_gmail_service.users().getProfile.return_value = mock_profile_request
        
        current_id = gmail_service.get_current_history_id(mock_user)
        assert current_id == '20000'
        
        # 2. 获取变更（假设有一些变更）
        mock_history_request = Mock()
        mock_history_request.execute.return_value = {
            'history': [
                {'messagesAdded': [{'message': {'id': 'new_msg'}}]}
            ],
            'historyId': '20001'
        }
        mock_gmail_service.users().history().list.return_value = mock_history_request
        
        changed_ids, new_id = gmail_service.fetch_changed_msg_ids(mock_user, '19999')
        assert 'new_msg' in changed_ids
        assert new_id == '20001'