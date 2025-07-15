"""
APScheduler configuration for MailAssistant
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from sqlalchemy import create_engine

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# APScheduler配置
jobstores = {
    'default': SQLAlchemyJobStore(url=settings.database_url)
}

executors = {
    'default': AsyncIOExecutor()
}

job_defaults = {
    'coalesce': False,  # 不合并多个相同任务
    'max_instances': 1,  # 同一任务最多同时运行1个实例
    'misfire_grace_time': 3600  # 错过执行时间1小时内仍然执行
}

# 创建调度器实例
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC'  # 使用UTC时间，用户时区在任务内部处理
)

def job_listener(event):
    """任务执行事件监听器"""
    if event.exception:
        logger.error(
            "Job execution failed",
            job_id=event.job_id,
            exception=str(event.exception),
            traceback=event.traceback
        )
    else:
        logger.info(
            "Job executed successfully", 
            job_id=event.job_id,
            return_value=event.retval
        )

# 添加事件监听器
scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

async def start_scheduler():
    """启动调度器"""
    try:
        if not scheduler.running:
            scheduler.start()
            logger.info("Task scheduler started successfully")
            
            # 设置系统级定时任务
            await setup_system_jobs()
        else:
            logger.warning("Task scheduler is already running")
    except Exception as e:
        logger.error("Failed to start task scheduler", error=str(e))
        raise

async def stop_scheduler():
    """停止调度器"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=True)
            logger.info("Task scheduler stopped successfully")
        else:
            logger.warning("Task scheduler is not running")
    except Exception as e:
        logger.error("Failed to stop task scheduler", error=str(e))
        raise

async def setup_system_jobs():
    """设置系统级定时任务"""
    from .jobs import create_token_refresh_job, create_cleanup_job
    
    # 令牌健康检查任务（每2小时）
    scheduler.add_job(
        create_token_refresh_job,
        'interval',
        hours=2,
        id='system_token_refresh',
        replace_existing=True,
        name='System Token Refresh Check'
    )
    
    # 日志清理任务（每日凌晨2点）
    scheduler.add_job(
        create_cleanup_job,
        'cron',
        hour=2,
        minute=0,
        id='system_cleanup',
        replace_existing=True,
        name='System Cleanup Task'
    )
    
    logger.info("System jobs scheduled successfully")

def get_scheduler_status():
    """获取调度器状态"""
    return {
        "running": scheduler.running,
        "jobs_count": len(scheduler.get_jobs()),
        "executors": list(scheduler._executors.keys()),
        "jobstores": list(scheduler._jobstores.keys())
    }

def get_active_jobs():
    """获取活跃任务列表"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "func": str(job.func),
            "trigger": str(job.trigger),
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "misfire_grace_time": job.misfire_grace_time,
            "max_instances": job.max_instances
        })
    return jobs