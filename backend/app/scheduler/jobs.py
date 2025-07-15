"""
Scheduled job definitions for MailAssistant
"""
import asyncio
from datetime import datetime, timedelta, time
from typing import Optional, List
import pytz
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.logging import get_logger
from ..models.user import User
from ..models.user_preference import UserPreference
from ..models.task_log import TaskLog, TaskStatus, TaskType
from ..services.gmail_service import gmail_service
from ..services.email_sync_service import email_sync_service
from .scheduler_app import scheduler

logger = get_logger(__name__)

async def setup_user_jobs(user_id: str):
    """为用户设置个性化定时任务"""
    try:
        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            logger.error("User not found", user_id=user_id)
            return
            
        # 获取用户的调度偏好
        schedule_pref = db.query(UserPreference).filter(
            UserPreference.user_id == user_id,
            UserPreference.preference_type == "schedule",
            UserPreference.is_active == True
        ).first()
        
        # 使用默认设置或用户偏好
        daily_time = time(9, 0)  # 默认09:00
        timezone_str = "Asia/Shanghai"  # 默认时区
        
        if schedule_pref:
            if schedule_pref.daily_report_time:
                daily_time = schedule_pref.daily_report_time
            if schedule_pref.timezone:
                timezone_str = schedule_pref.timezone
                
        # 创建用户的日报任务
        job_id = f"daily_report_{user_id}"
        scheduler.add_job(
            create_daily_report_job,
            'cron',
            hour=daily_time.hour,
            minute=daily_time.minute,
            timezone=timezone_str,
            args=[user_id],
            id=job_id,
            replace_existing=True,
            name=f"Daily Report for User {user.email}"
        )
        
        logger.info(
            "User daily job scheduled",
            user_id=user_id,
            time=daily_time.strftime("%H:%M"),
            timezone=timezone_str
        )
        
        db.close()
        
    except Exception as e:
        logger.error("Failed to setup user jobs", user_id=user_id, error=str(e))
        raise

async def create_daily_report_job(user_id: str):
    """执行用户日报生成任务"""
    task_unique_key = f"daily_report_{user_id}_{datetime.now().strftime('%Y-%m-%d')}"
    
    try:
        db = next(get_db())
        
        # 幂等性检查
        existing_task = db.query(TaskLog).filter(
            TaskLog.task_unique_key == task_unique_key,
            TaskLog.status.in_([TaskStatus.COMPLETED, TaskStatus.RUNNING])
        ).first()
        
        if existing_task:
            logger.info("Daily report task already processed", user_id=user_id, task_id=existing_task.id)
            db.close()
            return
            
        # 创建任务记录
        task_log = TaskLog(
            user_id=user_id,
            task_type=TaskType.DAILY_REPORT,
            task_name="Daily Email Report",
            task_description="Generate daily email analysis and report",
            status=TaskStatus.RUNNING,
            task_unique_key=task_unique_key,
            scheduler_job_id=f"daily_report_{user_id}",
            started_at=datetime.utcnow(),
            input_parameters={"user_id": user_id, "date": datetime.now().strftime('%Y-%m-%d')}
        )
        
        db.add(task_log)
        db.commit()
        
        logger.info("Starting daily report generation", user_id=user_id, task_id=task_log.id)
        
        # 执行邮件同步
        sync_stats = await email_sync_service.sync_user_emails(db, user_id, days=1)
        
        # 更新任务进度
        task_log.progress_percentage = 50
        task_log.emails_processed = sync_stats.get('fetched', 0)
        db.commit()
        
        # TODO: 这里后续会集成LangGraph Agent进行邮件分析
        # 目前先完成同步功能
        
        # 完成任务
        task_log.status = TaskStatus.COMPLETED
        task_log.completed_at = datetime.utcnow()
        task_log.execution_time_ms = int((task_log.completed_at - task_log.started_at).total_seconds() * 1000)
        task_log.progress_percentage = 100
        task_log.output_results = {
            "sync_stats": sync_stats,
            "status": "completed",
            "message": "Daily report generated successfully"
        }
        
        db.commit()
        db.close()
        
        logger.info(
            "Daily report completed successfully",
            user_id=user_id,
            task_id=task_log.id,
            emails_processed=sync_stats.get('fetched', 0)
        )
        
    except Exception as e:
        logger.error("Daily report job failed", user_id=user_id, error=str(e))
        
        # 更新任务状态为失败
        try:
            db = next(get_db())
            task_log = db.query(TaskLog).filter(
                TaskLog.task_unique_key == task_unique_key
            ).first()
            
            if task_log:
                task_log.status = TaskStatus.FAILED
                task_log.error_message = str(e)
                task_log.completed_at = datetime.utcnow()
                
                # 设置重试逻辑
                if task_log.retry_count < task_log.max_retries:
                    task_log.retry_count += 1
                    task_log.next_retry_at = datetime.utcnow() + timedelta(minutes=30)
                    task_log.status = TaskStatus.RETRYING
                    
                    # 安排重试任务
                    scheduler.add_job(
                        create_daily_report_job,
                        'date',
                        run_date=task_log.next_retry_at,
                        args=[user_id],
                        id=f"retry_daily_report_{user_id}_{task_log.retry_count}",
                        replace_existing=True
                    )
                    
                    logger.info(
                        "Scheduled retry for daily report",
                        user_id=user_id,
                        retry_count=task_log.retry_count,
                        next_retry=task_log.next_retry_at
                    )
                
                db.commit()
            
            db.close()
            
        except Exception as retry_error:
            logger.error("Failed to handle retry logic", error=str(retry_error))
        
        raise

