"""
监控工具类
提供系统监控和自愈功能
"""
import os
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..models.user_sync_status import UserSyncStatus
from ..core.database import SessionLocal
from ..core.logging import get_logger
from ..services.heartbeat_sync_service import cleanup_zombie_tasks_by_heartbeat

logger = get_logger(__name__)


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # CPU和内存使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds()
            }
        except Exception as e:
            logger.error(f"获取系统指标失败: {e}")
            return {"error": str(e)}
    
    def check_resource_usage(self) -> Dict[str, Any]:
        """检查资源使用情况并给出建议"""
        metrics = self.get_system_metrics()
        warnings = []
        recommendations = []
        
        # CPU检查
        cpu = metrics.get("cpu_percent", 0)
        if cpu > 80:
            warnings.append(f"CPU使用率过高: {cpu:.1f}%")
            recommendations.append("检查是否有异常进程占用CPU")
        
        # 内存检查
        memory_percent = metrics.get("memory", {}).get("percent", 0)
        if memory_percent > 85:
            warnings.append(f"内存使用率过高: {memory_percent:.1f}%")
            recommendations.append("考虑重启应用释放内存")
        
        # 磁盘检查
        disk_percent = metrics.get("disk", {}).get("percent", 0)
        if disk_percent > 90:
            warnings.append(f"磁盘使用率过高: {disk_percent:.1f}%")
            recommendations.append("清理临时文件和日志")
        
        return {
            "healthy": len(warnings) == 0,
            "warnings": warnings,
            "recommendations": recommendations,
            "metrics": metrics
        }


class SyncMonitor:
    """同步系统监控器"""
    
    @staticmethod
    def analyze_sync_patterns(db: Session) -> Dict[str, Any]:
        """分析同步模式和趋势"""
        try:
            now = datetime.utcnow()
            
            # 获取最近24小时的同步记录
            recent_syncs = db.query(UserSyncStatus).filter(
                UserSyncStatus.updated_at > (now - timedelta(hours=24))
            ).all()
            
            # 按小时分组统计
            hourly_stats = {}
            success_count = 0
            failure_count = 0
            
            for sync in recent_syncs:
                hour = sync.updated_at.replace(minute=0, second=0, microsecond=0)
                hour_key = hour.isoformat()
                
                if hour_key not in hourly_stats:
                    hourly_stats[hour_key] = {"total": 0, "success": 0, "failure": 0}
                
                hourly_stats[hour_key]["total"] += 1
                
                if sync.error_message:
                    hourly_stats[hour_key]["failure"] += 1
                    failure_count += 1
                elif sync.progress_percentage == 100:
                    hourly_stats[hour_key]["success"] += 1
                    success_count += 1
            
            # 成功率计算
            total_completed = success_count + failure_count
            success_rate = (success_count / total_completed * 100) if total_completed > 0 else 100
            
            # 趋势分析
            trends = []
            if success_rate < 80:
                trends.append("同步成功率偏低，需要关注")
            if failure_count > success_count:
                trends.append("失败次数超过成功次数，系统可能存在问题")
            
            return {
                "analysis_period": "24小时",
                "total_syncs": len(recent_syncs),
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": round(success_rate, 2),
                "hourly_distribution": hourly_stats,
                "trends": trends,
                "timestamp": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"同步模式分析失败: {e}")
            return {"error": str(e)}
    
    @staticmethod
    async def auto_heal_sync_issues() -> Dict[str, Any]:
        """自动修复同步问题"""
        actions_taken = []
        
        try:
            # 1. 清理僵死任务
            cleaned_count = await cleanup_zombie_tasks_by_heartbeat()
            if cleaned_count > 0:
                actions_taken.append(f"清理了 {cleaned_count} 个僵死任务")
            
            # 2. 检查数据一致性（这里可以加入更多修复逻辑）
            db = SessionLocal()
            try:
                inconsistent = db.query(UserSyncStatus).filter(
                    ~(
                        (UserSyncStatus.is_syncing == True) & 
                        (UserSyncStatus.progress_percentage.between(0, 99))
                        | 
                        (UserSyncStatus.is_syncing == False) & 
                        (UserSyncStatus.progress_percentage.in_([0, 100]))
                    )
                ).count()
                
                if inconsistent > 0:
                    actions_taken.append(f"检测到 {inconsistent} 个数据不一致记录，建议手动检查")
                
            finally:
                db.close()
            
            return {
                "auto_heal_completed": True,
                "actions_taken": actions_taken,
                "timestamp": datetime.utcnow().isoformat(),
                "next_check": (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"自动修复失败: {e}")
            return {
                "auto_heal_completed": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# 全局监控器实例
system_monitor = SystemMonitor()
sync_monitor = SyncMonitor()
