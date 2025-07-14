from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base

class EmailAnalysis(Base):
    __tablename__ = "email_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # LLM分析结果
    llm_provider = Column(String(50), nullable=False)  # openai, anthropic, gemini
    llm_model = Column(String(100), nullable=False)
    
    # 分析结果
    category = Column(String(50), nullable=False)  # important, spam, promotional, social, etc.
    importance_score = Column(Float, nullable=False, default=0.0)
    importance_reason = Column(Text)  # LLM给出的重要性分析原因
    
    # 内容分析
    summary = Column(Text)  # 邮件内容总结
    key_points = Column(JSON)  # 关键要点列表
    sentiment = Column(String(20))  # positive, negative, neutral
    urgency_level = Column(String(20))  # high, medium, low
    
    # 商业价值分析
    has_business_opportunity = Column(Boolean, default=False)
    business_opportunity_type = Column(String(100))  # 商业机会类型
    business_opportunity_description = Column(Text)
    
    # 个性化分析
    matches_user_preferences = Column(Boolean, default=False)
    preference_match_reasons = Column(JSON)  # 匹配的偏好原因列表
    
    # 推荐操作
    recommended_actions = Column(JSON)  # 推荐的操作列表
    
    # 向量表示（用于语义搜索）
    content_embedding = Column(String)  # 存储向量字符串表示
    
    # 分析元数据
    analysis_version = Column(String(20), default="1.0")
    processing_time_ms = Column(Integer)  # 分析耗时（毫秒）
    confidence_score = Column(Float, default=0.0)  # 分析结果置信度
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    email = relationship("Email", back_populates="analysis")
    user = relationship("User", back_populates="email_analyses")

    def __repr__(self):
        return f"<EmailAnalysis(id={self.id}, category='{self.category}', importance_score={self.importance_score})>"