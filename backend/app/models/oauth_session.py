"""
OAuth Session model for storing OAuth flow sessions in database
"""
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from datetime import datetime
import uuid
from enum import Enum

from ..core.database import Base


class SessionStatus(Enum):
    """OAuth会话状态"""
    PENDING = "pending"      # OAuth流程已开始，等待用户授权
    COMPLETED = "completed"  # 用户已完成授权，等待token交换
    EXPIRED = "expired"      # 会话已过期，需要重新开始
    CONSUMED = "consumed"    # Authorization code已使用，会话完成


class OAuthSession(Base):
    """OAuth会话模型 - 用于持久化存储OAuth流程中的会话数据"""
    __tablename__ = "oauth_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.PENDING)
    
    # OAuth流程数据（JSON格式）
    flow_data = Column(Text, nullable=False)  # 序列化的Flow对象信息
    authorization_url = Column(Text, nullable=False)
    state = Column(String(255), nullable=False)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)
    
    def __repr__(self):
        return f"<OAuthSession(session_id={self.session_id}, status={self.status.value}, expires_at={self.expires_at})>"