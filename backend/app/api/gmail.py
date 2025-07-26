"""
Gmail API routes for email operations
"""
from typing import List, Dict, Any, Optional, Callable
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime
import asyncio
import time

from ..core.database import get_db
from ..api.auth import get_current_user
from ..models.user import User
from ..models.user_sync_status import UserSyncStatus
from ..services.gmail_service import gmail_service
from ..services.email_sync_service import email_sync_service
from ..core.logging import get_logger
from ..utils.api_optimization import (
    monitor_api_performance,
    APIErrorHandler,
    OptimizationConfig,
    execute_with_fallback
)

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
@monitor_api_performance("search_emails")
async def search_emails_optimized(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """搜索邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_search_optimization_enabled():
            # 使用优化版本：解决N+1问题
            messages = await execute_with_fallback(
                lambda user, query, max_results: gmail_service.search_messages_optimized(user, query=query, max_results=max_results),
                lambda user, query, max_results: gmail_service.search_messages(user, query=query, max_results=max_results),
                True,
                current_user, request.query, request.max_results
            )
        else:
            # 原版实现（保持兼容性）
            messages = await asyncio.to_thread(
                gmail_service.search_messages,
                current_user, 
                query=request.query,
                max_results=request.max_results
            )
        
        return messages
        
    except Exception as e:
        logger.error(f"邮件搜索失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_search_error(e, "search_emails")


@router.get("/recent")
@monitor_api_performance("recent_emails")
async def get_recent_emails_optimized(
    days: int = Query(default=1, ge=1, le=7, description="Number of days"),
    max_results: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """获取最近邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_search_optimization_enabled():
            # 使用优化版本：解决N+1问题
            messages = await execute_with_fallback(
                lambda user, days, max_results: gmail_service.get_recent_messages_optimized(user, days=days, max_results=max_results),
                lambda user, days, max_results: gmail_service.get_recent_messages(user, days=days, max_results=max_results),
                True,
                current_user, days, max_results
            )
        else:
            # 原版实现（保持兼容性）
            messages = await asyncio.to_thread(
                gmail_service.get_recent_messages,
                current_user,
                days=days,
                max_results=max_results
            )
        
        return messages
        
    except Exception as e:
        logger.error(f"获取最近邮件失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_search_error(e, "recent_emails")


@router.get("/unread")
@monitor_api_performance("unread_emails")
async def get_unread_emails_optimized(
    max_results: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """获取未读邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_search_optimization_enabled():
            # 使用优化版本：解决N+1问题
            messages = await execute_with_fallback(
                lambda user, max_results: gmail_service.get_unread_messages_optimized(user, max_results=max_results),
                lambda user, max_results: gmail_service.get_unread_messages(user, max_results=max_results),
                True,
                current_user, max_results
            )
        else:
            # 原版实现（保持兼容性）
            messages = await asyncio.to_thread(
                gmail_service.get_unread_messages,
                current_user,
                max_results=max_results
            )
        
        return messages
        
    except Exception as e:
        logger.error(f"获取未读邮件失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_search_error(e, "unread_emails")


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
@monitor_api_performance("messages_by_sender")
async def get_messages_by_sender_optimized(
    sender_email: str,
    max_results: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """获取特定发件人的邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_search_optimization_enabled():
            # 使用优化版本：解决N+1问题
            messages = await execute_with_fallback(
                lambda user, sender_email, max_results: gmail_service.get_messages_by_sender_optimized(
                    user, sender_email=sender_email, max_results=max_results
                ),
                lambda user, sender_email, max_results: gmail_service.get_messages_by_sender(
                    user, sender_email=sender_email, max_results=max_results
                ),
                True,
                current_user, sender_email, max_results
            )
        else:
            # 原版实现（保持兼容性）
            messages = await asyncio.to_thread(
                gmail_service.get_messages_by_sender,
                current_user,
                sender_email=sender_email,
                max_results=max_results
            )
        
        return messages
        
    except Exception as e:
        logger.error(f"获取发件人邮件失败: {e}", extra={"user_id": current_user.id, "sender": sender_email})
        raise APIErrorHandler.handle_search_error(e, "messages_by_sender")


# 优化的同步 API

@router.post("/sync/today")
@monitor_api_performance("sync_today")
async def sync_today_emails_optimized(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同步今天的邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_sync_optimization_enabled():
            # 使用优化的智能同步
            result = await execute_with_fallback(
                lambda db, user: email_sync_service.smart_sync_user_emails_optimized(db, user, force_full=False),
                lambda db, user: email_sync_service.sync_emails_by_timerange(db, user, "today", 500),
                True,
                db, current_user
            )
            
            # 如果智能同步没有找到今天的邮件，使用查询方式补充
            if result['new'] == 0 and result['updated'] == 0:
                additional_result = await execute_with_fallback(
                    lambda db, user: email_sync_service.sync_emails_by_query_with_monitoring(db, user, "newer_than:1d", 500),
                    lambda db, user: email_sync_service.sync_emails_by_timerange(db, user, "today", 500),
                    True,
                    db, current_user
                )
                # 合并结果
                for key in ['new', 'updated', 'errors']:
                    result[key] += additional_result.get(key, 0)
        else:
            # 原版实现（保持兼容性）
            result = await asyncio.to_thread(
                email_sync_service.sync_emails_by_timerange,
                db, current_user, "today", 500
            )
        
        return {
            "success": True,
            "message": f"成功同步了 {result['new']} 封新邮件，更新了 {result['updated']} 封",
            "stats": result
        }
        
    except Exception as e:
        logger.error(f"同步今天邮件失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_sync_error(e, "sync_today")


@router.post("/sync/week")
@monitor_api_performance("sync_week")
async def sync_week_emails_optimized(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同步本周的邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_sync_optimization_enabled():
            # 使用优化的查询同步（一周的邮件）
            result = await execute_with_fallback(
                lambda db, user: email_sync_service.sync_emails_by_query_with_monitoring(db, user, "newer_than:7d", 500),
                lambda db, user: email_sync_service.sync_emails_by_timerange(db, user, "week", 500),
                True,
                db, current_user
            )
        else:
            # 原版实现（保持兼容性）
            result = await asyncio.to_thread(
                email_sync_service.sync_emails_by_timerange,
                db, current_user, "week", 500
            )
        
        return {
            "success": True,
            "message": f"成功同步了 {result['new']} 封新邮件，更新了 {result['updated']} 封",
            "stats": result
        }
        
    except Exception as e:
        logger.error(f"同步本周邮件失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_sync_error(e, "sync_week")


@router.post("/sync/month")
@monitor_api_performance("sync_month")
async def sync_month_emails_optimized(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同步本月的邮件 - 优化版本"""
    try:
        if OptimizationConfig.is_sync_optimization_enabled():
            # 使用优化的查询同步（一个月的邮件）
            result = await execute_with_fallback(
                lambda db, user: email_sync_service.sync_emails_by_query_with_monitoring(db, user, "newer_than:30d", 500),
                lambda db, user: email_sync_service.sync_emails_by_timerange(db, user, "month", 500),
                True,
                db, current_user
            )
        else:
            # 原版实现（保持兼容性）
            result = await asyncio.to_thread(
                email_sync_service.sync_emails_by_timerange,
                db, current_user, "month", 500
            )
        
        return {
            "success": True,
            "message": f"成功同步了 {result['new']} 封新邮件，更新了 {result['updated']} 封",
            "stats": result
        }
        
    except Exception as e:
        logger.error(f"同步本月邮件失败: {e}", extra={"user_id": current_user.id})
        raise APIErrorHandler.handle_sync_error(e, "sync_month")


# 健康检查和监控端点

@router.get("/health/optimization")
async def optimization_health_check():
    """优化功能健康检查"""
    return OptimizationConfig.get_optimization_status()


@router.get("/stats/performance")
async def get_performance_stats(
    current_user: User = Depends(get_current_user)
):
    """获取API性能统计（开发和调试用）"""
    from ..core.config import settings
    
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")
    
    # 这里可以返回内存中的性能统计信息
    # 实际实现可以集成到已有的监控系统
    return {
        "message": "Performance stats available in logs",
        "monitoring_enabled": OptimizationConfig.is_performance_monitoring_enabled(),
        "threshold": OptimizationConfig.get_performance_threshold(),
        "optimization_status": OptimizationConfig.get_optimization_status(),
        "timestamp": time.time()
    }