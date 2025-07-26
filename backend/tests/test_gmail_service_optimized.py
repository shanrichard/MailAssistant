"""
测试Gmail服务优化版本（任务3-14-5）
"""
import pytest
from unittest.mock import Mock, patch, call
from typing import List, Dict, Any

from app.services.gmail_service import gmail_service
from app.models.user import User


class TestGmailServiceOptimized:
    """Gmail服务优化功能测试"""
    
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
    def sample_message_ids(self):
        """示例邮件ID列表"""
        return ['msg1', 'msg2', 'msg3', 'msg4', 'msg5']
    
    @pytest.fixture
    def sample_messages_list_response(self):
        """模拟list_messages的响应"""
        return [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'},
            {'id': 'msg3', 'threadId': 'thread3'},
            {'id': 'msg4', 'threadId': 'thread4'},
            {'id': 'msg5', 'threadId': 'thread5'}
        ]
    
    @pytest.fixture
    def sample_batch_messages_response(self):
        """模拟get_messages_batch的响应"""
        return [
            {
                'gmail_id': 'msg1',
                'thread_id': 'thread1',
                'subject': 'Test Email 1',
                'sender': 'sender1@example.com',
                'snippet': 'This is test email 1'
            },
            {
                'gmail_id': 'msg2', 
                'thread_id': 'thread2',
                'subject': 'Test Email 2',
                'sender': 'sender2@example.com',
                'snippet': 'This is test email 2'
            },
            {
                'gmail_id': 'msg3',
                'thread_id': 'thread3', 
                'subject': 'Test Email 3',
                'sender': 'sender3@example.com',
                'snippet': 'This is test email 3'
            },
            {
                'gmail_id': 'msg4',
                'thread_id': 'thread4',
                'subject': 'Test Email 4', 
                'sender': 'sender4@example.com',
                'snippet': 'This is test email 4'
            },
            {
                'gmail_id': 'msg5',
                'thread_id': 'thread5',
                'subject': 'Test Email 5',
                'sender': 'sender5@example.com',
                'snippet': 'This is test email 5'
            }
        ]
    
    def test_search_messages_optimized_basic_functionality(
        self, 
        mock_user, 
        sample_messages_list_response,
        sample_batch_messages_response
    ):
        """测试优化版搜索消息的基本功能"""
        query = "newer_than:1d"
        max_results = 50
        
        # Mock list_messages和get_messages_batch方法
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            # 配置mock返回值
            mock_list.return_value = (sample_messages_list_response, None)
            mock_batch.return_value = sample_batch_messages_response
            
            # 执行测试
            result = gmail_service.search_messages_optimized(mock_user, query, max_results)
            
            # 验证结果
            assert len(result) == 5
            assert result[0]['gmail_id'] == 'msg1'
            assert result[0]['subject'] == 'Test Email 1'
            assert result[4]['gmail_id'] == 'msg5'
            
            # 验证方法调用
            mock_list.assert_called_once_with(
                user=mock_user, 
                query=query, 
                max_results=max_results
            )
            mock_batch.assert_called_once_with(
                mock_user, 
                ['msg1', 'msg2', 'msg3', 'msg4', 'msg5']
            )
    
    def test_search_messages_optimized_empty_results(self, mock_user):
        """测试优化版搜索消息的空结果处理"""
        query = "newer_than:1d"
        
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            # 配置mock返回空结果
            mock_list.return_value = ([], None)
            
            # 执行测试
            result = gmail_service.search_messages_optimized(mock_user, query, 50)
            
            # 验证结果
            assert result == []
            
            # 验证调用：空结果时不应该调用get_messages_batch
            mock_list.assert_called_once()
            mock_batch.assert_not_called()
    
    def test_search_messages_optimized_api_call_reduction(
        self, 
        mock_user,
        sample_messages_list_response,
        sample_batch_messages_response
    ):
        """测试API调用次数减少（解决N+1问题的核心测试）"""
        query = "newer_than:1d"
        
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch, \
             patch.object(gmail_service, 'get_message_details') as mock_details:
            
            # 配置mock
            mock_list.return_value = (sample_messages_list_response, None)
            mock_batch.return_value = sample_batch_messages_response
            
            # 执行优化版本
            gmail_service.search_messages_optimized(mock_user, query, 50)
            
            # 验证关键：只调用了1次list_messages + 1次get_messages_batch
            # 没有调用get_message_details（这是N+1问题的根源）
            mock_list.assert_called_once()
            mock_batch.assert_called_once()
            mock_details.assert_not_called()
    
    def test_search_messages_optimized_vs_original_compatibility(
        self,
        mock_user,
        sample_messages_list_response, 
        sample_batch_messages_response
    ):
        """测试优化版本与原版本结果的兼容性"""
        query = "newer_than:1d"
        
        # 为优化版本配置mock
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            mock_list.return_value = (sample_messages_list_response, None)
            mock_batch.return_value = sample_batch_messages_response
            
            # 执行优化版本
            optimized_result = gmail_service.search_messages_optimized(mock_user, query, 50)
        
        # 验证结果格式与原版本兼容
        assert isinstance(optimized_result, list)
        assert len(optimized_result) == 5
        
        # 验证每个消息都有必要的字段
        for message in optimized_result:
            assert 'gmail_id' in message
            assert 'thread_id' in message  
            assert 'subject' in message
            assert 'sender' in message
            assert 'snippet' in message
    
    def test_search_messages_optimized_error_handling(self, mock_user):
        """测试优化版本的错误处理"""
        query = "newer_than:1d"
        
        # 测试list_messages失败的情况
        with patch.object(gmail_service, 'list_messages') as mock_list:
            mock_list.side_effect = Exception("Gmail API error")
            
            with pytest.raises(Exception, match="Gmail API error"):
                gmail_service.search_messages_optimized(mock_user, query, 50)
        
        # 测试get_messages_batch失败的情况  
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            mock_list.return_value = ([{'id': 'msg1'}], None)
            mock_batch.side_effect = Exception("Batch API error")
            
            with pytest.raises(Exception, match="Batch API error"):
                gmail_service.search_messages_optimized(mock_user, query, 50)
    
    def test_search_messages_optimized_large_result_set(self, mock_user):
        """测试优化版本处理大结果集"""
        query = "newer_than:7d"
        
        # 模拟100个邮件ID
        large_message_list = [{'id': f'msg{i}', 'threadId': f'thread{i}'} for i in range(100)]
        large_batch_response = [
            {
                'gmail_id': f'msg{i}',
                'thread_id': f'thread{i}',
                'subject': f'Test Email {i}',
                'sender': f'sender{i}@example.com', 
                'snippet': f'This is test email {i}'
            } for i in range(100)
        ]
        
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            mock_list.return_value = (large_message_list, None)
            mock_batch.return_value = large_batch_response
            
            # 执行测试
            result = gmail_service.search_messages_optimized(mock_user, query, 100)
            
            # 验证结果
            assert len(result) == 100
            assert result[0]['gmail_id'] == 'msg0'
            assert result[99]['gmail_id'] == 'msg99'
            
            # 验证调用
            expected_ids = [f'msg{i}' for i in range(100)]
            mock_batch.assert_called_once_with(mock_user, expected_ids)
    
    def test_search_messages_optimized_pagination_handling(self, mock_user):
        """测试优化版本的分页处理"""
        query = "newer_than:1d"
        
        # 模拟有分页的情况
        page1_messages = [{'id': f'msg{i}', 'threadId': f'thread{i}'} for i in range(3)]
        page1_batch_response = [
            {
                'gmail_id': f'msg{i}',
                'thread_id': f'thread{i}', 
                'subject': f'Test Email {i}',
                'sender': f'sender{i}@example.com',
                'snippet': f'This is test email {i}'
            } for i in range(3)
        ]
        
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            # 模拟返回有next_page_token的情况（但优化版本只处理第一页）
            mock_list.return_value = (page1_messages, "next_page_token_123")
            mock_batch.return_value = page1_batch_response
            
            # 执行测试
            result = gmail_service.search_messages_optimized(mock_user, query, 50)
            
            # 验证只处理了第一页的结果
            assert len(result) == 3
            mock_list.assert_called_once()
            mock_batch.assert_called_once()


