from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON, Date, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 报告日期
    report_date = Column(Date, nullable=False)
    
    # 邮件统计
    total_emails = Column(Integer, default=0)
    important_emails_count = Column(Integer, default=0)
    spam_emails_count = Column(Integer, default=0)
    promotional_emails_count = Column(Integer, default=0)
    social_emails_count = Column(Integer, default=0)
    unread_emails_count = Column(Integer, default=0)
    
    # 重要邮件列表
    important_emails = Column(JSON)  # 重要邮件的ID和摘要列表
    
    # 分类汇总
    category_summary = Column(JSON)  # 各分类的邮件汇总
    
    # 商业机会
    business_opportunities = Column(JSON)  # 商业机会邮件列表
    business_opportunities_count = Column(Integer, default=0)
    
    # 发件人统计
    top_senders = Column(JSON)  # 发件人频次统计
    new_senders = Column(JSON)  # 新发件人列表
    
    # 关键词分析
    trending_keywords = Column(JSON)  # 热门关键词列表
    important_topics = Column(JSON)  # 重要话题列表
    
    # 个性化洞察
    personal_insights = Column(JSON)  # 个性化洞察和建议
    preference_matches = Column(JSON)  # 偏好匹配情况
    
    # 操作建议
    recommended_actions = Column(JSON)  # 推荐的批量操作
    priority_emails = Column(JSON)  # 需要优先处理的邮件
    
    # 报告元数据
    generation_time_ms = Column(Integer)  # 生成耗时（毫秒）
    llm_provider = Column(String(50))  # 使用的LLM提供商
    llm_model = Column(String(100))  # 使用的LLM模型
    report_version = Column(String(20), default="1.0")
    
    # 用户反馈
    user_rating = Column(Integer)  # 1-5星评分
    user_feedback = Column(Text)  # 用户文字反馈
    is_useful = Column(Boolean)  # 用户是否觉得有用
    
    # 状态
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    is_read_by_user = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="daily_reports")
    
    # 索引
    __table_args__ = (
        Index('idx_daily_reports_user_date', 'user_id', 'report_date', unique=True),
        Index('idx_daily_reports_date', 'report_date'),
        Index('idx_daily_reports_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<DailyReport(id={self.id}, user_id={self.user_id}, date={self.report_date})>"