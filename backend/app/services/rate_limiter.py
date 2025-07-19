"""
速率限制服务
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# 内存中的速率限制存储（生产环境应使用Redis）
rate_limit_storage: Dict[str, Dict[str, any]] = {}

async def check_rate_limit(
    user_id: str, 
    limit: int = 20, 
    window_seconds: int = 60
) -> bool:
    """
    检查用户是否超过速率限制
    
    Args:
        user_id: 用户ID
        limit: 时间窗口内允许的最大请求数
        window_seconds: 时间窗口大小（秒）
        
    Returns:
        bool: True表示可以继续，False表示超过限制
    """
    now = datetime.now()
    window_start = now - timedelta(seconds=window_seconds)
    
    # 获取或创建用户的速率限制记录
    if user_id not in rate_limit_storage:
        rate_limit_storage[user_id] = {
            'requests': [],
            'last_cleanup': now
        }
    
    user_data = rate_limit_storage[user_id]
    
    # 清理过期的请求记录
    user_data['requests'] = [
        req_time for req_time in user_data['requests'] 
        if req_time > window_start
    ]
    
    # 检查是否超过限制
    if len(user_data['requests']) >= limit:
        logger.warning("Rate limit exceeded", 
                      user_id=user_id, 
                      request_count=len(user_data['requests']),
                      limit=limit)
        return False
    
    # 记录新请求
    user_data['requests'].append(now)
    
    # 定期清理（每分钟）
    if now - user_data['last_cleanup'] > timedelta(minutes=1):
        user_data['last_cleanup'] = now
        await cleanup_expired_records()
    
    return True

async def cleanup_expired_records():
    """清理过期的速率限制记录"""
    now = datetime.now()
    expired_threshold = now - timedelta(minutes=5)
    
    users_to_remove = []
    for user_id, data in rate_limit_storage.items():
        if not data['requests'] or max(data['requests']) < expired_threshold:
            users_to_remove.append(user_id)
    
    for user_id in users_to_remove:
        del rate_limit_storage[user_id]
    
    if users_to_remove:
        logger.info("Cleaned up rate limit records", count=len(users_to_remove))

# Redis实现（用于生产环境）
class RedisRateLimiter:
    """基于Redis的速率限制器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_rate_limit(
        self, 
        user_id: str, 
        limit: int = 20, 
        window_seconds: int = 60
    ) -> bool:
        """使用Redis实现的速率限制检查"""
        key = f"rate_limit:{user_id}"
        now = datetime.now().timestamp()
        window_start = now - window_seconds
        
        # 使用Redis的有序集合和Lua脚本原子性操作
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        
        -- 移除过期的记录
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
        
        -- 获取当前计数
        local count = redis.call('ZCARD', key)
        
        -- 检查是否超过限制
        if count >= limit then
            return 0
        end
        
        -- 添加新记录
        redis.call('ZADD', key, now, now)
        redis.call('EXPIRE', key, window_seconds + 60)
        
        return 1
        """
        
        try:
            result = await self.redis.eval(
                lua_script, 
                1, 
                key, 
                str(now), 
                str(window_start), 
                str(limit)
            )
            return bool(result)
        except Exception as e:
            logger.error("Redis rate limit check failed", 
                        user_id=user_id, 
                        error=str(e))
            # 降级到允许请求
            return True