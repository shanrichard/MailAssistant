"""
Gmail API routes for email operations
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..api.auth import get_current_user
from ..models.user import User
from ..services.gmail_service import gmail_service
from ..services.email_sync_service import email_sync_service

router = APIRouter(prefix="/gmail", tags=["gmail"])


# Request/Response models
class SyncRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=30, description="Number of days to sync")
    max_messages: int = Field(default=100, ge=1, le=1000, description="Maximum messages to sync")


class SyncResponse(BaseModel):
    success: bool
    stats: Dict[str, int]
    message: str


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