"""
Gmail API routes for email operations
"""
from typing import List, Dict, Any, Optional, Callable
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio

from ..core.database import get_db
from ..api.auth import get_current_user
from ..models.user import User
from ..models.user_sync_status import UserSyncStatus
from ..services.gmail_service import gmail_service
from ..services.email_sync_service import email_sync_service
from ..core.logging import get_logger
from ..services.idempotent_sync_service import start_sync_idempotent, release_sync_status_atomic, get_active_task_info
from ..services.heartbeat_sync_service import execute_background_sync_with_heartbeat, get_sync_health_status

logger = get_logger(__name__)

router = APIRouter(prefix="/gmail", tags=["gmail"])


# Request/Response models
class SyncRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=30, description="Number of days to sync")
    max_messages: int = Field(default=100, ge=1, le=1000, description="Maximum messages to sync")


class SyncResponse(BaseModel):
    success: bool
    stats: Dict[str, int]
    message: str
    in_progress: Optional[bool] = False
    progress_percentage: Optional[int] = 0
    task_id: Optional[str] = None


class EmailListResponse(BaseModel):
    emails: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int


class BulkActionRequest(BaseModel):
    email_ids: List[str] = Field(..., description="List of email IDs")


class BulkActionResponse(BaseModel):
    success: bool
    stats: Dict[str, int]
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., description="Gmail search query")
    max_results: int = Field(default=50, ge=1, le=200)