async def create_token_refresh_job():
    """检查和刷新用户令牌"""
    try:
        db = next(get_db())
        
        # 获取所有有Gmail令牌的用户
        users = db.query(User).filter(User._encrypted_gmail_tokens.isnot(None)).all()
        
        logger.info(f"Checking tokens for {len(users)} users")
        
        for user in users:
            try:
                # 检查令牌是否需要刷新
                from ..services.oauth_service import oauth_token_manager
                
                refreshed_tokens, was_refreshed = oauth_token_manager.refresh_token_if_needed(
                    user._encrypted_gmail_tokens
                )
                
                if was_refreshed:
                    user._encrypted_gmail_tokens = refreshed_tokens
                    db.commit()
                    
                    logger.info("Token refreshed successfully", user_id=str(user.id))
                    
                    # 记录令牌刷新任务
                    task_log = TaskLog(
                        user_id=user.id,
                        task_type=TaskType.TOKEN_REFRESH,
                        task_name="Token Refresh",
                        task_description="Automatic Gmail token refresh",
                        status=TaskStatus.COMPLETED,
                        task_unique_key=f"token_refresh_{user.id}_{datetime.now().strftime('%Y-%m-%d_%H')}",
                        completed_at=datetime.utcnow(),
                        output_results={"status": "refreshed"}
                    )
                    db.add(task_log)
                    
            except Exception as user_error:
                logger.error("Token refresh failed for user", user_id=str(user.id), error=str(user_error))
                
                # 记录失败的令牌刷新
                task_log = TaskLog(
                    user_id=user.id,
                    task_type=TaskType.TOKEN_REFRESH,
                    task_name="Token Refresh",
                    task_description="Automatic Gmail token refresh",
                    status=TaskStatus.FAILED,
                    task_unique_key=f"token_refresh_{user.id}_{datetime.now().strftime('%Y-%m-%d_%H')}",
                    error_message=str(user_error),
                    completed_at=datetime.utcnow()
                )
                db.add(task_log)
        
        db.commit()
        db.close()
        
        logger.info("Token refresh job completed")
        
    except Exception as e:
        logger.error("Token refresh job failed", error=str(e))
        raise

async def create_cleanup_job():
    """清理旧的任务日志和临时数据"""
    try:
        db = next(get_db())
        
        # 删除30天前的已完成任务日志
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        deleted_count = db.query(TaskLog).filter(
            TaskLog.created_at < cutoff_date,
            TaskLog.status.in_([TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED])
        ).delete()
        
        db.commit()
        db.close()
        
        logger.info(f"Cleanup job completed, deleted {deleted_count} old task logs")
        
        # 记录清理任务
        task_log = TaskLog(
            task_type=TaskType.CLEANUP,
            task_name="System Cleanup",
            task_description="Clean up old task logs and temporary data",
            status=TaskStatus.COMPLETED,
            task_unique_key=f"cleanup_{datetime.now().strftime('%Y-%m-%d')}",
            completed_at=datetime.utcnow(),
            output_results={"deleted_logs": deleted_count}
        )
        
        db = next(get_db())
        db.add(task_log)
        db.commit()
        db.close()
        
    except Exception as e:
        logger.error("Cleanup job failed", error=str(e))
        raise

def remove_user_jobs(user_id: str):
    """移除用户的定时任务"""
    try:
        job_id = f"daily_report_{user_id}"
        scheduler.remove_job(job_id)
        logger.info("User jobs removed", user_id=user_id)
    except Exception as e:
        logger.error("Failed to remove user jobs", user_id=user_id, error=str(e))

def update_user_schedule(user_id: str, daily_time: time, timezone_str: str):
    """更新用户的任务调度时间"""
    try:
        # 移除旧任务
        remove_user_jobs(user_id)
        
        # 创建新任务
        asyncio.create_task(setup_user_jobs(user_id))
        
        logger.info(
            "User schedule updated",
            user_id=user_id,
            time=daily_time.strftime("%H:%M"),
            timezone=timezone_str
        )
        
    except Exception as e:
        logger.error("Failed to update user schedule", user_id=user_id, error=str(e))
        raise