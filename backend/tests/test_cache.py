"""
测试TTL缓存功能
"""
import asyncio
import time
from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock
from threading import Thread
import concurrent.futures

from app.core.cache import CheckpointerCache


class TestCheckpointerCache:
    """测试CheckpointerCache的功能"""
    
    def test_basic_get_or_create(self):
        """测试基本的获取或创建功能"""
        cache = CheckpointerCache(max_size=10, ttl_hours=1)
        
        # 创建值的工厂函数
        factory_called = False
        def factory():
            nonlocal factory_called
            factory_called = True
            return "test_value"
        
        # 第一次调用应该创建新值
        value = cache.get_or_create("test_key", factory)
        assert value == "test_value"
        assert factory_called
        
        # 第二次调用应该从缓存获取
        factory_called = False
        value2 = cache.get_or_create("test_key", factory)
        assert value2 == "test_value"
        assert not factory_called  # 工厂函数不应被调用
    
    def test_ttl_expiration(self):
        """测试TTL过期功能"""
        # 创建一个TTL很短的缓存（0.001小时 = 3.6秒）
        cache = CheckpointerCache(max_size=10, ttl_hours=0.001)
        
        # 添加一个值
        cache.get_or_create("test_key", lambda: "test_value")
        
        # 立即获取应该成功
        value = cache.get_or_create("test_key", lambda: "new_value")
        assert value == "test_value"
        
        # 等待过期
        time.sleep(4)
        
        # 现在应该创建新值
        value = cache.get_or_create("test_key", lambda: "new_value")
        assert value == "new_value"
    
    def test_lru_eviction(self):
        """测试LRU淘汰策略"""
        cache = CheckpointerCache(max_size=3, ttl_hours=1)
        
        # 添加3个值
        cache.get_or_create("key1", lambda: "value1")
        cache.get_or_create("key2", lambda: "value2")
        cache.get_or_create("key3", lambda: "value3")
        
        # 访问key1和key2，增加它们的访问计数
        cache.get_or_create("key1", lambda: "value1")
        cache.get_or_create("key2", lambda: "value2")
        
        # 添加第4个值，应该淘汰key3（访问次数最少）
        cache.get_or_create("key4", lambda: "value4")
        
        # 验证缓存内容
        stats = cache.get_stats()
        assert stats["size"] == 3
        assert "key3" not in stats["keys"]
        assert "key1" in stats["keys"]
        assert "key2" in stats["keys"]
        assert "key4" in stats["keys"]
    
    def test_concurrent_access(self):
        """测试并发访问的线程安全性"""
        cache = CheckpointerCache(max_size=100, ttl_hours=1)
        results = []
        
        def access_cache(key, value):
            """并发访问缓存"""
            for _ in range(100):
                result = cache.get_or_create(key, lambda: value)
                results.append((key, result))
        
        # 创建多个线程并发访问
        threads = []
        for i in range(10):
            key = f"key_{i % 3}"  # 使用3个不同的键
            value = f"value_{i}"
            thread = Thread(target=access_cache, args=(key, value))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证结果一致性
        # 对于每个键，所有结果应该是相同的（第一个创建的值）
        key_values = {}
        for key, value in results:
            if key not in key_values:
                key_values[key] = value
            else:
                # 确保同一个键总是返回相同的值
                assert key_values[key] == value
    
    def test_remove_functionality(self):
        """测试移除功能"""
        cache = CheckpointerCache(max_size=10, ttl_hours=1)
        
        # 添加值
        cache.get_or_create("test_key", lambda: "test_value")
        
        # 验证存在
        stats = cache.get_stats()
        assert "test_key" in stats["keys"]
        
        # 移除
        removed = cache.remove("test_key")
        assert removed
        
        # 验证已移除
        stats = cache.get_stats()
        assert "test_key" not in stats["keys"]
        
        # 再次移除应该返回False
        removed = cache.remove("test_key")
        assert not removed
    
    def test_clear_functionality(self):
        """测试清空缓存功能"""
        cache = CheckpointerCache(max_size=10, ttl_hours=1)
        
        # 添加多个值
        for i in range(5):
            cache.get_or_create(f"key_{i}", lambda i=i: f"value_{i}")
        
        # 验证有内容
        stats = cache.get_stats()
        assert stats["size"] == 5
        
        # 清空
        cache.clear()
        
        # 验证已清空
        stats = cache.get_stats()
        assert stats["size"] == 0
        assert len(stats["keys"]) == 0
    
    def test_stats_functionality(self):
        """测试统计功能"""
        cache = CheckpointerCache(max_size=50, ttl_hours=24)
        
        # 添加一些值并访问
        cache.get_or_create("key1", lambda: "value1")
        cache.get_or_create("key2", lambda: "value2")
        cache.get_or_create("key1", lambda: "value1")  # 再次访问key1
        
        stats = cache.get_stats()
        
        assert stats["size"] == 2
        assert stats["max_size"] == 50
        assert stats["ttl_hours"] == 24
        assert "key1" in stats["keys"]
        assert "key2" in stats["keys"]
        assert stats["access_counts"]["key1"] == 2
        assert stats["access_counts"]["key2"] == 1
    
    @pytest.mark.asyncio
    async def test_async_compatibility(self):
        """测试与异步代码的兼容性"""
        cache = CheckpointerCache(max_size=10, ttl_hours=1)
        
        async def async_factory():
            await asyncio.sleep(0.1)
            return "async_value"
        
        # 在异步上下文中使用同步缓存
        loop = asyncio.get_event_loop()
        value = await loop.run_in_executor(
            None, 
            cache.get_or_create, 
            "async_key", 
            lambda: "sync_value"
        )
        
        assert value == "sync_value"


if __name__ == "__main__":
    # 运行基本测试
    test = TestCheckpointerCache()
    test.test_basic_get_or_create()
    test.test_lru_eviction()
    test.test_concurrent_access()
    print("All tests passed!")