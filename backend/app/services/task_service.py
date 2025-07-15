"""
Task management service for MailAssistant
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from ..core.logging import get_logger
from ..models.user import User
from ..models.task_log import TaskLog, TaskStatus, TaskType
from ..models.user_preference import UserPreference
from ..scheduler.jobs import setup_user_jobs, remove_user_jobs, update_user_schedule
from ..scheduler.scheduler_app import scheduler, get_scheduler_status, get_active_jobs

logger = get_logger(__name__)

class TaskService:
    """任务管理服务"""
    
    async def create_user_schedule(self, db: Session, user_id: str, daily_time: time = None, timezone_str: str = "Asia/Shanghai") -> bool:
        """为新用户创建调度偏好和任务"""
        try:
            # 设置默认时间
            if daily_time is None:
                daily_time = time(9, 0)  # 默认09:00
            
            # 检查是否已有调度偏好
            existing_pref = db.query(UserPreference).filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == "schedule"
            ).first()
            
            if existing_pref:
                # 更新现有偏好
                existing_pref.daily_report_time = daily_time
                existing_pref.timezone = timezone_str
                existing_pref.auto_sync_enabled = True
                existing_pref.is_active = True
            else:
                # 创建新的调度偏好
                schedule_pref = UserPreference(
                    user_id=user_id,
                    preference_type="schedule",
                    preference_key="daily_schedule",
                    preference_value=f"daily_report_at_{daily_time.strftime('%H:%M')}",
                    daily_report_time=daily_time,
                    timezone=timezone_str,
                    auto_sync_enabled=True,
                    natural_description=f"Generate daily email report at {daily_time.strftime('%H:%M')} in {timezone_str}",
                    is_active=True
                )
                db.add(schedule_pref)
            
            db.commit()
            
            # 设置调度任务
            await setup_user_jobs(user_id)
            
            logger.info(
                "User schedule created successfully",
                user_id=user_id,
                time=daily_time.strftime("%H:%M"),
                timezone=timezone_str
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to create user schedule", user_id=user_id, error=str(e))
            db.rollback()
            return False
    
    async def update_user_schedule(self, db: Session, user_id: str, daily_time: time, timezone_str: str) -> bool:
        """更新用户的调度设置"""
        try:
            # 更新数据库中的偏好设置
            schedule_pref = db.query(UserPreference).filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == "schedule"
            ).first()
            
            if schedule_pref:
                schedule_pref.daily_report_time = daily_time
                schedule_pref.timezone = timezone_str
                schedule_pref.updated_at = datetime.utcnow()
            else:
                # 如果不存在，创建新的
                await self.create_user_schedule(db, user_id, daily_time, timezone_str)
                return True
            
            db.commit()
            
            # 更新调度任务
            update_user_schedule(user_id, daily_time, timezone_str)
            
            logger.info(
                "User schedule updated successfully",
                user_id=user_id,
                time=daily_time.strftime("%H:%M"),
                timezone=timezone_str
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to update user schedule", user_id=user_id, error=str(e))
            db.rollback()
            return False
    
    def get_user_schedule(self, db: Session, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的调度设置"""
        try:
            schedule_pref = db.query(UserPreference).filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == "schedule",
                UserPreference.is_active == True
            ).first()
            
            if schedule_pref:
                return {
                    "daily_report_time": schedule_pref.daily_report_time.strftime("%H:%M") if schedule_pref.daily_report_time else "09:00",
                    "timezone": schedule_pref.timezone or "Asia/Shanghai",
                    "auto_sync_enabled": schedule_pref.auto_sync_enabled,
                    "created_at": schedule_pref.created_at,
                    "updated_at": schedule_pref.updated_at
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to get user schedule", user_id=user_id, error=str(e))
            return None
    
    async def trigger_user_task(self, db: Session, user_id: str, task_type: TaskType) -> Optional[str]:
        """手动触发用户任务"""
        try:
            from ..scheduler.jobs import create_daily_report_job
            
            if task_type == TaskType.DAILY_REPORT:
                # 手动触发日报生成
                task_id = f"manual_daily_report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                scheduler.add_job(
                    create_daily_report_job,
                    'date',
                    run_date=datetime.now() + timedelta(seconds=5),  # 5秒后执行
                    args=[user_id],
                    id=task_id,
                    name=f"Manual Daily Report for User {user_id}"
                )
                
                logger.info("Manual daily report task scheduled", user_id=user_id, task_id=task_id)
                return task_id
            
            else:
                logger.warning("Unsupported task type for manual trigger", task_type=task_type)
                return None
                
        except Exception as e:
            logger.error("Failed to trigger user task", user_id=user_id, task_type=task_type, error=str(e))
            return None
    
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
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        try:
            status = get_scheduler_status()
            jobs = get_active_jobs()
            
            return {
                "scheduler": status,
                "active_jobs": jobs,
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error("Failed to get scheduler status", error=str(e))
            return {
                "scheduler": {"running": False, "error": str(e)},
                "active_jobs": [],
                "timestamp": datetime.utcnow()
            }
    
    async def disable_user_schedule(self, db: Session, user_id: str) -> bool:
        """禁用用户的定时任务"""
        try:
            # 更新数据库偏好设置
            schedule_pref = db.query(UserPreference).filter(
                UserPreference.user_id == user_id,
                UserPreference.preference_type == "schedule"
            ).first()
            
            if schedule_pref:
                schedule_pref.is_active = False
                schedule_pref.auto_sync_enabled = False
                db.commit()
            
            # 移除调度任务
            remove_user_jobs(user_id)
            
            logger.info("User schedule disabled", user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to disable user schedule", user_id=user_id, error=str(e))
            db.rollback()
            return False

# 创建全局实例
task_service = TaskService()