class TestGmailServiceOptimizedIntegration:
    """Gmail服务优化版本集成测试"""
    
    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        user = Mock(spec=User)
        user.id = "integration-test-user"
        user.get_decrypted_gmail_tokens.return_value = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token"
        }
        return user
    
    def test_optimized_method_integration_with_existing_apis(self, mock_user):
        """测试优化方法与现有API的集成"""
        # 这个测试验证新的optimized方法可以与现有的批量API正确集成
        
        # 准备测试数据
        message_list = [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'}
        ]
        
        batch_response = [
            {
                'gmail_id': 'msg1',
                'thread_id': 'thread1',
                'subject': 'Integration Test 1',
                'sender': 'test1@example.com',
                'snippet': 'Integration test message 1'
            },
            {
                'gmail_id': 'msg2',
                'thread_id': 'thread2', 
                'subject': 'Integration Test 2',
                'sender': 'test2@example.com',
                'snippet': 'Integration test message 2'
            }
        ]
        
        # 测试与已实现的get_messages_batch集成
        with patch.object(gmail_service, 'list_messages') as mock_list, \
             patch.object(gmail_service, 'get_messages_batch') as mock_batch:
            
            mock_list.return_value = (message_list, None)
            mock_batch.return_value = batch_response
            
            result = gmail_service.search_messages_optimized(
                mock_user, 
                "newer_than:1d", 
                50
            )
            
            # 验证集成正确
            assert len(result) == 2
            assert result[0]['gmail_id'] == 'msg1'
            assert result[1]['gmail_id'] == 'msg2'
            
            # 验证正确使用了已有的批量API
            mock_batch.assert_called_once_with(mock_user, ['msg1', 'msg2'])