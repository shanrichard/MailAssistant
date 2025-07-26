"""
Chunk Accumulator for Streaming Responses
智能累积流式响应chunks的工具类
"""

import re
import time
from typing import Optional


class ChunkAccumulator:
    """智能累积流式响应chunks的工具类"""
    
    def __init__(self, 
                 min_chunk_size: int = 10,
                 max_wait_time: float = 0.5,
                 delimiter_pattern: str = r'[。！？；\n]'):
        """
        初始化累积器
        
        Args:
            min_chunk_size: 最小chunk大小（字符数）
            max_wait_time: 最大等待时间（秒）
            delimiter_pattern: 分隔符正则表达式（句子边界）
        """
        self.buffer = ""
        self.last_emit_time = time.time()
        self.min_chunk_size = min_chunk_size
        self.max_wait_time = max_wait_time
        self.delimiter_pattern = delimiter_pattern
        self.total_chunks_emitted = 0
    
    def add(self, content: str) -> Optional[str]:
        """添加内容到缓冲区，返回应该发送的内容"""
        self.buffer += content
        
        if self.should_emit():
            return self.flush()
        return None
    
    def should_emit(self) -> bool:
        """判断是否应该发送缓冲内容"""
        # 1. 达到分隔符（句子结束）
        if re.search(self.delimiter_pattern, self.buffer):
            return True
        
        # 2. 缓冲区达到最小大小
        if len(self.buffer) >= self.min_chunk_size:
            return True
        
        # 3. 超过最大等待时间
        if time.time() - self.last_emit_time > self.max_wait_time:
            return True
        
        return False
    
    def flush(self) -> str:
        """清空并返回缓冲区内容"""
        content = self.buffer
        self.buffer = ""
        self.last_emit_time = time.time()
        self.total_chunks_emitted += 1
        return content