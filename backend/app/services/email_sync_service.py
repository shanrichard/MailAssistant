"""
Email synchronization service for syncing Gmail messages to local database
"""
import json
import logging
import time
import random
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timezone, timedelta
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
    
    # 新增智能同步相关方法
    
    def is_first_sync(self, db: Session, user: User) -> bool:
        """检查是否首次同步"""
        email_count = db.query(Email).filter(Email.user_id == user.id).count()
        return email_count == 0
    
    async def smart_sync_user_emails(
        self, 
        db: Session, 
        user: User, 
        force_full: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """智能同步策略（含容错机制）"""
        
        # 1. 检查是否首次同步
        is_first_sync = self.is_first_sync(db, user)
        
        # 2. 获取最新邮件时间戳（UTC时区）
        latest_timestamp = self._get_latest_email_timestamp(db, user)
        
        # 3. 决定同步策略
        if is_first_sync or force_full:
            return await self._full_sync_with_pagination(
                db, user, days=30, progress_callback=progress_callback
            )
        else:
            # 增量同步 + 轻量回扫
            # 注意：_incremental_sync 内部会处理 latest_timestamp 为 None 的情况（专家建议修复3）
            incremental_stats = await self._incremental_sync(db, user, since_timestamp=latest_timestamp)
            
            # 每周执行一次2天回扫，补充可能遗漏的邮件变更
            if self._should_run_light_rescan(db, user):
                rescan_stats = await self._light_rescan(db, user, days=2)
                incremental_stats = self._merge_stats(incremental_stats, rescan_stats)
            
            return incremental_stats

    async def _full_sync_with_pagination(
        self, 
        db: Session, 
        user: User, 
        days: int,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """分页全量同步（应对大量邮件）"""
        stats = {'fetched': 0, 'new': 0, 'updated': 0, 'errors': 0}
        page_token = None
        page_size = 100  # 初始页大小
        total_processed = 0
        
        # 计算时间范围（UTC）
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        query = f"after:{int(start_date.timestamp())} before:{int(end_date.timestamp())}"
        
        while True:
            try:
                # 动态调整页大小（根据API配额情况）
                page_size = self._adjust_page_size(page_size, stats['errors'])
                
                # 获取一页数据
                messages, next_page_token = gmail_service.search_messages_paginated(
                    user=user,
                    query=query,
                    max_results=page_size,
                    page_token=page_token
                )
                
                # 处理邮件
                for message in messages:
                    try:
                        sync_result = self._sync_single_message(db, user, message)
                        stats[sync_result] += 1
                        total_processed += 1
                        
                        # 进度回调：确保更新数据库进度（专家建议修复2）
                        if progress_callback and total_processed % 10 == 0:
                            # 计算进度百分比并写入数据库
                            progress_percentage = min(90, int(total_processed / 500 * 90))  # 最多到90%，留10%给后续处理
                            progress_callback({
                                'processed': total_processed,
                                'current_stats': stats,
                                'progress_percentage': progress_percentage
                            })
                            
                    except Exception as e:
                        stats['errors'] += 1
                        logger.error(f"Failed to sync message: {e}")
                        
                        # Token过期自动刷新
                        if "401" in str(e):
                            self._refresh_user_token(user)
                            
                # 分批提交，避免大事务
                if total_processed % 50 == 0:
                    db.commit()
                    
                # 检查是否有下一页
                page_token = next_page_token
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"Page sync failed: {e}")
                
                # 指数退避重试
                retry_count = stats.get('retry_count', 0)
                if retry_count < 3:
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                    stats['retry_count'] = retry_count + 1
                    continue
                else:
                    # 保存断点，下次可续传
                    self._save_sync_checkpoint(user.id, page_token, stats)
                    raise
                    
        db.commit()
        return stats

    async def _incremental_sync(
        self, 
        db: Session, 
        user: User, 
        since_timestamp: datetime
    ) -> Dict[str, int]:
        """增量同步：基于时间戳获取所有新邮件"""
        # 处理新账号情况：如果没有历史邮件，回退到全量同步（专家建议修复3）
        if not since_timestamp:
            logger.info("No previous emails found, falling back to full sync", extra={'user_id': user.id})
            return await self._full_sync_with_pagination(db, user, days=30)
        
        # 减8小时避免时区问题遗漏
        buffer_time = since_timestamp - timedelta(hours=8)
        query = f"after:{int(buffer_time.timestamp())}"
        
        return self.sync_emails_by_query(db, user, query, max_results=500)

    async def _light_rescan(self, db: Session, user: User, days: int) -> Dict[str, int]:
        """轻量回扫：检查最近N天的邮件变更"""
        # 只检查标签和已读状态变化
        query = f"newer_than:{days}d"
        return self.sync_emails_by_query(db, user, query, max_results=200)

    def _should_run_light_rescan(self, db: Session, user: User) -> bool:
        """判断是否需要轻量回扫（每周一次）"""
        last_rescan = self._get_last_rescan_time(db, user)
        if not last_rescan:
            return True
        return (datetime.now() - last_rescan).days >= 7

    def _get_latest_email_timestamp(self, db: Session, user: User) -> Optional[datetime]:
        """获取最新邮件时间戳"""
        latest_email = db.query(Email).filter(
            Email.user_id == user.id
        ).order_by(Email.received_at.desc()).first()
        
        return latest_email.received_at if latest_email else None

    def _adjust_page_size(self, current_size: int, errors: int) -> int:
        """根据错误率动态调整页大小"""
        if errors > 5:
            return max(10, current_size // 2)
        elif errors == 0 and current_size < 200:
            return min(200, current_size * 1.5)
        return current_size

    def _refresh_user_token(self, user: User):
        """刷新用户Token"""
        # TODO: 实现Token刷新逻辑
        logger.warning(f"Token refresh needed for user {user.id}")

    def _save_sync_checkpoint(self, user_id: str, page_token: str, stats: Dict):
        """保存同步断点"""
        # TODO: 实现断点保存逻辑
        logger.info(f"Saving sync checkpoint for user {user_id}: {page_token}")

    def _get_last_rescan_time(self, db: Session, user: User) -> Optional[datetime]:
        """获取最后回扫时间"""
        # TODO: 从用户偏好或同步状态中获取
        return None

    def _merge_stats(self, stats1: Dict[str, int], stats2: Dict[str, int]) -> Dict[str, int]:
        """合并同步统计"""
        merged = stats1.copy()
        for key, value in stats2.items():
            merged[key] = merged.get(key, 0) + value
        return merged


# Global email sync service instance
email_sync_service = EmailSyncService()