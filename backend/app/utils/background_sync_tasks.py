"""
Background Sync Tasks
后台同步任务管理器 - 解耦Gmail同步与用户操作
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..core.logging import get_logger
from ..services.email_sync_service import email_sync_service
from ..models.user import User

logger = get_logger(__name__)


class BackgroundSyncTasks:
    """后台同步任务管理器"""
    
    def __init__(self):
        self.is_running = False
        self._sync_task = None
        self._manual_sync_queue = asyncio.Queue()
        self._queue_task = None
    
    async def start(self):
        """启动后台同步任务"""
        if self.is_running:
            logger.warning("Background sync tasks already running")
            return
        
        self.is_running = True
        # 启动定期同步任务
        self._sync_task = asyncio.create_task(self._run_sync_loop())
        # 启动手动同步队列处理器
        self._queue_task = asyncio.create_task(self._process_manual_sync_queue())
        logger.info("Background sync tasks started")
    
    async def stop(self):
        """停止后台同步任务"""
        self.is_running = False
        
        # 停止定期同步
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        # 停止队列处理
        if self._queue_task:
            self._queue_task.cancel()
            try:
                await self._queue_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Background sync tasks stopped")
    
    async def _run_sync_loop(self):
        """定期同步循环"""
        while self.is_running:
            try:
                await self._perform_auto_sync()
                # 每30分钟自动同步一次
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Error in auto sync loop: {e}", exc_info=True)
                # 出错后等待5分钟再试
                await asyncio.sleep(300)
    
    async def _perform_auto_sync(self):
        """执行自动同步"""
        db = SessionLocal()
        try:
            logger.info("Starting auto sync for all active users")
            
            # 获取所有活跃用户
            active_users = db.query(User).filter(User.is_active == True).all()
            
            sync_count = 0
            error_count = 0
            
            for user in active_users:
                try:
                    # 使用优化的智能增量同步
                    stats = email_sync_service.smart_sync_user_emails_optimized(db, user)
                    logger.info(f"Auto sync completed for user {user.id}: {stats}")
                    sync_count += 1
                except Exception as e:
                    logger.error(f"Auto sync failed for user {user.id}: {e}")
                    error_count += 1
            
            logger.info(f"Auto sync completed: {sync_count} users synced, {error_count} errors")
            
        except Exception as e:
            logger.error(f"Error in auto sync: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def request_manual_sync(self, user_id: str, sync_type: str):
        """请求手动同步（非阻塞）"""
        sync_request = {
            'user_id': user_id,
            'sync_type': sync_type,
            'requested_at': datetime.now(timezone.utc).isoformat()
        }
        await self._manual_sync_queue.put(sync_request)
        logger.info(f"Manual sync requested: user_id={user_id}, sync_type={sync_type}")
    
    async def _process_manual_sync_queue(self):
        """处理手动同步队列"""
        while self.is_running:
            try:
                # 等待队列中的同步请求
                sync_request = await self._manual_sync_queue.get()
                await self._execute_manual_sync(sync_request)
                self._manual_sync_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing manual sync queue: {e}", exc_info=True)
                # 短暂延迟后继续处理队列
                await asyncio.sleep(1)
    
    async def _execute_manual_sync(self, sync_request: Dict[str, Any]):
        """执行手动同步请求"""
        db = SessionLocal()
        try:
            user_id = sync_request['user_id']
            sync_type = sync_request['sync_type']
            
            logger.info(f"Executing manual sync: {sync_request}")
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for manual sync")
                return
            
            # 根据同步类型执行相应的同步
            if sync_type == 'today':
                stats = email_sync_service.sync_emails_by_timerange(db, user, "today", 500)
            elif sync_type == 'week':
                stats = email_sync_service.sync_emails_by_timerange(db, user, "week", 500)  
            elif sync_type == 'month':
                stats = email_sync_service.sync_emails_by_timerange(db, user, "month", 500)
            else:
                logger.error(f"Unknown sync type: {sync_type}")
                return
            
            logger.info(f"Manual sync {sync_type} completed for user {user_id}: {stats}")
            
        except Exception as e:
            logger.error(f"Manual sync execution failed for user {sync_request.get('user_id')}: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态（用于监控和调试）"""
        return {
            "is_running": self.is_running,
            "queue_size": self._manual_sync_queue.qsize(),
            "auto_sync_active": self._sync_task and not self._sync_task.done(),
            "queue_processor_active": self._queue_task and not self._queue_task.done()
        }


# 全局后台同步任务实例
background_sync_tasks = BackgroundSyncTasks()