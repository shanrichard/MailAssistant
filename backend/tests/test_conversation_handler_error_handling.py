"""
测试 ConversationHandler 中的工具错误处理功能
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from langchain.tools import Tool
from app.agents.conversation_handler import ConversationHandler


class TestConversationHandlerErrorHandling:
    """测试工具错误处理功能"""
    
    def create_test_handler(self):
        """创建测试用的 ConversationHandler"""
        db_session = Mock()
        user = Mock()
        
        # 模拟环境变量
        with patch('app.core.config.settings') as mock_settings:
            mock_settings.agents.conversation_handler_default_model = "gpt-3.5-turbo"
            mock_settings.agents.conversation_handler_temperature = 0.7
            mock_settings.llm.default_provider = "openai"
            
            # 模拟 LLM
            with patch.object(ConversationHandler, 'llm', Mock()):
                handler = ConversationHandler("test_user", db_session, user)
                return handler
    
    def test_wrap_tool_with_error_handling_sync(self):
        """测试同步工具的错误处理包装"""
        handler = self.create_test_handler()
        
        # 创建一个会抛出异常的模拟工具
        def failing_tool(*args, **kwargs):
            raise ValueError("Test error")
        
        mock_tool = Tool(
            name="test_tool",
            description="Test tool",
            func=failing_tool
        )
        
        # 包装工具
        wrapped_tool = handler._wrap_tool_with_error_handling(mock_tool)
        
        # 执行工具并验证错误响应格式
        result = wrapped_tool.func()
        
        assert result["success"] is False
        assert result["error"] == "Test error"
        assert result["error_type"] == "ValueError"
        assert result["tool"] == "test_tool"
        assert "输入参数有误" in result["message"]
    
    @pytest.mark.asyncio
    async def test_wrap_tool_with_error_handling_async(self):
        """测试异步工具的错误处理包装"""
        handler = self.create_test_handler()
        
        # 创建一个会抛出异常的异步工具
        async def failing_async_tool(*args, **kwargs):
            raise ConnectionError("Network error")
        
        mock_tool = Tool(
            name="async_test",
            description="Async test tool",
            func=lambda: None,
            afunc=failing_async_tool
        )
        
        # 包装工具
        wrapped_tool = handler._wrap_tool_with_error_handling(mock_tool)
        
        # 执行工具并验证错误响应格式
        result = await wrapped_tool.afunc()
        
        assert result["success"] is False
        assert result["error"] == "Network error"
        assert result["error_type"] == "ConnectionError"
        assert result["tool"] == "async_test"
        assert "连接服务失败" in result["message"]
    
    @pytest.mark.asyncio
    async def test_sync_tool_in_async_context(self):
        """测试在异步上下文中运行同步工具"""
        handler = self.create_test_handler()
        
        # 创建一个同步工具（没有afunc）
        def sync_tool(*args, **kwargs):
            return {"result": "success"}
        
        mock_tool = Tool(
            name="sync_tool",
            description="Sync tool",
            func=sync_tool
        )
        
        # 包装工具
        wrapped_tool = handler._wrap_tool_with_error_handling(mock_tool)
        
        # 在异步上下文中执行
        result = await wrapped_tool.afunc()
        assert result["result"] == "success"
    
    def test_error_message_formatting(self):
        """测试错误消息格式化"""
        handler = self.create_test_handler()
        
        # 测试不同类型的错误
        test_cases = [
            (ConnectionError("Network error"), "连接服务失败"),
            (TimeoutError("Timeout"), "操作超时"),
            (ValueError("Invalid input"), "输入参数有误"),
            (PermissionError("Access denied"), "权限不足"),
            (RuntimeError("Unknown error"), "操作失败: Unknown error")
        ]
        
        for error, expected_message in test_cases:
            message = handler._get_user_friendly_error_message(error)
            assert expected_message in message
    
    @pytest.mark.asyncio
    async def test_stream_response_with_tool_error(self):
        """测试流式响应中的工具错误处理"""
        handler = self.create_test_handler()
        
        # 模拟 graph_agent.astream 返回包含工具错误的 chunk
        mock_chunks = [
            {
                "tool": {
                    "name": "test_tool",
                    "args": {"param": "value"}
                }
            },
            {
                "tool": {
                    "name": "test_tool",
                    "output": {
                        "error": "Tool execution failed",
                        "error_type": "RuntimeError",
                        "tool": "test_tool",
                        "success": False,
                        "message": "工具执行失败: RuntimeError"
                    }
                }
            }
        ]
        
        # 模拟 astream
        async def mock_astream(*args, **kwargs):
            for chunk in mock_chunks:
                yield chunk
        
        handler.graph_agent = Mock()
        handler.graph_agent.astream = mock_astream
        
        # 收集所有事件
        events = []
        async for event in handler.stream_response("test message", "session_1"):
            events.append(event)
        
        # 验证事件
        assert len(events) >= 2
        
        # 第一个应该是工具开始事件
        tool_start = events[0]
        assert tool_start["type"] == "tool_call_start"
        assert tool_start["tool_name"] == "test_tool"
        
        # 第二个应该是工具错误事件
        tool_error = events[1]
        assert tool_error["type"] == "tool_error"
        assert tool_error["tool_name"] == "test_tool"
        assert tool_error["error"] == "Tool execution failed"
        assert tool_error["error_type"] == "RuntimeError"
    
    def test_create_tools_with_wrapping(self):
        """测试 _create_tools 方法是否正确应用包装"""
        with patch('app.agents.conversation_tools.create_conversation_tools') as mock_create:
            # 模拟原始工具
            mock_tool = Tool(
                name="mock_tool",
                description="Mock tool",
                func=lambda: "result"
            )
            mock_create.return_value = [mock_tool]
            
            handler = self.create_test_handler()
            tools = handler._create_tools()
            
            # 验证工具被包装
            assert len(tools) == 1
            wrapped_tool = tools[0]
            
            # 原始工具的 func 不应该是包装后的 func
            assert wrapped_tool.func != mock_tool.func
            assert wrapped_tool.name == mock_tool.name
            assert wrapped_tool.description == mock_tool.description


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])