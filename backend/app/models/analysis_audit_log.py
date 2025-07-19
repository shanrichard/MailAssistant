"""
邮件分析审计日志模型
"""
from sqlalchemy import Column, String, Integer, Text, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from ..core.database import Base

class AnalysisAuditLog(Base):
    """邮件分析审计日志"""
    __tablename__ = "analysis_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id"), nullable=True)
    operation_type = Column(String, nullable=False, index=True)  # analyze, batch_analyze, generate_report, sync_emails
    request_params = Column(JSON)
    response_data = Column(JSON)
    execution_time_ms = Column(Integer)
    status = Column(String)  # success, error
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)