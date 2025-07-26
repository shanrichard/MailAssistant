"""
Daily Reports API routes
"""
import asyncio
from typing import Dict, Any
from datetime import date, datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db, SessionLocal
from ..api.auth import get_current_user
from ..models.user import User
from ..models.daily_report_log import DailyReportLog
from ..agents.email_processor import EmailProcessorAgent
from ..services.email_sync_service import email_sync_service
from ..core.logging import get_logger
from ..utils.report_state_manager import ReportStateManager

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


async def sync_user_emails_task(user_id: str):
    """后台邮件同步任务"""
    db = SessionLocal()
    try:
        logger.info(f"Starting background email sync for user {user_id}")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # 调用同步服务
            stats = email_sync_service.sync_user_emails(db, user, days=1, max_messages=100)
            logger.info(f"Email sync completed for user {user_id}: {stats}")
            
            # 更新用户的同步时间戳
            user.last_history_sync = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated last_history_sync for user {user_id}")
    except Exception as e:
        logger.error(f"Background sync failed for user {user_id}: {e}")
    finally:
        db.close()


async def check_and_trigger_sync(user_id: str, db: Session):
    """检查并触发邮件同步"""
    user = db.query(User).filter(User.id == user_id).first()
    
    # 使用 last_history_sync 字段判断
    if not user.last_history_sync or \
       datetime.now(timezone.utc) - user.last_history_sync > timedelta(minutes=30):
        # 使用 asyncio.create_task 触发后台同步，不等待
        asyncio.create_task(sync_user_emails_task(user_id))
        logger.info(f"Triggered background email sync for user {user_id}")
        return True
    return False


async def generate_report_task(user_id: str, report_date: date):
    """后台任务：生成日报"""
    db = SessionLocal()
    try:
        logger.info(f"Starting report generation for user {user_id} on {report_date}")
        
        # 1. 创建Agent实例
        processor = EmailProcessorAgent(str(user_id), db)
        logger.info(f"EmailProcessorAgent created for user {user_id}")
        
        # 2. 固定的请求消息
        logger.info("Calling processor.process...")
        report_content = await processor.process("请生成今天的邮件日报")
        logger.info(f"Report content generated, length: {len(report_content)}")
        
        # 3. 更新数据库
        report = db.query(DailyReportLog).filter(
            DailyReportLog.user_id == user_id,
            DailyReportLog.report_date == report_date
        ).first()
        
        if report:
            report.status = 'completed'
            report.report_content = {'content': report_content}
            report.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Report generated and saved for user {user_id} on {report_date}")
            
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)
        # 更新状态为failed
        try:
            report = db.query(DailyReportLog).filter(
                DailyReportLog.user_id == user_id,
                DailyReportLog.report_date == report_date
            ).first()
            if report:
                report.status = 'failed'
                report.report_content = {'error': str(e)}
                db.commit()
                logger.info(f"Report status updated to failed for user {user_id}")
        except Exception as db_error:
            logger.error(f"Failed to update report status: {db_error}")
    finally:
        db.close()
        logger.info(f"Report generation task completed for user {user_id}")


async def trigger_report_generation(user_id: str, report_date: date):
    """触发日报生成（异步执行）"""
    asyncio.create_task(generate_report_task(user_id, report_date))


