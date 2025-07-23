"""
增强版健康检查API
提供详细的系统状态监控
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.user_sync_status import UserSyncStatus
from ..services.heartbeat_sync_service import get_sync_health_status, cleanup_zombie_tasks_by_heartbeat
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/sync")
async def sync_system_health():
    """同步系统健康检查 - 增强版"""
    try:
        health_status = get_sync_health_status()
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.post("/sync/cleanup")
async def manual_cleanup_zombie_tasks():
    """手动清理僵死任务"""
    try:
        cleaned_count = await cleanup_zombie_tasks_by_heartbeat()
        
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"成功清理 {cleaned_count} 个僵死任务",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"手动清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/sync/detailed")
async def detailed_sync_status(db: Session = Depends(get_db)):
    """详细的同步状态信息"""
    try:
        now = datetime.utcnow()
        
        # 获取所有同步状态记录
        all_syncs = db.query(UserSyncStatus).all()
        
        # 分类统计
        running_syncs = [s for s in all_syncs if s.is_syncing]
        completed_syncs = [s for s in all_syncs if not s.is_syncing and s.progress_percentage == 100]
        failed_syncs = [s for s in all_syncs if not s.is_syncing and s.error_message]
        
        # 检测超时任务
        timeout_threshold = now - timedelta(minutes=30)
        long_running = [s for s in running_syncs if s.started_at and s.started_at < timeout_threshold]
        
        # 检测心跳超时任务
        heartbeat_timeout = now - timedelta(seconds=60)
        heartbeat_expired = [s for s in running_syncs if s.updated_at < heartbeat_timeout]
        
        return {
            "timestamp": now.isoformat(),
            "summary": {
                "total_records": len(all_syncs),
                "running_syncs": len(running_syncs),
                "completed_syncs": len(completed_syncs),
                "failed_syncs": len(failed_syncs),
                "long_running": len(long_running),
                "heartbeat_expired": len(heartbeat_expired)
            },
            "running_tasks": [
                {
                    "task_id": s.task_id,
                    "user_id": str(s.user_id),
                    "sync_type": s.sync_type,
                    "progress": s.progress_percentage,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "last_update": s.updated_at.isoformat(),
                    "minutes_running": int((now - s.started_at).total_seconds() / 60) if s.started_at else None,
                    "is_long_running": s in long_running,
                    "heartbeat_expired": s in heartbeat_expired
                }
                for s in running_syncs
            ],
            "recent_failures": [
                {
                    "task_id": s.task_id,
                    "user_id": str(s.user_id),
                    "error_message": s.error_message,
                    "failed_at": s.updated_at.isoformat(),
                    "minutes_ago": int((now - s.updated_at).total_seconds() / 60)
                }
                for s in sorted(failed_syncs, key=lambda x: x.updated_at, reverse=True)[:10]
            ]
        }
        
    except Exception as e:
        logger.error(f"获取详细状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/system")
async def system_overall_health():
    """系统整体健康状态"""
    try:
        # 获取同步系统健康状态
        sync_health = get_sync_health_status()
        
        # 系统整体评分
        health_score = 100
        issues = []
        
        if not sync_health.get("healthy", True):
            health_score -= 30
            issues.append("同步系统存在问题")
        
        if sync_health.get("statistics", {}).get("zombie_tasks", 0) > 0:
            health_score -= 20
            issues.append(f"检测到 {sync_health['statistics']['zombie_tasks']} 个僵死任务")
        
        if sync_health.get("statistics", {}).get("inconsistent_tasks", 0) > 0:
            health_score -= 15
            issues.append(f"检测到 {sync_health['statistics']['inconsistent_tasks']} 个数据不一致记录")
        
        # 运行时长检查（这里可以加入更多系统指标）
        uptime_hours = 24  # 假设系统运行24小时，实际应从系统获取
        if uptime_hours > 168:  # 超过一周
            health_score -= 5
            issues.append("系统已连续运行超过一周，建议重启")
        
        health_level = "excellent" if health_score >= 90 else                       "good" if health_score >= 70 else                       "warning" if health_score >= 50 else "critical"
        
        return {
            "health_score": health_score,
            "health_level": health_level,
            "timestamp": datetime.utcnow().isoformat(),
            "issues": issues,
            "sync_system": sync_health,
            "recommendations": [
                "定期监控健康检查接口",
                "设置自动化监控告警",
                "及时清理僵死任务",
                "保持系统更新"
            ] if health_score < 90 else ["系统运行良好"]
        }
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return {
            "health_score": 0,
            "health_level": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "issues": ["健康检查服务异常"]
        }
