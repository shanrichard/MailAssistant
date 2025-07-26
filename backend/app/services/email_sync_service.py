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
    
    def sync_emails_by_timerange(
        self, 
        db: Session, 
        user: User, 
        timerange: str, 
        max_results: int = 500
    ) -> Dict[str, int]:
        """Sync emails by time range (today, week, month)"""
        try:
            # 构建查询字符串
            if timerange == "today":
                query = "newer_than:1d"
            elif timerange == "week":
                query = "newer_than:7d"
            elif timerange == "month":
                query = "newer_than:30d"
            else:
                raise ValueError(f"Invalid timerange: {timerange}")
            
            logger.info(f"Starting {timerange} email sync for user {user.id}")
            
            # 使用现有的按查询同步方法
            stats = self.sync_emails_by_query(db, user, query, max_results)
            
            # 更新同步状态
            self._update_sync_status(
                db, 
                user, 
                f"成功同步{timerange}邮件", 
                stats
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync {timerange} emails for user {user.id}: {str(e)}")
            self._update_sync_status(
                db, 
                user, 
                f"同步{timerange}邮件失败: {str(e)}", 
                {'new': 0, 'updated': 0, 'errors': 1}
            )
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
    
    def _update_sync_status(self, db: Session, user: User, message: str, stats: Dict[str, int]):
        """更新用户同步状态（简化版）"""
        from datetime import datetime
        from ..models.user_sync_status import UserSyncStatus
        
        try:
            # 获取或创建同步状态记录
            sync_status = db.query(UserSyncStatus).filter(
                UserSyncStatus.user_id == user.id
            ).first()
            
            if not sync_status:
                sync_status = UserSyncStatus(user_id=user.id)
                db.add(sync_status)
            
            # 更新简化的状态信息
            sync_status.last_sync_time = datetime.now()
            sync_status.sync_message = f"{message} (新: {stats.get('new', 0)}, 更新: {stats.get('updated', 0)})"
            
            db.commit()
            logger.info(f"Updated sync status for user {user.id}: {message}")
            
        except Exception as e:
            logger.error(f"Failed to update sync status for user {user.id}: {str(e)}")
            db.rollback()
    
    # Optimized batch operations (Task 3-14-5)
    
    def _sync_messages_batch(self, db: Session, user: User, gmail_messages: List[Dict[str, Any]]) -> Dict[str, int]:
        """批量同步邮件，优化数据库操作
        
        这个方法解决了原版_sync_single_message中的N次数据库查询问题：
        - 原版：每个邮件单独查询数据库检查是否存在（N次查询）
        - 优化版：批量查询所有邮件的存在性（1次查询）
        
        Args:
            db: 数据库会话
            user: 用户对象
            gmail_messages: Gmail消息列表
            
        Returns:
            同步统计信息：{'new': int, 'updated': int, 'errors': int}
        """
        if not gmail_messages:
            return {'new': 0, 'updated': 0, 'errors': 0}
        
        try:
            # 1. 批量检查已存在的邮件（优化：1次查询而不是N次）
            gmail_ids = [msg.get('gmail_id') for msg in gmail_messages if msg.get('gmail_id')]
            
            # 去重gmail_ids，处理可能的重复数据
            unique_gmail_ids = list(set(gmail_ids))
            
            existing_emails = db.query(Email).filter(
                Email.user_id == user.id,
                Email.gmail_id.in_(unique_gmail_ids)
            ).all()
            
            # 创建现有邮件的映射，便于快速查找
            existing_ids_map = {email.gmail_id: email for email in existing_emails}
            
            # 2. 分类处理：新邮件vs更新邮件
            new_emails = []
            updated_emails = []
            processed_gmail_ids = set()  # 用于去重
            
            for gmail_message in gmail_messages:
                gmail_id = gmail_message.get('gmail_id')
                if not gmail_id or gmail_id in processed_gmail_ids:
                    continue  # 跳过无效或重复的邮件ID
                
                processed_gmail_ids.add(gmail_id)
                
                if gmail_id in existing_ids_map:
                    # 检查是否需要更新现有邮件
                    existing_email = existing_ids_map[gmail_id]
                    if self._update_email_from_gmail(existing_email, gmail_message):
                        updated_emails.append(existing_email)
                else:
                    # 创建新邮件
                    new_email = self._create_email_from_gmail(user, gmail_message)
                    new_emails.append(new_email)
            
            # 3. 批量数据库操作（优化：批量操作而不是逐个操作）
            if new_emails:
                db.add_all(new_emails)
                logger.debug(f"Batch added {len(new_emails)} new emails")
            
            if updated_emails:
                for email in updated_emails:
                    db.add(email)  # 将更新的邮件标记为需要保存
                logger.debug(f"Batch updated {len(updated_emails)} existing emails")
            
            stats = {
                'new': len(new_emails),
                'updated': len(updated_emails),
                'errors': 0
            }
            
            logger.info(f"Batch sync completed: {stats['new']} new, {stats['updated']} updated emails")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to batch sync messages for user {user.id}: {str(e)}")
            return {'new': 0, 'updated': 0, 'errors': 1}
    
    def sync_emails_by_query_with_monitoring(
        self, 
        db: Session, 
        user: User, 
        query: str, 
        max_results: int = 100
    ) -> Dict[str, int]:
        """带性能监控的邮件同步
        
        集成已实现的性能监控组件，追踪优化效果：
        - 监控各阶段耗时
        - 记录API调用次数
        - 收集性能元数据
        - 记录错误信息
        
        Args:
            db: 数据库会话
            user: 用户对象
            query: Gmail查询字符串
            max_results: 最大结果数
            
        Returns:
            同步统计信息：{'new': int, 'updated': int, 'errors': int}
        """
        from ..utils.sync_performance_monitor import SyncPerformanceMonitor
        from ..services.gmail_service import gmail_service
        
        monitor = SyncPerformanceMonitor()
        monitor.start_monitoring()
        
        try:
            # 1. 获取邮件列表（使用优化版本）
            monitor.start_stage('fetch_messages')
            gmail_messages = gmail_service.search_messages_optimized(user, query, max_results)
            monitor.record_api_call(count=len(gmail_messages))
            monitor.end_stage('fetch_messages')
            
            # 2. 批量同步到数据库（使用优化版本）
            monitor.start_stage('sync_to_db')
            stats = self._sync_messages_batch(db, user, gmail_messages)
            monitor.end_stage('sync_to_db')
            
            # 3. 提交事务
            monitor.start_stage('commit_transaction')
            db.commit()
            monitor.end_stage('commit_transaction')
            
            # 4. 记录性能数据
            monitor.set_metadata('user_id', str(user.id))
            monitor.set_metadata('query', query)
            monitor.set_metadata('message_count', len(gmail_messages))
            
            # 5. 生成性能报告
            report = monitor.get_report()
            logger.info(f"Sync performance: {report['total_duration']:.2f}s, "
                       f"{report['api_calls']} API calls, {len(gmail_messages)} messages")
            
            return stats
            
        except Exception as e:
            monitor.record_error('sync_process', e)
            db.rollback()
            logger.error(f"Failed to sync emails with monitoring for user {user.id}: {str(e)}")
            raise
    
    def smart_sync_user_emails_optimized(
        self, 
        db: Session, 
        user: User, 
        force_full: bool = False
    ) -> Dict[str, int]:
        """优化的智能同步，集成History API和性能监控
        
        实现真正的增量同步策略：
        1. 优先使用History API进行增量同步
        2. History API失败时回退到时间基础同步
        3. 集成性能监控追踪优化效果
        4. 自动管理historyId的更新
        
        Args:
            db: 数据库会话
            user: 用户对象
            force_full: 是否强制全量同步
            
        Returns:
            同步统计信息：{'new': int, 'updated': int, 'errors': int}
        """
        from ..utils.sync_performance_monitor import SyncPerformanceMonitor
        from ..services.gmail_service import gmail_service
        
        monitor = SyncPerformanceMonitor()
        monitor.start_monitoring()
        
        try:
            # 1. 检查是否可以使用History API增量同步
            if not force_full and user.last_history_id:
                monitor.start_stage('history_sync')
                try:
                    # 使用History API获取变更的邮件ID
                    changed_ids, new_history_id = gmail_service.fetch_changed_msg_ids(
                        user, user.last_history_id
                    )
                    
                    if changed_ids:
                        # 批量获取变更邮件的详情
                        changed_messages = gmail_service.get_messages_batch(user, changed_ids)
                        stats = self._sync_messages_batch(db, user, changed_messages)
                        
                        # 更新history_id
                        user.last_history_id = new_history_id
                        user.last_history_sync = datetime.now(timezone.utc)
                        db.add(user)
                        db.commit()
                        
                        monitor.end_stage('history_sync')
                        logger.info(f"History API sync completed: {stats}")
                        return stats
                    else:
                        # 无变更，但仍需更新historyId
                        user.last_history_id = new_history_id
                        user.last_history_sync = datetime.now(timezone.utc)
                        db.add(user)
                        db.commit()
                        
                        monitor.end_stage('history_sync')
                        logger.info("History API sync: no changes found")
                        return {'new': 0, 'updated': 0, 'errors': 0}
                        
                except Exception as e:
                    logger.warning(f"History API sync failed, falling back to time-based sync: {e}")
                    monitor.record_error('history_sync', e)
                    monitor.end_stage('history_sync')
            
            # 2. 回退到时间基础的同步（使用优化的方法）
            monitor.start_stage('time_based_sync')
            if self.is_first_sync(db, user) or force_full:
                stats = self._full_sync_with_optimization(db, user, monitor)
            else:
                latest_timestamp = self._get_latest_email_timestamp(db, user)
                if latest_timestamp:
                    buffer_time = latest_timestamp - timedelta(hours=8)
                    query = f"after:{int(buffer_time.timestamp())}"
                    stats = self.sync_emails_by_query_with_monitoring(db, user, query, 500)
                else:
                    stats = self._full_sync_with_optimization(db, user, monitor)
            
            # 3. 获取并保存新的history_id
            try:
                current_history_id = gmail_service.get_current_history_id(user)
                user.last_history_id = current_history_id
                user.last_history_sync = datetime.now(timezone.utc)
                db.add(user)
                db.commit()
                logger.info(f"Updated historyId to {current_history_id} for user {user.id}")
            except Exception as e:
                logger.warning(f"Failed to update history_id: {e}")
                
            monitor.end_stage('time_based_sync')
            return stats
            
        except Exception as e:
            monitor.record_error('smart_sync', e)
            raise
        finally:
            # 记录性能报告
            report = monitor.get_report()
            logger.info(f"Smart sync completed: {report}")
    
    def _full_sync_with_optimization(
        self, 
        db: Session, 
        user: User, 
        monitor: 'SyncPerformanceMonitor'
    ) -> Dict[str, int]:
        """优化的全量同步实现
        
        这是原有_full_sync_with_pagination方法的简化优化版本
        
        Args:
            db: 数据库会话
            user: 用户对象
            monitor: 性能监控器
            
        Returns:
            同步统计信息
        """
        # TODO: 实现优化的全量同步逻辑
        # 暂时使用现有的sync_emails_by_query_with_monitoring作为fallback
        return self.sync_emails_by_query_with_monitoring(db, user, "newer_than:30d", 500)


# Global email sync service instance
email_sync_service = EmailSyncService()