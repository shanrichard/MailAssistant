"""
Task management service for MailAssistant
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from ..core.logging import get_logger
from ..models.task_log import TaskLog, TaskStatus, TaskType

logger = get_logger(__name__)

class TaskService:
    """任务管理服务"""
    
    def get_user_task_history(self, db: Session, user_id: str, limit: int = 50, task_type: TaskType = None) -> List[Dict[str, Any]]:
        """获取用户任务历史"""
        try:
            query = db.query(TaskLog).filter(TaskLog.user_id == user_id)
            
            if task_type:
                query = query.filter(TaskLog.task_type == task_type)
            
            tasks = query.order_by(desc(TaskLog.created_at)).limit(limit).all()
            
            task_list = []
            for task in tasks:
                task_list.append({
                    "id": str(task.id),
                    "task_type": task.task_type,
                    "task_name": task.task_name,
                    "status": task.status,
                    "progress_percentage": task.progress_percentage,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "execution_time_ms": task.execution_time_ms,
                    "error_message": task.error_message,
                    "retry_count": task.retry_count,
                    "emails_processed": task.emails_processed,
                    "output_results": task.output_results,
                    "created_at": task.created_at
                })
            
            return task_list
            
        except Exception as e:
            logger.error("Failed to get user task history", user_id=user_id, error=str(e))
            return []
    
    def get_task_details(self, db: Session, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详细信息"""
        try:
            task = db.query(TaskLog).filter(TaskLog.id == task_id).first()
            
            if not task:
                return None
            
            return {
                "id": str(task.id),
                "user_id": str(task.user_id) if task.user_id else None,
                "task_type": task.task_type,
                "task_name": task.task_name,
                "task_description": task.task_description,
                "status": task.status,
                "progress_percentage": task.progress_percentage,
                "input_parameters": task.input_parameters,
                "output_results": task.output_results,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "execution_time_ms": task.execution_time_ms,
                "error_message": task.error_message,
                "error_traceback": task.error_traceback,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "next_retry_at": task.next_retry_at,
                "scheduler_job_id": task.scheduler_job_id,
                "task_unique_key": task.task_unique_key,
                "emails_processed": task.emails_processed,
                "emails_analyzed": task.emails_analyzed,
                "operations_performed": task.operations_performed,
                "created_at": task.created_at,
                "updated_at": task.updated_at
            }
            
        except Exception as e:
            logger.error("Failed to get task details", task_id=task_id, error=str(e))
            return None

# 创建全局实例
task_service = TaskService()