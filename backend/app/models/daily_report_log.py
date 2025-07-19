"""
日报生成日志模型
"""
from sqlalchemy import Column, String, Date, JSON, DateTime, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from ..core.database import Base

class DailyReportLog(Base):
    """日报生成日志表"""
    __tablename__ = "daily_report_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    report_date = Column(Date, nullable=False, index=True)
    report_content = Column(JSON, nullable=False)
    status = Column(String, default="completed")  # completed, failed, processing
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # 唯一索引保证幂等性
    __table_args__ = (
        UniqueConstraint('user_id', 'report_date', name='_user_date_uc'),
    )