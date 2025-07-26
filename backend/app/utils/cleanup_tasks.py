"""
Cleanup Tasks
定期清理任务
"""
import asyncio
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.logging import get_logger
from .report_state_manager import ReportStateManager

logger = get_logger(__name__)


class CleanupTasks:
    """清理任务管理器"""
    
    def __init__(self):
        self.is_running = False
        self._task = None
    
    async def start(self):
        """启动清理任务"""
        if self.is_running:
            logger.warning("Cleanup tasks already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._run_cleanup_loop())
        logger.info("Cleanup tasks started")
    
    async def stop(self):
        """停止清理任务"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Cleanup tasks stopped")
    
    async def _run_cleanup_loop(self):
        """运行清理循环"""
        while self.is_running:
            try:
                await self._perform_cleanup()
                # 每小时运行一次
                await asyncio.sleep(3600)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
                # 出错后等待5分钟再试
                await asyncio.sleep(300)
    
    async def _perform_cleanup(self):
        """执行清理任务"""
        db = SessionLocal()
        try:
            logger.info("Starting cleanup tasks")
            
            # 1. 清理过期的日报（保留7天）
            stale_reports = ReportStateManager.cleanup_stale_reports(db, days=7)
            logger.info(f"Cleaned up {stale_reports} stale reports")
            
            # 2. 检查并处理超时的报告
            from ..models.daily_report_log import DailyReportLog
            
            # 查找所有正在处理中的报告
            processing_reports = db.query(DailyReportLog).filter(
                DailyReportLog.status == 'processing'
            ).all()
            
            timeout_count = 0
            for report in processing_reports:
                if ReportStateManager.check_timeout(report):
                    ReportStateManager.handle_timeout(db, report)
                    timeout_count += 1
            
            if timeout_count > 0:
                logger.info(f"Marked {timeout_count} reports as failed due to timeout")
            
            # 3. 清理孤立的用户同步状态（用户已删除但状态还在）
            from ..models.user_sync_status import UserSyncStatus
            from ..models.user import User
            
            # 查找没有对应用户的同步状态
            orphan_statuses = db.query(UserSyncStatus).outerjoin(
                User, UserSyncStatus.user_id == User.id
            ).filter(User.id.is_(None)).all()
            
            for status in orphan_statuses:
                db.delete(status)
            
            if orphan_statuses:
                db.commit()
                logger.info(f"Cleaned up {len(orphan_statuses)} orphan sync statuses")
            
            logger.info("Cleanup tasks completed successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def force_cleanup(self):
        """强制执行一次清理（用于测试或手动触发）"""
        await self._perform_cleanup()


# 全局清理任务实例
cleanup_manager = CleanupTasks()