"""
Session Store for OAuth Flow Manager
OAuth会话状态存储和管理
"""

import uuid
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from threading import Lock

from ..core.logging import get_logger

logger = get_logger(__name__)


class SessionData:
    """会话数据对象"""
    def __init__(self, session_id: str, data: Dict[str, Any], ttl_minutes: int = 10):
        self.session_id = session_id
        self.data = data
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
        self.last_accessed = self.created_at
        
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.utcnow() > self.expires_at
        
    def update_access_time(self):
        """更新最后访问时间"""
        self.last_accessed = datetime.utcnow()
        
    def extend_expiry(self, minutes: int = 10):
        """延长过期时间"""
        self.expires_at = datetime.utcnow() + timedelta(minutes=minutes)
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'is_expired': self.is_expired()
        }


class SessionStore:
    """
    会话存储器
    
    提供OAuth会话的持久化存储，支持：
    1. 会话创建和管理
    2. TTL过期清理
    3. 原子操作保证
    4. 调试信息获取
    """
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.lock = Lock()
        
        logger.info("Session Store initialized")
    
    def create_session(self, data: Dict[str, Any], ttl_minutes: int = 10) -> str:
        """
        创建新会话
        
        Args:
            data: 会话数据
            ttl_minutes: 过期时间（分钟）
            
        Returns:
            session_id: 会话ID
        """
        session_id = str(uuid.uuid4())
        
        session_data = SessionData(session_id, data, ttl_minutes)
        
        with self.lock:
            self.sessions[session_id] = session_data
            
        logger.info("Session created", 
                   session_id=session_id,
                   ttl_minutes=ttl_minutes,
                   expires_at=session_data.expires_at.isoformat())
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话数据或None
        """
        with self.lock:
            session_data = self.sessions.get(session_id)
            
            if not session_data:
                logger.warning("Session not found", session_id=session_id)
                return None
                
            if session_data.is_expired():
                logger.warning("Session expired", session_id=session_id)
                del self.sessions[session_id]
                return None
            
            # 更新访问时间
            session_data.update_access_time()
            
            logger.debug("Session retrieved", session_id=session_id)
            return session_data.data
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        更新会话数据
        
        Args:
            session_id: 会话ID
            data: 新的会话数据
            
        Returns:
            是否更新成功
        """
        with self.lock:
            session_data = self.sessions.get(session_id)
            
            if not session_data:
                logger.warning("Cannot update non-existent session", session_id=session_id)
                return False
                
            if session_data.is_expired():
                logger.warning("Cannot update expired session", session_id=session_id)
                del self.sessions[session_id]
                return False
            
            # 更新数据和访问时间
            session_data.data.update(data)
            session_data.update_access_time()
            
            logger.info("Session updated", session_id=session_id)
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否删除成功
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info("Session deleted", session_id=session_id)
                return True
            else:
                logger.warning("Cannot delete non-existent session", session_id=session_id)
                return False
    
    def extend_session(self, session_id: str, minutes: int = 10) -> bool:
        """
        延长会话过期时间
        
        Args:
            session_id: 会话ID
            minutes: 延长时间（分钟）
            
        Returns:
            是否延长成功
        """
        with self.lock:
            session_data = self.sessions.get(session_id)
            
            if not session_data:
                logger.warning("Cannot extend non-existent session", session_id=session_id)
                return False
                
            if session_data.is_expired():
                logger.warning("Cannot extend expired session", session_id=session_id)
                del self.sessions[session_id]
                return False
            
            session_data.extend_expiry(minutes)
            
            logger.info("Session extended", 
                       session_id=session_id,
                       new_expiry=session_data.expires_at.isoformat())
            return True
    
    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            清理的会话数量
        """
        with self.lock:
            expired_sessions = [
                session_id for session_id, session_data in self.sessions.items()
                if session_data.is_expired()
            ]
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                
            if expired_sessions:
                logger.info("Cleaned up expired sessions", count=len(expired_sessions))
                
            return len(expired_sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息（用于调试）
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息或None
        """
        with self.lock:
            session_data = self.sessions.get(session_id)
            
            if not session_data:
                return None
                
            return session_data.to_dict()
    
    def get_all_sessions_info(self) -> Dict[str, Any]:
        """
        获取所有会话信息（用于调试）
        
        Returns:
            所有会话信息
        """
        # 先清理过期会话
        cleaned_count = self.cleanup_expired_sessions()
        
        with self.lock:
            sessions_info = [
                session_data.to_dict() 
                for session_data in self.sessions.values()
            ]
            
            return {
                'total_sessions': len(self.sessions),
                'cleaned_sessions': cleaned_count,
                'sessions': sessions_info,
                'store_stats': {
                    'active_sessions': len(self.sessions),
                    'last_cleanup': datetime.utcnow().isoformat()
                }
            }
    
    def clear_all_sessions(self) -> int:
        """
        清除所有会话（用于测试/调试）
        
        Returns:
            清除的会话数量
        """
        with self.lock:
            count = len(self.sessions)
            self.sessions.clear()
            
            logger.warning("All sessions cleared", count=count)
            return count
    
    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在且未过期
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话是否存在
        """
        with self.lock:
            session_data = self.sessions.get(session_id)
            
            if not session_data:
                return False
                
            if session_data.is_expired():
                del self.sessions[session_id]
                return False
                
            return True


# 全局Session Store实例
session_store = SessionStore()