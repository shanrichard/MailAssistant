"""
测试 search_email_history 函数的分页功能
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from sqlalchemy import func

from app.agents.conversation_tools import create_conversation_tools
from app.models.email import Email


class TestSearchEmailHistoryPagination:
    """测试邮件搜索分页功能"""
    
    @pytest.fixture
    def mock_db_session(self):
        """创建模拟的数据库会话"""
        session = Mock()
        return session
    
    @pytest.fixture
    def mock_user_context(self):
        """创建模拟的用户上下文"""
        return {"user_id": "test_user_123"}
    
    @pytest.fixture
    def conversation_tools(self, mock_db_session, mock_user_context):
        """创建对话工具集"""
        return create_conversation_tools("test_user_123", mock_db_session, mock_user_context)
    
    def create_mock_email(self, id, subject, sender, received_at, is_read=False, body="Test body"):
        """创建模拟邮件对象"""
        email = Mock(spec=Email)
        email.id = id
        email.subject = subject
        email.sender = sender
        email.recipients = "test@example.com"
        email.cc_recipients = None
        email.received_at = received_at
        email.is_read = is_read
        email.is_important = False
        email.has_attachments = False
        email.body_plain = body
        return email
    
    def test_fixed_limit_50(self, conversation_tools, mock_db_session):
        """测试固定limit为50，即使传入其他值也应该返回50条"""
        # 创建60个模拟邮件
        mock_emails = []
        base_time = datetime.now()
        for i in range(60):
            email = self.create_mock_email(
                id=f"email_{i}",
                subject=f"Test Email {i}",
                sender=f"sender{i}@test.com",
                received_at=base_time - timedelta(hours=i)
            )
            mock_emails.append(email)
        
        # 模拟查询结果（包含total_count）
        mock_results = []
        for email in mock_emails[:50]:  # 只返回前50个
            result = Mock()
            result.Email = email
            result.total_count = 60
            mock_results.append(result)
        
        # 设置mock返回值
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        # 调用函数（尝试传入limit=100）
        search_tool = None
        for tool in conversation_tools:
            if tool.name == "search_email_history":
                search_tool = tool
                break
        
        result = search_tool.func(limit=100)  # 尝试请求100条
        result_dict = json.loads(result)
        
        # 验证结果
        assert result_dict["status"] == "success"
        assert result_dict["results_count"] == 50  # 应该返回50条
        assert result_dict["total_count"] == 60
        assert result_dict["has_more"] == True
        assert result_dict["next_offset"] == 50
        
    def test_offset_pagination(self, conversation_tools, mock_db_session):
        """测试offset分页功能正常工作"""
        # 创建150个模拟邮件
        mock_emails = []
        base_time = datetime.now()
        for i in range(150):
            email = self.create_mock_email(
                id=f"email_{i}",
                subject=f"Test Email {i}",
                sender=f"sender{i}@test.com",
                received_at=base_time - timedelta(hours=i)
            )
            mock_emails.append(email)
        
        # 测试第一页 (offset=0)
        mock_results_page1 = []
        for email in mock_emails[:50]:
            result = Mock()
            result.Email = email
            result.total_count = 150
            mock_results_page1.append(result)
        
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_results_page1
        
        search_tool = None
        for tool in conversation_tools:
            if tool.name == "search_email_history":
                search_tool = tool
                break
        
        # 第一页
        result = search_tool.func(offset=0)
        result_dict = json.loads(result)
        assert result_dict["results_count"] == 50
        assert result_dict["total_count"] == 150
        assert result_dict["has_more"] == True
        assert result_dict["next_offset"] == 50
        
        # 测试第二页 (offset=50)
        mock_results_page2 = []
        for email in mock_emails[50:100]:
            result = Mock()
            result.Email = email
            result.total_count = 150
            mock_results_page2.append(result)
        
        mock_query.all.return_value = mock_results_page2
        
        result = search_tool.func(offset=50)
        result_dict = json.loads(result)
        assert result_dict["results_count"] == 50
        assert result_dict["total_count"] == 150
        assert result_dict["has_more"] == True
        assert result_dict["next_offset"] == 100
        
        # 测试最后一页 (offset=100)
        mock_results_page3 = []
        for email in mock_emails[100:150]:
            result = Mock()
            result.Email = email
            result.total_count = 150
            mock_results_page3.append(result)
        
        mock_query.all.return_value = mock_results_page3
        
        result = search_tool.func(offset=100)
        result_dict = json.loads(result)
        assert result_dict["results_count"] == 50
        assert result_dict["total_count"] == 150
        assert result_dict["has_more"] == False
        assert result_dict["next_offset"] is None
        
    def test_large_result_no_error(self, conversation_tools, mock_db_session):
        """测试大数据量（>80KB）不会返回错误"""
        # 创建包含大量内容的邮件
        mock_emails = []
        base_time = datetime.now()
        large_body = "A" * 2000  # 2KB的内容
        
        for i in range(50):
            email = self.create_mock_email(
                id=f"email_{i}",
                subject=f"Test Email with Large Content {i}",
                sender=f"sender{i}@test.com",
                received_at=base_time - timedelta(hours=i),
                body=large_body
            )
            mock_emails.append(email)
        
        mock_results = []
        for email in mock_emails:
            result = Mock()
            result.Email = email
            result.total_count = 50
            mock_results.append(result)
        
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        search_tool = None
        for tool in conversation_tools:
            if tool.name == "search_email_history":
                search_tool = tool
                break
        
        # 执行搜索
        result = search_tool.func()
        result_dict = json.loads(result)
        
        # 验证：应该正常返回结果，而不是错误
        assert result_dict["status"] == "success"
        assert result_dict["results_count"] == 50
        assert "error" not in result_dict
        assert "message" not in result_dict or "数据量过大" not in result_dict.get("message", "")
        
    def test_backward_compatibility(self, conversation_tools, mock_db_session):
        """测试向后兼容性：传入limit参数时函数正常运行"""
        # 创建30个模拟邮件
        mock_emails = []
        base_time = datetime.now()
        for i in range(30):
            email = self.create_mock_email(
                id=f"email_{i}",
                subject=f"Test Email {i}",
                sender=f"sender{i}@test.com",
                received_at=base_time - timedelta(hours=i)
            )
            mock_emails.append(email)
        
        mock_results = []
        for email in mock_emails:
            result = Mock()
            result.Email = email
            result.total_count = 30
            mock_results.append(result)
        
        mock_query = Mock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_results
        
        search_tool = None
        for tool in conversation_tools:
            if tool.name == "search_email_history":
                search_tool = tool
                break
        
        # 传入各种limit值，函数应该正常运行
        for limit_value in [10, 20, 50, 100, 200]:
            result = search_tool.func(limit=limit_value)
            result_dict = json.loads(result)
            assert result_dict["status"] == "success"
            assert "error" not in result_dict