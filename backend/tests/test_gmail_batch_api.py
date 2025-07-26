"""
测试Gmail API批量请求功能（任务3-14-3）
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock, call
from googleapiclient.errors import HttpError
from typing import List, Dict, Any

from app.services.gmail_service import gmail_service
from app.models.user import User


class TestGmailBatchAPI:
    """Gmail批量请求API功能测试"""
    
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
    
    def test_get_messages_batch_success_small_batch(self, mock_user, mock_gmail_service):
        """测试批量获取邮件成功（小批量）"""
        # 准备测试数据 - 5个邮件ID
        message_ids = ['msg1', 'msg2', 'msg3', 'msg4', 'msg5']
        
        # 模拟批量响应
        mock_batch_response = [
            {'id': 'msg1', 'threadId': 'thread1', 'snippet': 'Test message 1'},
            {'id': 'msg2', 'threadId': 'thread2', 'snippet': 'Test message 2'},
            {'id': 'msg3', 'threadId': 'thread3', 'snippet': 'Test message 3'},
            {'id': 'msg4', 'threadId': 'thread4', 'snippet': 'Test message 4'},
            {'id': 'msg5', 'threadId': 'thread5', 'snippet': 'Test message 5'}
        ]
        
        # 配置mock
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.return_value = mock_batch_response
            
            # 执行测试
            result = gmail_service.get_messages_batch(mock_user, message_ids)
            
            # 验证结果
            assert len(result) == 5
            assert result[0]['id'] == 'msg1'
            assert result[4]['id'] == 'msg5'
            
            # 验证批量请求被调用
            mock_batch.assert_called_once_with(mock_user, message_ids)
    
    def test_get_messages_batch_success_large_batch(self, mock_user, mock_gmail_service):
        """测试批量获取邮件成功（大批量，需要分批）"""
        # 准备测试数据 - 100个邮件ID（需要分2批）
        message_ids = [f'msg{i}' for i in range(100)]
        
        # 模拟分批响应
        batch1_response = [{'id': f'msg{i}', 'snippet': f'Message {i}'} for i in range(50)]
        batch2_response = [{'id': f'msg{i}', 'snippet': f'Message {i}'} for i in range(50, 100)]
        
        # 配置mock - 两次批量调用
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.side_effect = [batch1_response, batch2_response]
            
            # 执行测试
            result = gmail_service.get_messages_batch(mock_user, message_ids)
            
            # 验证结果
            assert len(result) == 100
            assert result[0]['id'] == 'msg0'
            assert result[99]['id'] == 'msg99'
            
            # 验证分批调用
            assert mock_batch.call_count == 2
            mock_batch.assert_has_calls([
                call(mock_user, message_ids[:50]),
                call(mock_user, message_ids[50:])
            ])
    
    def test_get_messages_batch_with_retry_429_then_success(self, mock_user, mock_gmail_service):
        """测试429限流重试成功（专家建议）"""
        message_ids = ['msg1', 'msg2', 'msg3']
        
        # 第1次调用返回429错误，第2次成功
        http_error_429 = HttpError(
            resp=Mock(status=429),
            content=b'Rate limit exceeded'
        )
        success_response = [
            {'id': 'msg1', 'snippet': 'Message 1'},
            {'id': 'msg2', 'snippet': 'Message 2'},
            {'id': 'msg3', 'snippet': 'Message 3'}
        ]
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.side_effect = [http_error_429, success_response]
            
            # Mock time.sleep to avoid actual delay in tests
            with patch('time.sleep') as mock_sleep:
                # 执行测试
                result = gmail_service.get_messages_batch_with_retry(mock_user, message_ids)
                
                # 验证结果
                assert len(result) == 3
                assert result[0]['id'] == 'msg1'
                
                # 验证重试机制
                assert mock_batch.call_count == 2  # 1次失败 + 1次成功
                mock_sleep.assert_called_once_with(2)  # 指数退避：2^1
    
    def test_get_messages_batch_retry_twice_then_skip(self, mock_user, mock_gmail_service):
        """测试两次失败后跳过（专家建议）"""
        message_ids = ['msg1', 'msg2']
        
        # 两次都返回5xx错误
        http_error_503 = HttpError(
            resp=Mock(status=503),
            content=b'Service unavailable'
        )
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.side_effect = [http_error_503, http_error_503]
            
            with patch('time.sleep'):
                with patch('app.services.gmail_service.logger') as mock_logger:
                    # 执行测试
                    result = gmail_service.get_messages_batch_with_retry(mock_user, message_ids)
                    
                    # 验证返回空列表而不阻塞
                    assert result == []
                    
                    # 验证重试了2次
                    assert mock_batch.call_count == 2
                    
                    # 验证记录了错误日志
                    mock_logger.error.assert_called()
    
    def test_get_messages_batch_non_retryable_error_propagates(self, mock_user, mock_gmail_service):
        """测试非重试错误正常抛出"""
        message_ids = ['msg1']
        
        # 401错误（认证问题）不应该重试
        http_error_401 = HttpError(
            resp=Mock(status=401),
            content=b'Unauthorized'
        )
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.side_effect = http_error_401
            
            # 执行测试，预期抛出异常
            with pytest.raises(HttpError) as exc_info:
                gmail_service.get_messages_batch_with_retry(mock_user, message_ids)
            
            assert exc_info.value.resp.status == 401
            # 验证没有重试
            assert mock_batch.call_count == 1
    
    @patch('httpx.Client')
    def test_batch_request_timeout_control(self, mock_httpx_client, mock_user, mock_gmail_service):
        """测试网络超时控制（专家建议）"""
        message_ids = ['msg1', 'msg2']
        
        # 模拟超时设置
        mock_client_instance = Mock()
        mock_httpx_client.return_value.__enter__.return_value = mock_client_instance
        
        # 模拟Gmail批量请求成功
        mock_batch_response = [
            {'id': 'msg1', 'snippet': 'Message 1'},
            {'id': 'msg2', 'snippet': 'Message 2'}
        ]
        
        with patch.object(gmail_service, '_execute_gmail_batch_request') as mock_execute:
            mock_execute.return_value = mock_batch_response
            
            # 执行测试
            result = gmail_service._batch_request(mock_user, message_ids)
            
            # 验证超时设置
            mock_httpx_client.assert_called_with(timeout=5.0)
            
            # 验证结果
            assert len(result) == 2
            assert result[0]['id'] == 'msg1'
    
    def test_chunk_list_utility(self):
        """测试列表分块工具方法"""
        # 测试正好整除的情况
        items = list(range(100))
        chunks = list(gmail_service._chunk_list(items, 50))
        assert len(chunks) == 2
        assert len(chunks[0]) == 50
        assert len(chunks[1]) == 50
        
        # 测试不整除的情况
        items = list(range(103))
        chunks = list(gmail_service._chunk_list(items, 50))
        assert len(chunks) == 3
        assert len(chunks[0]) == 50
        assert len(chunks[1]) == 50
        assert len(chunks[2]) == 3
        
        # 测试空列表
        items = []
        chunks = list(gmail_service._chunk_list(items, 50))
        assert len(chunks) == 0
        
        # 测试小于chunk_size的列表
        items = list(range(10))
        chunks = list(gmail_service._chunk_list(items, 50))
        assert len(chunks) == 1
        assert len(chunks[0]) == 10
    
    def test_batch_size_limits(self, mock_user, mock_gmail_service):
        """测试批量大小限制"""
        # 测试正好50个（最大批量大小）
        message_ids = [f'msg{i}' for i in range(50)]
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.return_value = [{'id': f'msg{i}'} for i in range(50)]
            
            result = gmail_service.get_messages_batch(mock_user, message_ids)
            
            # 验证单次调用
            assert mock_batch.call_count == 1
            assert len(result) == 50
    
    @patch('app.services.gmail_service.logger')
    def test_batch_request_logs_appropriately(self, mock_logger, mock_user, mock_gmail_service):
        """测试批量请求的日志记录"""
        message_ids = ['msg1', 'msg2', 'msg3']
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.return_value = [{'id': f'msg{i}'} for i in range(3)]
            
            gmail_service.get_messages_batch(mock_user, message_ids)
            
            # 验证日志记录
            mock_logger.info.assert_called()


class TestGmailBatchAPIIntegration:
    """Gmail批量API集成测试"""
    
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
    
    def test_batch_workflow_with_history_integration(self, mock_user, mock_gmail_service):
        """测试批量请求与History API的集成工作流程"""
        # 1. 先获取变更的邮件ID (来自History API)
        changed_ids = ['msg1', 'msg2', 'msg3', 'msg4', 'msg5']
        
        # 2. 批量获取这些邮件的详情
        mock_batch_response = [
            {'id': f'msg{i}', 'threadId': f'thread{i}', 'snippet': f'Message {i}'} 
            for i in range(1, 6)
        ]
        
        with patch.object(gmail_service, '_batch_request') as mock_batch:
            mock_batch.return_value = mock_batch_response
            
            # 执行批量获取
            result = gmail_service.get_messages_batch(mock_user, changed_ids)
            
            # 验证结果
            assert len(result) == 5
            assert all(msg['id'] in changed_ids for msg in result)
            
            # 验证只调用了一次批量请求（因为<50个）
            mock_batch.assert_called_once_with(mock_user, changed_ids)