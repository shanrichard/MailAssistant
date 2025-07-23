"""
带心跳机制的后台同步服务
基于专家建议实现精确监控
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging
from sqlalchemy.orm import Session
from sqlalchemy import update

from ..models.user_sync_status import UserSyncStatus
from ..models.user import User
from ..services.email_sync_service import email_sync_service
from ..core.database import SessionLocal
from ..core.logging import get_logger
from .idempotent_sync_service import release_sync_status_atomic

logger = get_logger(__name__)

HEARTBEAT_INTERVAL = 15  # 心跳间隔15秒


async def execute_background_sync_with_heartbeat(user_id: str, force_full: bool, task_id: str):
    """带心跳机制的后台同步执行器"""
    try:
        logger.info(f"开始执行带心跳的后台同步", extra={"task_id": task_id, "user_id": user_id})
    except Exception as e:
        logger.error(f"记录日志时出错: {e}", extra={"task_id": task_id})
    
    async def heartbeat_worker():
        """心跳工作线程"""
        db = SessionLocal()
        try:
            while True:
                try:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)
                    
                    # 更新心跳时间戳
                    logger.info(f"更新心跳", extra={"task_id": task_id})
                    result = db.execute(
                        update(UserSyncStatus)
                        .where(UserSyncStatus.task_id == task_id)
                        .values(updated_at=datetime.utcnow())
                    )
                    db.commit()
                    
                    if result.rowcount == 0:
                        logger.warning(f"心跳更新失败，任务可能已被清理: {task_id}")
                        break
                        
                except Exception as e:
                    logger.error(f"心跳更新异常: {e}", extra={"task_id": task_id})
                    break
        except asyncio.CancelledError:
            logger.info(f"心跳任务被取消: {task_id}")
            raise
        finally:
            db.close()

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(heartbeat_worker())
    
    db = SessionLocal()
    try:
        # 执行实际的同步逻辑
        await execute_actual_sync(user_id, force_full, task_id, db)
        
    except Exception as e:
        logger.error(f"同步任务执行失败: {e}", extra={"task_id": task_id})
        raise
        
    finally:
        # 确保心跳任务被取消
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
            
        # 释放同步状态
        release_sync_status_atomic(db, user_id, task_id)
        db.close()


async def execute_actual_sync(user_id: str, force_full: bool, task_id: str, db: Session):
    """实际执行同步的核心逻辑"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"用户不存在: {user_id}")
            
        # 定义进度回调
        def progress_callback(progress_info):
            try:
                db.execute(
                    update(UserSyncStatus)
                    .where(UserSyncStatus.task_id == task_id)
                    .values(
                        progress_percentage=progress_info.get('progress_percentage', 0),
                        current_stats=progress_info.get('current_stats', {}),
                        updated_at=datetime.utcnow()
                    )
                )
                db.commit()
            except Exception as e:
                logger.error(f"进度更新失败: {e}", extra={"task_id": task_id})
        
        # 执行智能同步
        result = await email_sync_service.smart_sync_user_emails(
            db, user, force_full, progress_callback=progress_callback
        )
        
        # 标记完成
        db.execute(
            update(UserSyncStatus)
            .where(UserSyncStatus.task_id == task_id)
            .values(
                is_syncing=False,
                progress_percentage=100,
                current_stats=result,
                updated_at=datetime.utcnow()
            )
        )
        db.commit()
        
        logger.info(f"同步任务完成", extra={"task_id": task_id, "stats": result})
        
    except Exception as e:
        # 记录错误但不释放状态（由finally块处理）
        logger.error(f"同步执行异常: {e}", extra={"task_id": task_id})
        raise


