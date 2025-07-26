from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Gmail API相关字段
    gmail_id = Column(String(255), nullable=False)  # 移除全局unique，改为联合约束
    thread_id = Column(String(255), nullable=False)
    
    # 邮件基本信息
    subject = Column(Text, nullable=False)
    sender = Column(String(255), nullable=False)
    recipients = Column(Text)  # JSON格式存储收件人列表
    cc_recipients = Column(Text)  # JSON格式存储抄送人列表
    bcc_recipients = Column(Text)  # JSON格式存储密送人列表
    
    # 邮件内容
    body_plain = Column(Text)
    body_html = Column(Text)
    
    # 邮件元数据
    received_at = Column(DateTime(timezone=True), nullable=False)
    is_read = Column(Boolean, default=False)
    is_important = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    labels = Column(Text)  # JSON格式存储标签列表
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="emails")
    
    # 索引和约束
    __table_args__ = (
        # 联合唯一约束：防止同一用户的同一封Gmail邮件重复插入（专家建议）
        UniqueConstraint('gmail_id', 'user_id', name='_gmail_user_uc'),
        # 索引
        Index('idx_emails_user_id', 'user_id'),
        Index('idx_emails_gmail_id', 'gmail_id'),
        Index('idx_emails_received_at', 'received_at'),
    )

    def __repr__(self):
        return f"<Email(id={self.id}, subject='{self.subject[:50]}...', sender='{self.sender}')>"