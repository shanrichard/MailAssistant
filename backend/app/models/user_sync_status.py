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
    """用户邮件同步状态表"""
    __tablename__ = "user_sync_status"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    is_syncing = Column(Boolean, default=False, nullable=False)
    sync_type = Column(String(20))  # 'full', 'incremental', 'rescan'
    started_at = Column(DateTime(timezone=True))
    progress_percentage = Column(Integer, default=0)
    current_stats = Column(JSONB)
    task_id = Column(String(100))
    error_message = Column(Text)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSyncStatus(user_id={self.user_id}, is_syncing={self.is_syncing}, sync_type='{self.sync_type}')>"