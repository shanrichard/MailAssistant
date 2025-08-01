"""
Background Sync Tasks
后台同步任务管理器 - 解耦Gmail同步与用户操作
"""
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import SessionLocal
from ..core.logging import get_logger
from ..core.config import settings
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
                # 根据配置的小时数自动同步
                sync_interval_seconds = settings.auto_sync_interval_hours * 3600
                logger.info(f"Next auto sync in {settings.auto_sync_interval_hours} hours ({sync_interval_seconds} seconds)")
                await asyncio.sleep(sync_interval_seconds)
            except Exception as e:
                logger.error(f"Error in auto sync loop: {e}", exc_info=True)
                # 出错后等待5分钟再试
                await asyncio.sleep(300)
    
    async def _perform_auto_sync(self):
        """执行自动同步"""
        # 使用 PostgreSQL 咨询锁防止多进程重复执行
        # 锁ID: 987654321 (任意选择的唯一数字)
        SYNC_LOCK_ID = 987654321
        
        # 尝试获取咨询锁
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": SYNC_LOCK_ID})
            got_lock = result.scalar()
            
            if not got_lock:
                logger.info("Another process is already performing auto sync, skipping")
                return
            
            logger.info("Acquired sync lock, starting auto sync for all active users")
            
            sync_count = 0
            error_count = 0
            
            # 获取所有活跃用户ID
            active_user_ids = [user.id for user in db.query(User).filter(User.is_active == True).all()]
        finally:
            # 确保释放锁
            if 'got_lock' in locals() and got_lock:
                db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": SYNC_LOCK_ID})
                logger.info("Released sync lock")
            db.close()
        
        # 为每个用户创建独立的数据库会话
        for user_id in active_user_ids:
            user_db = SessionLocal()
            try:
                user = user_db.query(User).filter(User.id == user_id).first()
                if not user:
                    continue
                    
                # 使用优化的智能增量同步
                stats = email_sync_service.smart_sync_user_emails_optimized(user_db, user)
                logger.info(f"Auto sync completed for user {user.id}: {stats}")
                sync_count += 1
            except Exception as e:
                logger.error(f"Auto sync failed for user {user_id}: {e}")
                error_count += 1
                user_db.rollback()
            finally:
                user_db.close()
        
        logger.info(f"Auto sync completed: {sync_count} users synced, {error_count} errors")
    
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
        user_id = sync_request['user_id']
        sync_type = sync_request['sync_type']
        
        # 为每个用户生成唯一的锁ID（使用用户ID的哈希值）
        # 确保锁ID在合理范围内（PostgreSQL bigint）
        user_lock_id = abs(hash(user_id)) % 1000000000
        
        logger.info(f"Executing manual sync: {sync_request}")
        
        # 为每个同步请求创建独立的数据库会话
        db = SessionLocal()
        got_lock = False
        try:
            # 尝试获取用户级别的咨询锁
            result = db.execute(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": user_lock_id})
            got_lock = result.scalar()
            
            if not got_lock:
                logger.warning(f"Another sync is already running for user {user_id}, skipping")
                return
            
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for manual sync")
                return
            
            # 根据同步类型执行相应的同步
            # 使用新的分页同步方法，避免内存溢出
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
            logger.error(f"Manual sync execution failed for user {user_id}: {e}", exc_info=True)
            db.rollback()
        finally:
            # 释放用户级别的锁
            if got_lock:
                db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": user_lock_id})
                logger.info(f"Released sync lock for user {user_id}")
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