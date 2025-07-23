"""
幂等同步启动服务
基于专家建议实现
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import update

from ..models.user_sync_status import UserSyncStatus
from ..models.user import User
from ..core.logging import get_logger

logger = get_logger(__name__)


def start_sync_idempotent(db: Session, user_id: str, force_full: bool) -> str:
    """
    幂等的同步启动接口
    - 如果存在有效的进行中任务（<30分钟），则复用现有task_id
    - 否则，清理旧状态并创建新任务
    - 使用行锁保证并发安全
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        force_full: 是否强制全量同步
        
    Returns:
        str: 任务ID（新创建或复用的）
    """
    # 确保数据库会话没有活动事务
    if db.in_transaction():
        db.rollback()
    
    try:
        # 开始新事务
        db.begin()
        
        # 使用行锁获取用户同步状态
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user_id
        ).with_for_update().first()

        from app.utils.datetime_utils import utc_now, safe_datetime_diff
        
        now = utc_now()
        
        # 检查是否存在有效的进行中任务
        if (sync_status and 
            sync_status.is_syncing and 
            sync_status.started_at):
            
            time_diff = safe_datetime_diff(now, sync_status.started_at)
            if time_diff and time_diff < timedelta(minutes=30):
                task_id = sync_status.task_id
                db.commit()  # 显式提交事务
                
                logger.info(f"复用现有同步任务: {task_id}", 
                           extra={"user_id": user_id, "task_id": task_id})
                return task_id  # 复用老任务，避免重复
        
        # 创建新任务
        new_task_id = f"sync_{user_id}_{uuid.uuid4().hex[:8]}_{int(now.timestamp())}"
        
        if sync_status:
            # 更新现有记录
            sync_status.task_id = new_task_id
            sync_status.is_syncing = True
            sync_status.sync_type = 'full' if force_full else 'incremental'
            sync_status.started_at = now
            sync_status.updated_at = now
            sync_status.progress_percentage = 0
            sync_status.current_stats = {}
            sync_status.error_message = None
        else:
            # 创建新记录
            sync_status = UserSyncStatus(
                user_id=user_id,
                task_id=new_task_id,
                is_syncing=True,
                sync_type='full' if force_full else 'incremental',
                started_at=now,
                updated_at=now,
                progress_percentage=0,
                current_stats={}
            )
            db.add(sync_status)
        
        # 显式提交事务
        db.commit()
        
        # 事务提交后记录日志
        logger.info(f"启动新同步任务: {new_task_id}", 
                   extra={"user_id": user_id, "force_full": force_full, "task_id": new_task_id})
        return new_task_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"幂等同步启动失败: {e}", extra={"user_id": user_id})
        raise


def release_sync_status_atomic(db: Session, user_id: str, task_id: str, error_message: Optional[str] = None):
    """
    原子性释放同步状态
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        task_id: 任务ID
        error_message: 错误信息（如果有）
    """
    from app.utils.datetime_utils import utc_now
    
    try:
        with db.begin():
            updates = {
                'is_syncing': False,
                'updated_at': utc_now()
            }
            if error_message:
                updates['error_message'] = error_message
                updates['progress_percentage'] = 0  # 错误时重置进度
                
            db.execute(
                update(UserSyncStatus)
                .where(UserSyncStatus.task_id == task_id)
                .values(**updates)
            )
            
        logger.info(f"状态已释放", 
                   extra={"user_id": user_id, "task_id": task_id, "error": error_message})
            
    except Exception as e:
        logger.error(f"状态释放失败: {e}", 
                    extra={"user_id": user_id, "task_id": task_id})
        raise


def get_active_task_info(db: Session, user_id: str) -> Optional[dict]:
    """
    获取用户当前活跃任务信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        dict: 活跃任务信息，如果没有则返回None
    """
    from app.utils.datetime_utils import utc_now, safe_datetime_diff
    
    sync_status = db.query(UserSyncStatus).filter(
        UserSyncStatus.user_id == user_id,
        UserSyncStatus.is_syncing == True
    ).first()
    
    if not sync_status:
        return None
        
    now = utc_now()
    
    # 检查任务是否还有效（30分钟内）
    time_diff = safe_datetime_diff(now, sync_status.started_at) if sync_status.started_at else None
    if time_diff and time_diff < timedelta(minutes=30):
        return {
            "task_id": sync_status.task_id,
            "sync_type": sync_status.sync_type,
            "started_at": sync_status.started_at,
            "progress_percentage": sync_status.progress_percentage,
            "current_stats": sync_status.current_stats or {},
            "is_active": True
        }
    
    return {
        "task_id": sync_status.task_id,
        "is_active": False,
        "expired": True
    }
