"""
TTL缓存实现 - 解决弱引用字典的竞态条件问题
"""
from datetime import datetime, timedelta
import threading
from typing import Dict, Any, Callable, Optional, Tuple
from ..core.logging import get_logger

logger = get_logger(__name__)


class CheckpointerCache:
    """
    线程安全的TTL缓存，支持LRU淘汰策略
    解决弱引用字典的竞态条件问题
    """
    def __init__(self, max_size: int = 1000, ttl_hours: int = 24):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存项数
            ttl_hours: 缓存过期时间（小时）
        """
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._access_count: Dict[str, int] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._ttl = timedelta(hours=ttl_hours)
        
        logger.info(f"CheckpointerCache initialized with max_size={max_size}, ttl_hours={ttl_hours}")
        
    def get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:
        """
        获取或创建缓存项，保证线程安全
        
        Args:
            key: 缓存键
            factory: 创建新值的工厂函数
            
        Returns:
            缓存的值
        """
        with self._lock:
            # 清理过期项
            self._cleanup_expired()
            
            # 检查缓存
            if key in self._cache:
                value, expire_time = self._cache[key]
                if datetime.now() < expire_time:
                    self._access_count[key] = self._access_count.get(key, 0) + 1
                    logger.debug(f"Cache hit for key: {key}")
                    return value
                else:
                    # 过期了，删除
                    del self._cache[key]
                    del self._access_count[key]
                    logger.debug(f"Cache expired for key: {key}")
            
            # 创建新值
            logger.debug(f"Creating new value for key: {key}")
            try:
                value = factory()
            except Exception as e:
                logger.error(f"Failed to create value for key {key}: {e}")
                raise
            
            expire_time = datetime.now() + self._ttl
            
            # LRU淘汰
            if len(self._cache) >= self._max_size:
                self._evict_lru()
            
            self._cache[key] = (value, expire_time)
            self._access_count[key] = 1
            logger.info(f"Created and cached new value for key: {key}")
            return value
    
    def _cleanup_expired(self):
        """清理过期的缓存项"""
        now = datetime.now()
        expired_keys = [k for k, (_, expire) in self._cache.items() if expire <= now]
        
        for key in expired_keys:
            del self._cache[key]
            self._access_count.pop(key, None)
            
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _evict_lru(self):
        """基于访问频率的LRU淘汰"""
        if not self._cache:
            return
            
        # 找出访问次数最少的项
        lru_key = min(self._access_count.items(), key=lambda x: x[1])[0]
        del self._cache[lru_key]
        del self._access_count[lru_key]
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_count.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_hours": self._ttl.total_seconds() / 3600,
                "keys": list(self._cache.keys()),
                "access_counts": dict(self._access_count)
            }
    
    def remove(self, key: str) -> bool:
        """
        移除特定的缓存项
        
        Args:
            key: 要移除的键
            
        Returns:
            是否成功移除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._access_count.pop(key, None)
                logger.debug(f"Removed cache entry: {key}")
                return True
            return False