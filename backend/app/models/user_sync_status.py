"""
用户同步状态模型
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..core.database import Base


class UserSyncStatus(Base):
    """用户邮件同步状态表（简化版）"""
    __tablename__ = "user_sync_status"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    last_sync_time = Column(DateTime(timezone=True))
    sync_message = Column(Text)
    
    # 时间戳（保留用于系统管理）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSyncStatus(user_id={self.user_id}, last_sync_time={self.last_sync_time})>"