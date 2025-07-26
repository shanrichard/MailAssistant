"""
测试数据库写入优化
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from app.agents.conversation_handler import ConversationHandler
from app.models.conversation import ConversationMessage


@pytest.mark.asyncio
async def test_no_intermediate_db_writes():
    """验证流式过程中没有中间数据库写入"""
    # 创建 mock 对象
    mock_db = Mock()
    mock_user = Mock(id="test-user")
    
    # 创建 handler
    handler = ConversationHandler(user_id="test-user", db_session=mock_db, user=mock_user)
    
    # Mock LangGraph agent
    mock_chunk_1 = Mock(content="你好", tool_call_chunks=None)
    mock_chunk_2 = Mock(content="，世界", tool_call_chunks=None)
    mock_chunk_3 = Mock(content="。", tool_call_chunks=None)
    
    async def mock_astream(*args, **kwargs):
        yield mock_chunk_1, {}
        yield mock_chunk_2, {}
        yield mock_chunk_3, {}
    
    handler.graph_agent.astream = mock_astream
    
    # 收集所有输出
    responses = []
    async for response in handler.stream_response("测试消息", "test-session"):
        responses.append(response)
    
    # 验证：
    # 1. 用户消息写入一次（开始时）
    # 2. AI 响应写入一次（结束时）
    # 总共应该是 2 次 add 调用
    assert mock_db.add.call_count == 2
    assert mock_db.commit.call_count == 2
    
    # 验证第一次是用户消息
    first_call = mock_db.add.call_args_list[0][0][0]
    assert isinstance(first_call, ConversationMessage)
    assert first_call.role == "user"
    
    # 验证第二次是 AI 消息（完整内容）
    second_call = mock_db.add.call_args_list[1][0][0]
    assert isinstance(second_call, ConversationMessage)
    assert second_call.role == "assistant"
    assert second_call.content == "你好，世界。"  # 完整内容


@pytest.mark.asyncio
async def test_chunk_accumulation():
    """测试 chunk 累积功能"""
    mock_db = Mock()
    mock_user = Mock(id="test-user")
    
    handler = ConversationHandler(user_id="test-user", db_session=mock_db, user=mock_user)
    
    # 模拟很多小 chunks
    small_chunks = []
    text = "这是一个测试消息，用来验证流式响应的累积功能。"
    for char in text:
        small_chunks.append(Mock(content=char, tool_call_chunks=None))
    
    async def mock_astream(*args, **kwargs):
        for chunk in small_chunks:
            yield chunk, {}
    
    handler.graph_agent.astream = mock_astream
    
    # 收集响应 chunks
    response_chunks = []
    async for response in handler.stream_response("测试", "test-session"):
        if response.get("type") == "agent_response_chunk":
            response_chunks.append(response["content"])
    
    # 验证：
    # 1. 响应 chunks 数量应该远少于原始字符数
    assert len(response_chunks) < len(text) / 2  # 至少减少一半
    
    # 2. 最终拼接的内容应该完整
    final_content = "".join(response_chunks)
    assert final_content == text
    
    # 3. 每个 chunk 应该是合理的大小（除了最后一个）
    for chunk in response_chunks[:-1]:
        assert len(chunk) >= 5  # 至少 5 个字符（可以根据配置调整）


@pytest.mark.asyncio
async def test_error_recovery_with_partial_content():
    """测试错误情况下的部分内容保存"""
    mock_db = Mock()
    mock_user = Mock(id="test-user")
    
    handler = ConversationHandler(user_id="test-user", db_session=mock_db, user=mock_user)
    
    # 模拟流式过程中出错
    async def mock_astream(*args, **kwargs):
        yield Mock(content="部分内容", tool_call_chunks=None), {}
        yield Mock(content="已经生成", tool_call_chunks=None), {}
        raise Exception("模拟错误")
    
    handler.graph_agent.astream = mock_astream
    
    # 收集响应
    responses = []
    async for response in handler.stream_response("测试", "test-session"):
        responses.append(response)
    
    # 验证错误响应
    error_response = next((r for r in responses if r.get("type") == "error"), None)
    assert error_response is not None
    
    # 验证部分内容是否被保存
    # 应该有 2 次 add 调用：用户消息 + 部分 AI 响应
    assert mock_db.add.call_count == 2
    
    # 验证保存的部分内容
    ai_msg_call = mock_db.add.call_args_list[1][0][0]
    assert ai_msg_call.content == "部分内容已经生成"


def test_performance_metrics():
    """测试性能指标计算"""
    from app.utils.chunk_accumulator import ChunkAccumulator
    
    # 模拟典型的中文响应
    text = "Python是一种高级编程语言，具有简洁易读的语法特点。它支持多种编程范式，包括面向对象、函数式和过程式编程。Python拥有丰富的标准库和第三方包生态系统，广泛应用于Web开发、数据科学、人工智能等领域。"
    
    # 测试不同配置下的 chunk 数量
    configs = [
        {"min_chunk_size": 5, "expected_max_chunks": 40},
        {"min_chunk_size": 10, "expected_max_chunks": 20},
        {"min_chunk_size": 20, "expected_max_chunks": 10},
    ]
    
    for config in configs:
        acc = ChunkAccumulator(min_chunk_size=config["min_chunk_size"])
        chunks_emitted = 0
        
        # 模拟逐字符接收
        for char in text:
            if acc.add(char):
                chunks_emitted += 1
        
        # 最后的 flush
        if acc.flush():
            chunks_emitted += 1
        
        # 验证 chunk 数量在预期范围内
        assert chunks_emitted <= config["expected_max_chunks"], \
            f"Too many chunks ({chunks_emitted}) for min_size={config['min_chunk_size']}"
        
        print(f"Config: min_size={config['min_chunk_size']}, "
              f"chunks={chunks_emitted}, "
              f"reduction={100 - (chunks_emitted/len(text)*100):.1f}%")