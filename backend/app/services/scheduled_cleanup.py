"""
定时清理任务服务
每2分钟检查并清理僵死任务
"""
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..core.logging import get_logger
from .heartbeat_sync_service import cleanup_zombie_tasks_by_heartbeat

logger = get_logger(__name__)

scheduler = None


def start_scheduler():
    """启动定时任务调度器"""
    global scheduler
    
    if scheduler and scheduler.running:
        logger.warning("调度器已在运行")
        return
    
    scheduler = AsyncIOScheduler()
    
    # 每2分钟清理一次僵死任务
    scheduler.add_job(
        scheduled_zombie_cleanup,
        trigger=IntervalTrigger(minutes=2),
        id='zombie_task_cleaner_v2',
        replace_existing=True
    )
    
    try:
        scheduler.start()
        logger.info("定时清理任务调度器已启动")
    except Exception as e:
        logger.error(f"启动调度器失败: {e}")


def stop_scheduler():
    """停止定时任务调度器"""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("定时清理任务调度器已停止")


async def scheduled_zombie_cleanup():
    """每2分钟清理一次僵死任务"""
    try:
        cleaned_count = await cleanup_zombie_tasks_by_heartbeat()
        if cleaned_count > 0:
            logger.info(f"定时清理完成，清理了 {cleaned_count} 个僵死任务")
    except Exception as e:
        logger.error(f"定时清理任务执行失败: {e}")


# 应用启动时自动启动调度器
def init_cleanup_scheduler():
    """初始化清理调度器"""
    start_scheduler()
