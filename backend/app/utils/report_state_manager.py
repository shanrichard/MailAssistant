"""
Report State Manager
日报状态管理器 - 处理并发控制和超时检查
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import asyncio
from contextlib import contextmanager

from ..models.daily_report_log import DailyReportLog
from ..core.logging import get_logger

logger = get_logger(__name__)


class ReportStateManager:
    """日报状态管理器"""
    
    TIMEOUT_SECONDS = 300  # 5分钟超时
    LOCK_TIMEOUT = 10  # 获取锁的超时时间
    
    @staticmethod
    def check_timeout(report: DailyReportLog) -> bool:
        """检查报告是否超时"""
        if report.status != 'processing':
            return False
            
        elapsed = (datetime.now(timezone.utc) - report.created_at).total_seconds()
        return elapsed > ReportStateManager.TIMEOUT_SECONDS
    
    @staticmethod
    def handle_timeout(db: Session, report: DailyReportLog) -> None:
        """处理超时的报告"""
        report.status = 'failed'
        report.report_content = {
            'error': 'Generation timeout',
            'timeout_at': datetime.now(timezone.utc).isoformat()
        }
        report.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.warning(f"Report {report.id} marked as failed due to timeout")
    
    @staticmethod
    @contextmanager
    def acquire_report_lock(db: Session, user_id: str, report_date: datetime.date):
        """获取报告生成锁（使用数据库唯一约束）"""
        new_report = DailyReportLog(
            user_id=user_id,
            report_date=report_date,
            status='processing',
            report_content={'locked_at': datetime.now(timezone.utc).isoformat()}
        )
        
        try:
            db.add(new_report)
            db.commit()
            # 成功获取锁
            yield new_report
        except IntegrityError:
            # 并发冲突，其他进程已经在处理
            db.rollback()
            yield None
    
    @staticmethod
    async def wait_for_completion(
        db: Session, 
        user_id: str, 
        report_date: datetime.date,
        max_wait: int = 30
    ) -> Optional[DailyReportLog]:
        """等待报告完成（用于并发请求）"""
        start_time = datetime.now(timezone.utc)
        
        while (datetime.now(timezone.utc) - start_time).total_seconds() < max_wait:
            report = db.query(DailyReportLog).filter(
                DailyReportLog.user_id == user_id,
                DailyReportLog.report_date == report_date
            ).first()
            
            if report and report.status in ['completed', 'failed']:
                return report
                
            await asyncio.sleep(1)
            db.commit()  # 刷新事务以获取最新数据
        
        return None
    
    @staticmethod
    def cleanup_stale_reports(db: Session, days: int = 7) -> int:
        """清理过期的报告"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        stale_reports = db.query(DailyReportLog).filter(
            DailyReportLog.created_at < cutoff_date
        ).all()
        
        count = len(stale_reports)
        for report in stale_reports:
            db.delete(report)
        
        db.commit()
        logger.info(f"Cleaned up {count} stale reports older than {days} days")
        return count
    
    @staticmethod
    def get_report_status(db: Session, user_id: str, report_date: datetime.date) -> Dict[str, Any]:
        """获取报告状态的详细信息"""
        report = db.query(DailyReportLog).filter(
            DailyReportLog.user_id == user_id,
            DailyReportLog.report_date == report_date
        ).first()
        
        if not report:
            return {
                'exists': False,
                'status': None,
                'message': 'No report found'
            }
        
        # 检查超时
        if ReportStateManager.check_timeout(report):
            ReportStateManager.handle_timeout(db, report)
        
        elapsed = (datetime.now(timezone.utc) - report.created_at).total_seconds()
        
        return {
            'exists': True,
            'status': report.status,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat(),
            'elapsed_seconds': elapsed,
            'is_timeout': elapsed > ReportStateManager.TIMEOUT_SECONDS,
            'content_size': len(str(report.report_content.get('content', ''))) if report.status == 'completed' else 0
        }