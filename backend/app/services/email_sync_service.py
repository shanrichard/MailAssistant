"""
Email synchronization service for syncing Gmail messages to local database
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..core.database import get_db
from ..models.user import User
from ..models.email import Email
from ..services.gmail_service import gmail_service

logger = logging.getLogger(__name__)


class EmailSyncService:
    """Service for synchronizing Gmail messages to local database"""
    
    def __init__(self):
        pass
    
    def sync_user_emails(
        self, 
        db: Session, 
        user: User, 
        days: int = 1, 
        max_messages: int = 100
    ) -> Dict[str, int]:
        """Sync user's emails from Gmail to local database"""
        try:
            stats = {
                'fetched': 0,
                'new': 0,
                'updated': 0,
                'errors': 0
            }
            
            # Get recent messages from Gmail
            logger.info(f"Fetching recent emails for user {user.id} from last {days} days")
            gmail_messages = gmail_service.get_recent_messages(user, days=days, max_results=max_messages)
            stats['fetched'] = len(gmail_messages)
            
            for gmail_message in gmail_messages:
                try:
                    result = self._sync_single_message(db, user, gmail_message)
                    if result == 'new':
                        stats['new'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync message {gmail_message.get('gmail_id')}: {str(e)}")
                    stats['errors'] += 1
            
            # Commit changes
            db.commit()
            
            logger.info(f"Email sync completed for user {user.id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync emails for user {user.id}: {str(e)}")
            db.rollback()
            raise
    
    def _sync_single_message(self, db: Session, user: User, gmail_message: Dict[str, Any]) -> str:
        """Sync a single Gmail message to database"""
        gmail_id = gmail_message.get('gmail_id')
        
        # Check if message already exists
        existing_email = db.query(Email).filter(
            Email.gmail_id == gmail_id,
            Email.user_id == user.id
        ).first()
        
        if existing_email:
            # Update existing message
            updated = self._update_email_from_gmail(existing_email, gmail_message)
            if updated:
                db.add(existing_email)
                return 'updated'
            return 'unchanged'
        else:
            # Create new message
            new_email = self._create_email_from_gmail(user, gmail_message)
            db.add(new_email)
            return 'new'
    
    def _create_email_from_gmail(self, user: User, gmail_message: Dict[str, Any]) -> Email:
        """Create new Email object from Gmail message data"""
        return Email(
            user_id=user.id,
            gmail_id=gmail_message.get('gmail_id'),
            thread_id=gmail_message.get('thread_id'),
            subject=gmail_message.get('subject', ''),
            sender=gmail_message.get('sender', ''),
            recipients=json.dumps(gmail_message.get('recipients', [])),
            cc_recipients=json.dumps(gmail_message.get('cc_recipients', [])),
            bcc_recipients=json.dumps(gmail_message.get('bcc_recipients', [])),
            body_plain=gmail_message.get('body_plain', ''),
            body_html=gmail_message.get('body_html', ''),
            received_at=gmail_message.get('received_at'),
            is_read='UNREAD' not in gmail_message.get('labels', []),
            has_attachments=gmail_message.get('has_attachments', False),
            labels=json.dumps(gmail_message.get('labels', []))
        )
    
    def _update_email_from_gmail(self, email: Email, gmail_message: Dict[str, Any]) -> bool:
        """Update existing Email object with Gmail message data"""
        updated = False
        
        # Check if read status changed
        is_read = 'UNREAD' not in gmail_message.get('labels', [])
        if email.is_read != is_read:
            email.is_read = is_read
            updated = True
        
        # Check if labels changed
        new_labels = json.dumps(gmail_message.get('labels', []))
        if email.labels != new_labels:
            email.labels = new_labels
            updated = True
        
        if updated:
            email.updated_at = datetime.utcnow()
        
        return updated
    
    def sync_unread_emails(self, db: Session, user: User) -> Dict[str, int]:
        """Sync only unread emails for a user"""
        try:
            stats = {
                'fetched': 0,
                'new': 0,
                'updated': 0,
                'errors': 0
            }
            
            # Get unread messages from Gmail
            logger.info(f"Fetching unread emails for user {user.id}")
            gmail_messages = gmail_service.get_unread_messages(user, max_results=200)
            stats['fetched'] = len(gmail_messages)
            
            for gmail_message in gmail_messages:
                try:
                    result = self._sync_single_message(db, user, gmail_message)
                    if result == 'new':
                        stats['new'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync unread message {gmail_message.get('gmail_id')}: {str(e)}")
                    stats['errors'] += 1
            
            # Commit changes
            db.commit()
            
            logger.info(f"Unread email sync completed for user {user.id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync unread emails for user {user.id}: {str(e)}")
            db.rollback()
            raise
    
    def sync_emails_by_query(
        self, 
        db: Session, 
        user: User, 
        query: str, 
        max_results: int = 100
    ) -> Dict[str, int]:
        """Sync emails matching a specific Gmail query"""
        try:
            stats = {
                'fetched': 0,
                'new': 0,
                'updated': 0,
                'errors': 0
            }
            
            # Get messages from Gmail using query
            logger.info(f"Fetching emails for user {user.id} with query: {query}")
            gmail_messages = gmail_service.search_messages(user, query=query, max_results=max_results)
            stats['fetched'] = len(gmail_messages)
            
            for gmail_message in gmail_messages:
                try:
                    result = self._sync_single_message(db, user, gmail_message)
                    if result == 'new':
                        stats['new'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync message {gmail_message.get('gmail_id')}: {str(e)}")
                    stats['errors'] += 1
            
            # Commit changes
            db.commit()
            
            logger.info(f"Query email sync completed for user {user.id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync emails by query for user {user.id}: {str(e)}")
            db.rollback()
            raise
    
    def get_sync_status(self, db: Session, user: User) -> Dict[str, Any]:
        """Get email synchronization status for user"""
        try:
            # Count local emails
            total_emails = db.query(Email).filter(Email.user_id == user.id).count()
            unread_emails = db.query(Email).filter(
                Email.user_id == user.id,
                Email.is_read == False
            ).count()
            
            # Get latest email timestamp
            latest_email = db.query(Email).filter(
                Email.user_id == user.id
            ).order_by(Email.received_at.desc()).first()
            
            latest_sync = latest_email.received_at if latest_email else None
            
            return {
                'total_emails': total_emails,
                'unread_emails': unread_emails,
                'latest_sync': latest_sync,
                'user_id': user.id
            }
            
        except Exception as e:
            logger.error(f"Failed to get sync status for user {user.id}: {str(e)}")
            raise
    
    def mark_emails_as_read(
        self, 
        db: Session, 
        user: User, 
        email_ids: List[str]
    ) -> Dict[str, int]:
        """Mark emails as read both locally and in Gmail"""
        try:
            stats = {
                'local_updated': 0,
                'gmail_updated': 0,
                'errors': 0
            }
            
            # Get emails from database
            emails = db.query(Email).filter(
                Email.user_id == user.id,
                Email.id.in_(email_ids)
            ).all()
            
            if not emails:
                return stats
            
            # Update local database
            gmail_message_ids = []
            for email in emails:
                if not email.is_read:
                    email.is_read = True
                    email.updated_at = datetime.utcnow()
                    stats['local_updated'] += 1
                    gmail_message_ids.append(email.gmail_id)
            
            db.commit()
            
            # Update Gmail
            if gmail_message_ids:
                success = gmail_service.mark_as_read(user, gmail_message_ids)
                if success:
                    stats['gmail_updated'] = len(gmail_message_ids)
                else:
                    stats['errors'] = len(gmail_message_ids)
            
            logger.info(f"Marked emails as read for user {user.id}: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to mark emails as read for user {user.id}: {str(e)}")
            db.rollback()
            raise
    
    def bulk_mark_category_as_read(
        self, 
        db: Session, 
        user: User, 
        category: str
    ) -> Dict[str, int]:
        """Mark all emails in a category as read"""
        try:
            # Get emails in category
            emails = db.query(Email).filter(
                Email.user_id == user.id,
                Email.category == category,
                Email.is_read == False
            ).all()
            
            if not emails:
                return {'local_updated': 0, 'gmail_updated': 0, 'errors': 0}
            
            email_ids = [str(email.id) for email in emails]
            return self.mark_emails_as_read(db, user, email_ids)
            
        except Exception as e:
            logger.error(f"Failed to bulk mark category {category} as read for user {user.id}: {str(e)}")
            raise


# Global email sync service instance
email_sync_service = EmailSyncService()