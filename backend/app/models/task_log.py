from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, ENUM
import uuid
from enum import Enum

from ..core.database import Base

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskType(str, Enum):
    EMAIL_SYNC = "email_sync"
    EMAIL_ANALYSIS = "email_analysis"
    DAILY_REPORT = "daily_report"
    BATCH_OPERATION = "batch_operation"
    PREFERENCE_UPDATE = "preference_update"
    CLEANUP = "cleanup"

class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 全局任务可能没有用户
    
    # 任务基本信息
    task_type = Column(ENUM(TaskType), nullable=False)
    task_name = Column(String(255), nullable=False)
    task_description = Column(Text)
    
    # 任务状态
    status = Column(ENUM(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    progress_percentage = Column(Integer, default=0)  # 0-100
    
    # 任务参数
    input_parameters = Column(JSON)  # 任务输入参数
    output_results = Column(JSON)  # 任务输出结果
    
    # 执行信息
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    execution_time_ms = Column(Integer)  # 执行耗时（毫秒）
    
    # 错误处理
    error_message = Column(Text)
    error_traceback = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_retry_at = Column(DateTime(timezone=True))
    
    # 资源使用
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)
    
    # 业务指标
    emails_processed = Column(Integer, default=0)
    emails_analyzed = Column(Integer, default=0)
    operations_performed = Column(Integer, default=0)
    
    # 任务优先级和调度
    priority_level = Column(Integer, default=5)  # 1-10，10最高
    scheduled_at = Column(DateTime(timezone=True))
    is_scheduled = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    recurring_pattern = Column(String(100))  # cron表达式
    
    # 依赖关系
    parent_task_id = Column(UUID(as_uuid=True), ForeignKey("task_logs.id"))
    depends_on_tasks = Column(JSON)  # 依赖的任务ID列表
    
    # 元数据
    worker_id = Column(String(100))  # 执行任务的工作节点ID
    task_version = Column(String(20), default="1.0")
    environment = Column(String(50), default="production")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    user = relationship("User", back_populates="task_logs")
    parent_task = relationship("TaskLog", remote_side=[id], backref="subtasks")
    
    # 索引
    __table_args__ = (
        Index('idx_task_logs_user_id', 'user_id'),
        Index('idx_task_logs_type', 'task_type'),
        Index('idx_task_logs_status', 'status'),
        Index('idx_task_logs_created_at', 'created_at'),
        Index('idx_task_logs_scheduled_at', 'scheduled_at'),
        Index('idx_task_logs_priority', 'priority_level'),
    )

    def __repr__(self):
        return f"<TaskLog(id={self.id}, type='{self.task_type}', status='{self.status}')>"