@router.get("/daily")
async def get_daily_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取今日日报"""
    today = date.today()
    user_id = str(current_user.id)
    
    try:
        # 检查并触发邮件同步（不等待）
        sync_triggered = await check_and_trigger_sync(user_id, db)
        if sync_triggered:
            logger.info(f"Email sync triggered for user {user_id} when accessing daily report")
        # 查询今天的日报
        report = db.query(DailyReportLog).filter(
            DailyReportLog.user_id == user_id,
            DailyReportLog.report_date == today
        ).first()
        
        # 情况1: 日报已存在且完成
        if report and report.status == 'completed':
            return {
                'status': 'completed',
                'content': report.report_content.get('content', ''),
                'generated_at': report.created_at.isoformat()
            }
        
        # 情况2: 日报正在生成中
        if report and report.status == 'processing':
            # 使用状态管理器检查超时
            if ReportStateManager.check_timeout(report):
                ReportStateManager.handle_timeout(db, report)
                # 继续到情况3重新生成
            else:
                elapsed = (datetime.now(timezone.utc) - report.created_at).total_seconds()
                return {
                    'status': 'processing',
                    'message': f'日报生成中，请稍后刷新页面（已进行 {int(elapsed)} 秒）'
                }
        
        # 情况3: 不存在或失败，需要创建新的
        with ReportStateManager.acquire_report_lock(db, user_id, today) as new_report:
            if new_report:
                # 成功获取锁，触发生成
                await trigger_report_generation(user_id, today)
                
                return {
                    'status': 'processing',
                    'message': '开始生成日报，请稍后刷新页面'
                }
            else:
                # 并发情况：其他请求已经在处理
                # 等待一小段时间看是否能快速完成
                completed_report = await ReportStateManager.wait_for_completion(
                    db, user_id, today, max_wait=5
                )
                
                if completed_report and completed_report.status == 'completed':
                    return {
                        'status': 'completed',
                        'content': completed_report.report_content.get('content', ''),
                        'generated_at': completed_report.created_at.isoformat()
                    }
                else:
                    return {
                        'status': 'processing',
                        'message': '日报生成中，请稍后刷新页面'
                    }
            
    except Exception as e:
        logger.error(f"Failed to get daily report: {e}")
        raise HTTPException(status_code=500, detail="获取日报失败")


@router.post("/daily/refresh")
async def refresh_daily_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """强制刷新今日日报"""
    today = date.today()
    user_id = str(current_user.id)
    
    try:
        # 检查是否有正在处理的报告
        existing_report = db.query(DailyReportLog).filter(
            DailyReportLog.user_id == user_id,
            DailyReportLog.report_date == today
        ).first()
        
        if existing_report and existing_report.status == 'processing':
            # 检查是否超时
            if not ReportStateManager.check_timeout(existing_report):
                elapsed = (datetime.now(timezone.utc) - existing_report.created_at).total_seconds()
                return {
                    'status': 'processing',
                    'message': f'日报正在生成中，请稍等（已进行 {int(elapsed)} 秒）'
                }
        
        # 删除旧日报
        if existing_report:
            db.delete(existing_report)
            db.commit()
        
        # 使用锁机制创建新的processing记录
        with ReportStateManager.acquire_report_lock(db, user_id, today) as new_report:
            if new_report:
                # 成功获取锁，触发生成
                await trigger_report_generation(user_id, today)
                
                return {
                    'status': 'processing',
                    'message': '开始重新生成日报，请稍后刷新页面'
                }
            else:
                # 并发情况：其他请求已经在处理
                return {
                    'status': 'processing',
                    'message': '日报刷新已由其他请求触发，请稍后刷新页面'
                }
        
    except Exception as e:
        logger.error(f"Failed to refresh daily report: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="刷新日报失败")


@router.get("/sync-status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取邮件同步状态"""
    user = db.query(User).filter(User.id == current_user.id).first()
    
    sync_needed = False
    time_since_sync = None
    
    if user.last_history_sync:
        time_since_sync = datetime.now(timezone.utc) - user.last_history_sync
        sync_needed = time_since_sync > timedelta(minutes=30)
    else:
        sync_needed = True
        
    return {
        "last_sync": user.last_history_sync.isoformat() if user.last_history_sync else None,
        "time_since_sync": str(time_since_sync) if time_since_sync else None,
        "sync_needed": sync_needed,
        "threshold_minutes": 30
    }


@router.get("/daily/status")
async def get_report_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取今日日报的详细状态"""
    today = date.today()
    user_id = str(current_user.id)
    
    status_info = ReportStateManager.get_report_status(db, user_id, today)
    
    # 添加额外的上下文信息
    status_info['user_id'] = user_id
    status_info['report_date'] = today.isoformat()
    status_info['current_time'] = datetime.now(timezone.utc).isoformat()
    
    return status_info


@router.post("/cleanup")
async def trigger_cleanup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """手动触发清理任务（仅管理员可用）"""
    # 这里可以添加管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Only admins can trigger cleanup")
    
    try:
        from ..utils.cleanup_tasks import cleanup_manager
        await cleanup_manager.force_cleanup()
        
        return {
            "status": "success",
            "message": "Cleanup tasks executed successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute cleanup tasks")