async def cleanup_zombie_tasks_by_heartbeat():
    """基于心跳的僵死任务清理"""
    HEARTBEAT_TIMEOUT = 60  # 心跳超时时间（2个心跳周期）
    
    logger.info("Starting zombie task cleanup...")
    
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT)
        
        # 查找僵死任务：正在同步但心跳超时
        zombie_tasks = db.query(UserSyncStatus).filter(
            UserSyncStatus.is_syncing == True,
            UserSyncStatus.updated_at < cutoff_time
        ).all()
        
        cleaned_count = 0
        for task in zombie_tasks:
            logger.warning(
                f"检测到僵死任务，自动清理: {task.task_id}",
                extra={
                    "user_id": task.user_id,
                    "last_update": task.updated_at,
                    "minutes_silent": (datetime.utcnow() - task.updated_at).total_seconds() / 60
                }
            )
            
            # 原子性清理
            release_sync_status_atomic(
                db,
                task.user_id,
                task.task_id,
                f"任务心跳超时，自动清理于 {datetime.utcnow()}"
            )
            cleaned_count += 1
            
        if zombie_tasks:
            logger.info(f"自动清理了 {len(zombie_tasks)} 个僵死任务")
        else:
            logger.info("No zombie tasks found in this cleanup cycle")
            
        logger.info(f"Zombie task cleanup completed. Cleaned {cleaned_count} tasks")
        
        # 返回清理结果供调度器记录
        return {"cleaned_count": cleaned_count, "timestamp": datetime.utcnow()}
        
    except Exception as e:
        logger.error(f"僵死任务清理失败: {e}")
        return {"cleaned_count": 0, "timestamp": datetime.utcnow(), "error": str(e)}
    finally:
        db.close()


def get_sync_health_status() -> dict:
    """获取同步系统健康状态"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        
        # 统计各种状态的任务
        total_users = db.query(UserSyncStatus).count()
        active_syncs = db.query(UserSyncStatus).filter(
            UserSyncStatus.is_syncing == True
        ).count()
        
        # 检测僵死任务（心跳超时）
        heartbeat_timeout = now - timedelta(seconds=60)
        zombie_tasks = db.query(UserSyncStatus).filter(
            UserSyncStatus.is_syncing == True,
            UserSyncStatus.updated_at < heartbeat_timeout
        ).all()
        
        # 检测数据一致性问题
        inconsistent_tasks = db.query(UserSyncStatus).filter(
            ~(
                (UserSyncStatus.is_syncing == True) & 
                (UserSyncStatus.progress_percentage.between(0, 99))
                | 
                (UserSyncStatus.is_syncing == False) & 
                (UserSyncStatus.progress_percentage.in_([0, 100]))
            )
        ).count()
        
        # 统计最近完成的同步
        recent_cutoff = now - timedelta(hours=1)
        recent_syncs = db.query(UserSyncStatus).filter(
            UserSyncStatus.updated_at > recent_cutoff,
            UserSyncStatus.is_syncing == False,
            UserSyncStatus.progress_percentage == 100
        ).count()
        
        health_status = {
            "healthy": len(zombie_tasks) == 0 and inconsistent_tasks == 0,
            "timestamp": now.isoformat(),
            "statistics": {
                "total_users": total_users,
                "active_syncs": active_syncs,
                "zombie_tasks": len(zombie_tasks),
                "inconsistent_tasks": inconsistent_tasks,
                "recent_completed_syncs": recent_syncs
            },
            "zombie_task_details": [
                {
                    "task_id": task.task_id,
                    "user_id": str(task.user_id),
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "last_update": task.updated_at.isoformat(),
                    "silent_minutes": int((now - task.updated_at).total_seconds() / 60)
                }
                for task in zombie_tasks[:5]  # 只显示前5个
            ]
        }
        
        if not health_status["healthy"]:
            logger.warning("同步系统健康检查发现问题", extra={"health_data": health_status})
            
        return health_status
        
    except Exception as e:
        error_response = {
            "healthy": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
        logger.error("健康检查执行失败", extra={"error_data": error_response})
        return error_response
    finally:
        db.close()
