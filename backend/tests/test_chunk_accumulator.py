"""
Tests for ChunkAccumulator
"""

import pytest
import time
from app.utils.chunk_accumulator import ChunkAccumulator


def test_accumulator_with_delimiter():
    """测试遇到分隔符时立即发送"""
    acc = ChunkAccumulator(min_chunk_size=20)
    
    # 添加不足最小大小的内容
    result = acc.add("你好")
    assert result is None
    
    # 添加包含分隔符的内容
    result = acc.add("，世界。")
    assert result == "你好，世界。"


def test_accumulator_min_size():
    """测试达到最小大小时发送"""
    acc = ChunkAccumulator(min_chunk_size=5)
    
    result = acc.add("一二三")
    assert result is None
    
    result = acc.add("四五")
    assert result == "一二三四五"


def test_accumulator_timeout():
    """测试超时发送"""
    acc = ChunkAccumulator(max_wait_time=0.1)
    
    result = acc.add("测试")
    assert result is None
    
    time.sleep(0.15)
    result = acc.add("内容")
    assert result == "测试内容"


def test_accumulator_flush():
    """测试强制刷新"""
    acc = ChunkAccumulator()
    acc.add("未完成的内容")
    
    result = acc.flush()
    assert result == "未完成的内容"
    assert acc.buffer == ""


def test_accumulator_mixed_content():
    """测试混合中英文内容"""
    acc = ChunkAccumulator(min_chunk_size=10)
    
    # 测试中英文混合
    result = acc.add("Hello 世界")
    assert result is None  # 8个字符，未达到最小大小
    
    result = acc.add("！Welcome")
    assert result == "Hello 世界！Welcome"  # 遇到感叹号分隔符


def test_accumulator_multiple_sentences():
    """测试多个句子的处理"""
    acc = ChunkAccumulator()
    
    # 第一句
    result = acc.add("这是第一句话。")
    assert result == "这是第一句话。"
    
    # 第二句
    result = acc.add("这是")
    assert result is None
    
    result = acc.add("第二句话。")
    assert result == "这是第二句话。"


def test_accumulator_total_chunks_emitted():
    """测试发送计数器"""
    acc = ChunkAccumulator(min_chunk_size=5)
    
    assert acc.total_chunks_emitted == 0
    
    acc.add("12345")  # 触发发送
    assert acc.total_chunks_emitted == 1
    
    acc.add("67890")  # 再次触发
    assert acc.total_chunks_emitted == 2