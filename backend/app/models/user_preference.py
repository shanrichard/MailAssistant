from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON, Index, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from ..core.database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # 偏好类型
    preference_type = Column(String(50), nullable=False)  # sender, keyword, topic, domain, etc.
    
    # 偏好内容
    preference_key = Column(String(255), nullable=False)  # 具体的偏好键（如发件人邮箱、关键词等）
    preference_value = Column(Text, nullable=False)  # 偏好值或描述
    
    # 偏好设置
    is_important = Column(Boolean, default=True)  # True表示重要，False表示不重要
    priority_level = Column(Integer, default=5)  # 1-10的优先级，10最高
    
    # 自然语言描述
    natural_description = Column(Text)  # 用户用自然语言描述的偏好
    
    # 向量表示（用于语义匹配）
    description_embedding = Column(String)  # 偏好描述的向量表示
    
    # 学习数据
    match_count = Column(Integer, default=0)  # 匹配次数
    positive_feedback_count = Column(Integer, default=0)  # 正向反馈次数
    negative_feedback_count = Column(Integer, default=0)  # 负向反馈次数
    effectiveness_score = Column(Float, default=0.0)  # 有效性评分
    
    # 定时任务偏好（仅对preference_type='schedule'有效）
    daily_report_time = Column(Time)  # 日报生成时间，默认09:00
    timezone = Column(String(50))  # 用户时区，如'Asia/Shanghai'
    auto_sync_enabled = Column(Boolean, default=True)  # 是否启用自动同步
    
    # 状态
    is_active = Column(Boolean, default=True)
    is_learned = Column(Boolean, default=False)  # 是否是系统学习得到的偏好
    
    # 元数据
    source = Column(String(50), default="user")  # user, system, learned
    confidence_level = Column(Float, default=1.0)  # 置信度
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_matched_at = Column(DateTime(timezone=True))
    
    # 关系
    user = relationship("User", back_populates="preferences")
    
    # 索引
    __table_args__ = (
        Index('idx_user_preferences_user_id', 'user_id'),
        Index('idx_user_preferences_type', 'preference_type'),
        Index('idx_user_preferences_key', 'preference_key'),
        Index('idx_user_preferences_active', 'is_active'),
        Index('idx_user_preferences_priority', 'priority_level'),
    )

    def __repr__(self):
        return f"<UserPreference(id={self.id}, type='{self.preference_type}', key='{self.preference_key}')>"