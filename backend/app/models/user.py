"""
User model for authentication and user management
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, time
import uuid
from typing import Optional, Dict, Any

from ..core.database import Base
from ..core.security import encryption_manager


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    google_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)  # 使用Text类型，不限制长度
    
    # Encrypted Gmail OAuth tokens
    _encrypted_gmail_tokens = Column("encrypted_gmail_tokens", Text, nullable=True)
    
    # User preferences
    preferences_text = Column(Text, nullable=True)
    daily_report_time = Column(Time, default=time(8, 0))  # 8:00 AM
    timezone = Column(String(50), default="UTC")
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    email_analyses = relationship("EmailAnalysis", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    daily_reports = relationship("DailyReport", back_populates="user", cascade="all, delete-orphan")
    task_logs = relationship("TaskLog", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def gmail_tokens(self) -> Optional[str]:
        """Get decrypted Gmail tokens"""
        if not self._encrypted_gmail_tokens:
            return None
        return self._encrypted_gmail_tokens
    
    @gmail_tokens.setter
    def gmail_tokens(self, tokens: Optional[Dict[str, Any]]):
        """Set encrypted Gmail tokens"""
        if tokens is None:
            self._encrypted_gmail_tokens = None
        else:
            self._encrypted_gmail_tokens = encryption_manager.encrypt_json(tokens)
    
    def get_decrypted_gmail_tokens(self) -> Optional[Dict[str, Any]]:
        """Get decrypted Gmail tokens as dictionary"""
        if not self._encrypted_gmail_tokens:
            return None
        try:
            return encryption_manager.decrypt_json(self._encrypted_gmail_tokens)
        except Exception:
            return None
    
    def update_gmail_tokens(self, tokens: Dict[str, Any]) -> None:
        """Update Gmail tokens"""
        from ..utils.datetime_utils import utc_now
        self.gmail_tokens = tokens
        self.updated_at = utc_now()
    
    def clear_gmail_tokens(self) -> None:
        """Clear Gmail tokens"""
        from ..utils.datetime_utils import utc_now
        self._encrypted_gmail_tokens = None
        self.updated_at = utc_now()
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"