@router.get("/profile")
async def get_gmail_profile(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get Gmail user profile"""
    try:
        profile = gmail_service.get_user_profile(current_user)
        return {
            "success": True,
            "profile": profile
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get Gmail profile: {str(e)}")


@router.post("/sync", response_model=SyncResponse)
async def sync_emails(
    request: SyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """Sync emails from Gmail to local database"""
    try:
        stats = email_sync_service.sync_user_emails(
            db=db,
            user=current_user,
            days=request.days,
            max_messages=request.max_messages
        )
        
        return SyncResponse(
            success=True,
            stats=stats,
            message=f"Successfully synced {stats['new']} new emails and updated {stats['updated']} existing emails"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sync emails: {str(e)}")


@router.post("/sync/unread", response_model=SyncResponse)
async def sync_unread_emails(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """Sync only unread emails from Gmail"""
    try:
        stats = email_sync_service.sync_unread_emails(db=db, user=current_user)
        
        return SyncResponse(
            success=True,
            stats=stats,
            message=f"Successfully synced {stats['new']} new unread emails"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sync unread emails: {str(e)}")


@router.get("/sync/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get email synchronization status"""
    try:
        status = email_sync_service.get_sync_status(db=db, user=current_user)
        return {
            "success": True,
            "status": status
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get sync status: {str(e)}")


@router.post("/search", response_model=List[Dict[str, Any]])
async def search_emails(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Search emails in Gmail"""
    try:
        messages = gmail_service.search_messages(
            user=current_user,
            query=request.query,
            max_results=request.max_results
        )
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to search emails: {str(e)}")


@router.get("/recent")
async def get_recent_emails(
    days: int = Query(default=1, ge=1, le=7, description="Number of days"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get recent emails from Gmail"""
    try:
        messages = gmail_service.get_recent_messages(
            user=current_user,
            days=days,
            max_results=max_results
        )
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get recent emails: {str(e)}")


@router.get("/unread")
async def get_unread_emails(
    max_results: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get unread emails from Gmail"""
    try:
        messages = gmail_service.get_unread_messages(
            user=current_user,
            max_results=max_results
        )
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get unread emails: {str(e)}")


@router.post("/mark-read", response_model=BulkActionResponse)
async def mark_emails_as_read(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BulkActionResponse:
    """Mark emails as read"""
    try:
        stats = email_sync_service.mark_emails_as_read(
            db=db,
            user=current_user,
            email_ids=request.email_ids
        )
        
        return BulkActionResponse(
            success=True,
            stats=stats,
            message=f"Successfully marked {stats['local_updated']} emails as read"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to mark emails as read: {str(e)}")


@router.post("/mark-read/category/{category}", response_model=BulkActionResponse)
async def mark_category_as_read(
    category: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> BulkActionResponse:
    """Mark all emails in a category as read"""
    try:
        stats = email_sync_service.bulk_mark_category_as_read(
            db=db,
            user=current_user,
            category=category
        )
        
        return BulkActionResponse(
            success=True,
            stats=stats,
            message=f"Successfully marked {stats['local_updated']} {category} emails as read"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to mark {category} emails as read: {str(e)}")


@router.post("/labels/add")
async def add_labels_to_emails(
    message_ids: List[str],
    label_ids: List[str],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add labels to Gmail messages"""
    try:
        success = gmail_service.add_labels(current_user, message_ids, label_ids)
        
        return {
            "success": success,
            "message": f"{'Successfully' if success else 'Failed to'} add labels to {len(message_ids)} messages"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add labels: {str(e)}")


@router.post("/labels/remove")
async def remove_labels_from_emails(
    message_ids: List[str],
    label_ids: List[str],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Remove labels from Gmail messages"""
    try:
        success = gmail_service.remove_labels(current_user, message_ids, label_ids)
        
        return {
            "success": success,
            "message": f"{'Successfully' if success else 'Failed to'} remove labels from {len(message_ids)} messages"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove labels: {str(e)}")


@router.get("/message/{message_id}")
async def get_message_details(
    message_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed information about a specific Gmail message"""
    try:
        message = gmail_service.get_message_details(current_user, message_id)
        parsed_message = gmail_service.parse_message(message)
        
        return {
            "success": True,
            "message": parsed_message
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get message details: {str(e)}")


@router.get("/sender/{sender_email}")
async def get_messages_by_sender(
    sender_email: str,
    max_results: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get messages from a specific sender"""
    try:
        messages = gmail_service.get_messages_by_sender(
            user=current_user,
            sender_email=sender_email,
            max_results=max_results
        )
        return messages
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get messages by sender: {str(e)}")


# 新的智能同步 API 端点

@router.post("/sync/smart", response_model=SyncResponse)
async def smart_sync_emails(
    background_tasks: BackgroundTasks,
    force_full: bool = Query(default=False, description="Force full sync"),
    background: bool = Query(default=False, description="Run in background"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """智能同步：幂等启动，防止重复任务"""
    try:
        # 使用幂等启动接口
        task_id = start_sync_idempotent(db, current_user.id, force_full)
        
        # 检查是否复用了现有任务
        active_task = get_active_task_info(db, current_user.id)
        
        if active_task and active_task.get("is_active") and active_task["task_id"] == task_id:
            # 复用现有任务
            return SyncResponse(
                success=True,
                stats=active_task.get("current_stats", {}),
                message="复用进行中的同步任务",
                in_progress=True,
                progress_percentage=active_task.get("progress_percentage", 0),
                task_id=task_id
            )
        
        # 新任务：启动后台任务
        logger.info(f"准备启动后台任务", extra={"task_id": task_id, "has_background_tasks": bool(background_tasks)})
        
        if background_tasks:
            logger.info(f"使用BackgroundTasks启动任务", extra={"task_id": task_id})
            background_tasks.add_task(
                execute_background_sync_with_heartbeat, current_user.id, force_full, task_id
            )
        else:
            # 如果没有BackgroundTasks，使用asyncio
            logger.info(f"使用asyncio.create_task启动任务", extra={"task_id": task_id})
            asyncio.create_task(
                execute_background_sync_with_heartbeat(current_user.id, force_full, task_id)
            )
        
        return SyncResponse(
            success=True,
            stats={},
            message="同步任务已启动",
            task_id=task_id,
            in_progress=True
        )
        
    except Exception as e:
        logger.error(f"启动同步失败: {e}", extra={"user_id": current_user.id})
        raise HTTPException(status_code=400, detail=f"启动同步失败: {str(e)}")


@router.get("/sync/should-sync")
async def should_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """检查是否需要同步及同步建议"""
    try:
        # 检查是否首次同步
        is_first = email_sync_service.is_first_sync(db, current_user)
        
        # 获取最后同步时间
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == current_user.id
        ).first()
        
        last_sync = sync_status.updated_at if sync_status else None
        
        # 获取邮件数量
        from ..models.email import Email
        email_count = db.query(Email).filter(Email.user_id == current_user.id).count()
        
        # 决定是否需要同步
        need_sync = is_first or (sync_status and sync_status.is_syncing is False)
        exceeded = False
        
        if last_sync:
            from datetime import timedelta
            from app.utils.datetime_utils import utc_now, safe_datetime_diff, format_datetime_for_api
            
            # 使用安全的时区处理函数
            current_time = utc_now()
            time_diff = safe_datetime_diff(current_time, last_sync)
            
            if time_diff:
                exceeded = time_diff > timedelta(hours=1)  # 1小时未同步则建议同步
                need_sync = need_sync or exceeded
                logger.debug(f"Time difference since last sync: {time_diff}, exceeded: {exceeded}")
        
        # 返回详细原因
        return {
            "needsSync": need_sync,
            "reason": "firstSync" if is_first else "thresholdExceeded" if exceeded else "scheduled",
            "lastSyncTime": format_datetime_for_api(last_sync),
            "emailCount": email_count,
            "isFirstSync": is_first
        }
        
    except Exception as e:
        logger.error(f"Failed to check sync status: {e}", user_id=current_user.id)
        raise HTTPException(status_code=400, detail=f"Failed to check sync status: {str(e)}")


@router.get("/sync/progress/{task_id}")
async def get_sync_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """获取后台同步任务进度"""
    try:
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == current_user.id,
            UserSyncStatus.task_id == task_id
        ).first()
        
        if not sync_status:
            raise HTTPException(status_code=404, detail="Sync task not found")
        
        return {
            "success": True,
            "isRunning": sync_status.is_syncing,
            "progress": sync_status.progress_percentage,
            "stats": sync_status.current_stats or {},
            "error": sync_status.error_message,
            "syncType": sync_status.sync_type,
            "startedAt": sync_status.started_at.isoformat() if sync_status.started_at else None,
            "updatedAt": sync_status.updated_at.isoformat() if sync_status.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get sync progress: {e}", task_id=task_id, user_id=current_user.id)
        raise HTTPException(status_code=400, detail=f"Failed to get sync progress: {str(e)}")

@router.get("/sync/health")
async def sync_health_check():
    """同步系统健康检查"""
    try:
        health_status = get_sync_health_status()
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")