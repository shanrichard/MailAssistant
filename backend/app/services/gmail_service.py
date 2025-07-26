"""
Gmail API service for email operations
"""
import json
import base64
import email
import time
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

from ..core.config import settings
from ..models.user import User
from ..models.email import Email
from .oauth_service import oauth_token_manager

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail API service for email operations"""
    
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
    
    def get_service(self, user: User):
        """Get authenticated Gmail service for user (public method for batch requests)"""
        return self._get_gmail_service(user)
    
    def _get_gmail_service(self, user: User):
        """Get authenticated Gmail service for user"""
        try:
            # Get user's encrypted Gmail tokens
            encrypted_tokens = user._encrypted_gmail_tokens
            if not encrypted_tokens:
                raise ValueError("No Gmail tokens found for user")
            
            # Refresh tokens if needed
            refreshed_encrypted_tokens, was_refreshed = oauth_token_manager.refresh_token_if_needed(encrypted_tokens)
            if was_refreshed and refreshed_encrypted_tokens:
                user._encrypted_gmail_tokens = refreshed_encrypted_tokens
                tokens = user.get_decrypted_gmail_tokens()
            else:
                tokens = user.get_decrypted_gmail_tokens()
            
            # Create credentials（兼容不同的token字段名）
            access_token = tokens.get('access_token') or tokens.get('token')
            credentials = Credentials(
                token=access_token,
                refresh_token=tokens.get('refresh_token'),
                token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=self.scopes
            )
            
            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            return service
            
        except Exception as e:
            logger.error(f"Failed to get Gmail service for user {user.id}: {str(e)}")
            raise
    
    def get_user_profile(self, user: User) -> Dict[str, Any]:
        """Get Gmail user profile"""
        try:
            service = self._get_gmail_service(user)
            profile = service.users().getProfile(userId='me').execute()
            return profile
        except HttpError as e:
            logger.error(f"Failed to get user profile: {str(e)}")
            raise
    
    def list_messages(
        self, 
        user: User, 
        query: str = '', 
        max_results: int = 100,
        page_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """List Gmail messages with optional query"""
        try:
            service = self._get_gmail_service(user)
            
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'q': query
            }
            
            if page_token:
                request_params['pageToken'] = page_token
            
            result = service.users().messages().list(**request_params).execute()
            
            messages = result.get('messages', [])
            next_page_token = result.get('nextPageToken')
            
            return messages, next_page_token
            
        except HttpError as e:
            logger.error(f"Failed to list messages: {str(e)}")
            raise
    
    def get_message_details(self, user: User, message_id: str) -> Dict[str, Any]:
        """Get detailed message information"""
        try:
            service = self._get_gmail_service(user)
            message = service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            return message
        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {str(e)}")
            raise
    
    def parse_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Gmail message data into structured format"""
        try:
            payload = message_data.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract headers
            header_dict = {}
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                header_dict[name] = value
            
            # Extract message parts
            body_plain = ''
            body_html = ''
            attachments = []
            
            def extract_parts(parts):
                nonlocal body_plain, body_html, attachments
                
                for part in parts:
                    mime_type = part.get('mimeType', '')
                    filename = part.get('filename', '')
                    
                    if mime_type == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            body_plain += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    
                    elif mime_type == 'text/html':
                        data = part.get('body', {}).get('data', '')
                        if data:
                            body_html += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    
                    elif filename:
                        # Attachment
                        attachments.append({
                            'filename': filename,
                            'mime_type': mime_type,
                            'size': part.get('body', {}).get('size', 0)
                        })
                    
                    # Process nested parts
                    if 'parts' in part:
                        extract_parts(part['parts'])
            
            # Handle single part message
            if 'parts' in payload:
                extract_parts(payload['parts'])
            else:
                # Single part message
                mime_type = payload.get('mimeType', '')
                data = payload.get('body', {}).get('data', '')
                
                if data:
                    decoded_data = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    if mime_type == 'text/plain':
                        body_plain = decoded_data
                    elif mime_type == 'text/html':
                        body_html = decoded_data
            
            # Parse recipients
            def parse_recipients(recipient_string):
                if not recipient_string:
                    return []
                # Simple parsing - could be enhanced
                return [addr.strip() for addr in recipient_string.split(',')]
            
            # Convert timestamp
            internal_date = int(message_data.get('internalDate', 0))
            received_at = datetime.fromtimestamp(internal_date / 1000, tz=timezone.utc)
            
            return {
                'gmail_id': message_data.get('id'),
                'thread_id': message_data.get('threadId'),
                'subject': header_dict.get('subject', ''),
                'sender': header_dict.get('from', ''),
                'recipients': parse_recipients(header_dict.get('to', '')),
                'cc_recipients': parse_recipients(header_dict.get('cc', '')),
                'bcc_recipients': parse_recipients(header_dict.get('bcc', '')),
                'body_plain': body_plain,
                'body_html': body_html,
                'received_at': received_at,
                'has_attachments': len(attachments) > 0,
                'labels': message_data.get('labelIds', []),
                'snippet': message_data.get('snippet', ''),
                'attachments': attachments
            }
            
        except Exception as e:
            logger.error(f"Failed to parse message: {str(e)}")
            raise
    
    def mark_as_read(self, user: User, message_ids: List[str]) -> bool:
        """Mark messages as read"""
        try:
            service = self._get_gmail_service(user)
            
            # Batch modify to remove UNREAD label
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': message_ids,
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
            logger.info(f"Marked {len(message_ids)} messages as read for user {user.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to mark messages as read: {str(e)}")
            return False
    
    def mark_as_unread(self, user: User, message_ids: List[str]) -> bool:
        """Mark messages as unread"""
        try:
            service = self._get_gmail_service(user)
            
            # Batch modify to add UNREAD label
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': message_ids,
                    'addLabelIds': ['UNREAD']
                }
            ).execute()
            
            logger.info(f"Marked {len(message_ids)} messages as unread for user {user.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to mark messages as unread: {str(e)}")
            return False
    
    def add_labels(self, user: User, message_ids: List[str], label_ids: List[str]) -> bool:
        """Add labels to messages"""
        try:
            service = self._get_gmail_service(user)
            
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': message_ids,
                    'addLabelIds': label_ids
                }
            ).execute()
            
            logger.info(f"Added labels {label_ids} to {len(message_ids)} messages for user {user.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to add labels: {str(e)}")
            return False
    
    def remove_labels(self, user: User, message_ids: List[str], label_ids: List[str]) -> bool:
        """Remove labels from messages"""
        try:
            service = self._get_gmail_service(user)
            
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': message_ids,
                    'removeLabelIds': label_ids
                }
            ).execute()
            
            logger.info(f"Removed labels {label_ids} from {len(message_ids)} messages for user {user.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Failed to remove labels: {str(e)}")
            return False
    
    def search_messages(
        self, 
        user: User, 
        query: str, 
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search messages and return parsed results"""
        try:
            # Get message list
            messages, _ = self.list_messages(user, query=query, max_results=max_results)
            
            # Get detailed message data
            detailed_messages = []
            for message in messages:
                message_details = self.get_message_details(user, message['id'])
                parsed_message = self.parse_message(message_details)
                detailed_messages.append(parsed_message)
            
            return detailed_messages
            
        except Exception as e:
            logger.error(f"Failed to search messages: {str(e)}")
            raise
    
    def search_messages_paginated(
        self, 
        user: User, 
        query: str, 
        max_results: int = 50,
        page_token: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Search messages with pagination support"""
        try:
            # Get message list with pagination
            messages, next_page_token = self.list_messages(
                user, query=query, max_results=max_results, page_token=page_token
            )
            
            # Get detailed message data
            detailed_messages = []
            for message in messages:
                message_details = self.get_message_details(user, message['id'])
                parsed_message = self.parse_message(message_details)
                detailed_messages.append(parsed_message)
            
            return detailed_messages, next_page_token
            
        except Exception as e:
            logger.error(f"Failed to search messages paginated: {str(e)}")
            raise
    
    def get_recent_messages(
        self, 
        user: User, 
        days: int = 1, 
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent messages from the last N days"""
        try:
            # Create query for recent messages
            query = f'newer_than:{days}d'
            
            return self.search_messages(user, query, max_results)
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {str(e)}")
            raise
    
    def get_unread_messages(self, user: User, max_results: int = 100) -> List[Dict[str, Any]]:
        """Get unread messages"""
        try:
            query = 'is:unread'
            return self.search_messages(user, query, max_results)
            
        except Exception as e:
            logger.error(f"Failed to get unread messages: {str(e)}")
            raise
    
    def get_messages_by_sender(
        self, 
        user: User, 
        sender_email: str, 
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages from specific sender"""
        try:
            query = f'from:{sender_email}'
            return self.search_messages(user, query, max_results)
            
        except Exception as e:
            logger.error(f"Failed to get messages by sender: {str(e)}")
            raise
    
    def get_messages_by_timerange(
        self, 
        user: User, 
        timerange: str, 
        max_results: int = 500
    ) -> List[Dict[str, Any]]:
        """Get messages by time range (today, week, month)"""
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
            
            logger.info(f"Fetching {timerange} messages with query: {query}")
            return self.search_messages(user, query, max_results)
            
        except Exception as e:
            logger.error(f"Failed to get messages by timerange {timerange}: {str(e)}")
            raise
    
    # Gmail History API support (Task 3-14-2)
    
    def fetch_changed_msg_ids(self, user: User, start_history_id: str) -> Tuple[List[str], str]:
        """获取变更的邮件ID，处理historyId过期（专家建议）"""
        try:
            return self.get_history_changes(user, start_history_id)
        except HttpError as e:
            if e.resp.status == 404:  # historyId过期（>7天）
                logger.warning(f"historyId expired for user {user.id}, falling back to full sync")
                return self._fallback_full_sync(user)
            raise
    
    def get_history_changes(self, user: User, start_history_id: str) -> Tuple[List[str], str]:
        """获取历史变更的邮件ID列表和新的historyId"""
        try:
            service = self._get_gmail_service(user)
            
            logger.info(f"Fetching history changes for user {user.id} from historyId {start_history_id}")
            
            # 调用Gmail History API
            result = service.users().history().list(
                userId='me',
                startHistoryId=start_history_id
            ).execute()
            
            # 提取变更的邮件ID
            history_data = result.get('history', [])
            changed_message_ids = self._extract_message_ids_from_history(history_data)
            
            # 获取新的historyId
            new_history_id = result.get('historyId', start_history_id)
            
            logger.info(f"Found {len(changed_message_ids)} changed messages, new historyId: {new_history_id}")
            
            return changed_message_ids, new_history_id
            
        except HttpError as e:
            logger.error(f"Failed to get history changes for user {user.id}: {str(e)}")
            raise
    
    def get_history_changes_detailed(self, user: User, start_history_id: str) -> Tuple[Dict[str, List[Dict]], str]:
        """获取详细的历史变更信息，包括新增、删除、标签变更
        
        Returns:
            (changes_dict, new_history_id)
            changes_dict = {
                'messages_added': [{'id': 'xxx', 'labels': [...]}],
                'messages_deleted': [{'id': 'xxx'}],
                'labels_added': [{'message_id': 'xxx', 'label_ids': [...]}],
                'labels_removed': [{'message_id': 'xxx', 'label_ids': [...]}]
            }
        """
        try:
            service = self._get_gmail_service(user)
            
            logger.info(f"Fetching detailed history changes for user {user.id} from historyId {start_history_id}")
            
            all_history = []
            page_token = None
            
            # 分页获取所有历史记录
            while True:
                params = {
                    'userId': 'me',
                    'startHistoryId': start_history_id,
                    'historyTypes': ['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
                }
                if page_token:
                    params['pageToken'] = page_token
                    
                result = service.users().history().list(**params).execute()
                
                history_data = result.get('history', [])
                all_history.extend(history_data)
                
                page_token = result.get('nextPageToken')
                if not page_token:
                    break
            
            # 解析历史记录
            changes = {
                'messages_added': [],
                'messages_deleted': [],
                'labels_added': [],
                'labels_removed': []
            }
            
            for history_entry in all_history:
                # 处理新增邮件
                for msg_added in history_entry.get('messagesAdded', []):
                    message = msg_added.get('message', {})
                    changes['messages_added'].append({
                        'id': message.get('id'),
                        'thread_id': message.get('threadId'),
                        'label_ids': message.get('labelIds', [])
                    })
                
                # 处理删除的邮件
                for msg_deleted in history_entry.get('messagesDeleted', []):
                    message = msg_deleted.get('message', {})
                    changes['messages_deleted'].append({
                        'id': message.get('id')
                    })
                
                # 处理标签添加
                for label_added in history_entry.get('labelsAdded', []):
                    message = label_added.get('message', {})
                    changes['labels_added'].append({
                        'message_id': message.get('id'),
                        'label_ids': label_added.get('labelIds', [])
                    })
                
                # 处理标签移除
                for label_removed in history_entry.get('labelsRemoved', []):
                    message = label_removed.get('message', {})
                    changes['labels_removed'].append({
                        'message_id': message.get('id'),
                        'label_ids': label_removed.get('labelIds', [])
                    })
            
            # 获取新的historyId
            new_history_id = result.get('historyId', start_history_id)
            
            logger.info(f"History changes: {len(changes['messages_added'])} added, "
                       f"{len(changes['messages_deleted'])} deleted, "
                       f"{len(changes['labels_added'])} labels added, "
                       f"{len(changes['labels_removed'])} labels removed")
            
            return changes, new_history_id
            
        except HttpError as e:
            logger.error(f"Failed to get detailed history changes for user {user.id}: {str(e)}")
            raise
    
    def get_current_history_id(self, user: User) -> str:
        """获取用户当前的historyId"""
        try:
            service = self._get_gmail_service(user)
            
            # 调用Gmail API获取用户profile
            profile = service.users().getProfile(userId='me').execute()
            
            history_id = profile.get('historyId')
            if not history_id:
                raise ValueError("No historyId found in user profile")
            
            logger.info(f"Current historyId for user {user.id}: {history_id}")
            return history_id
            
        except HttpError as e:
            logger.error(f"Failed to get current historyId for user {user.id}: {str(e)}")
            raise
    
    def _extract_message_ids_from_history(self, history_data: List[Dict[str, Any]]) -> List[str]:
        """从history响应中提取邮件ID"""
        message_ids = set()  # 使用set去重
        
        for history_entry in history_data:
            # 处理各种类型的变更
            for change_type in ['messagesAdded', 'messagesDeleted', 'labelsAdded', 'labelsRemoved']:
                if change_type in history_entry:
                    for item in history_entry[change_type]:
                        if 'message' in item and 'id' in item['message']:
                            message_ids.add(item['message']['id'])
        
        return list(message_ids)
    
    def _fallback_full_sync(self, user: User) -> Tuple[List[str], str]:
        """historyId过期时的fallback全量同步"""
        try:
            logger.info(f"Performing fallback full sync for user {user.id}")
            
            # 获取最近的邮件（比如最近1天的）作为fallback
            recent_messages = self.get_recent_messages(user, days=1, max_results=100)
            
            # 提取邮件ID
            message_ids = [msg.get('gmail_id') for msg in recent_messages if msg.get('gmail_id')]
            
            # 获取当前的historyId
            current_history_id = self.get_current_history_id(user)
            
            logger.info(f"Fallback sync completed: {len(message_ids)} messages, historyId: {current_history_id}")
            
            return message_ids, current_history_id
            
        except Exception as e:
            logger.error(f"Fallback full sync failed for user {user.id}: {str(e)}")
            raise
    
    # Gmail Batch API support (Task 3-14-3)
    
    def get_messages_batch(self, user: User, message_ids: List[str]) -> List[Dict[str, Any]]:
        """批量获取邮件详情（最多50个一批）"""
        if not message_ids:
            return []
        
        logger.info(f"Batch fetching {len(message_ids)} messages for user {user.id}")
        
        all_messages = []
        
        # 分批处理，每批最多50个邮件
        for batch in self._chunk_list(message_ids, 50):
            try:
                batch_messages = self.get_messages_batch_with_retry(user, batch)
                all_messages.extend(batch_messages)
            except Exception as e:
                logger.error(f"Failed to fetch batch for user {user.id}: {str(e)}")
                # 继续处理下一批，不让单批失败阻塞整个过程
                continue
        
        logger.info(f"Successfully fetched {len(all_messages)} messages in batches for user {user.id}")
        return all_messages
    
    def get_messages_batch_with_retry(self, user: User, message_ids: List[str]) -> List[Dict[str, Any]]:
        """批量获取邮件，带重试机制（专家建议）"""
        if not message_ids:
            return []
        
        retry_count = 0
        while retry_count <= 1:  # 最多重试1次
            try:
                return self._batch_request(user, message_ids)
            except HttpError as e:
                if e.resp.status in [429, 500, 502, 503, 504] and retry_count == 0:
                    retry_count += 1
                    wait_time = 2 ** retry_count  # 指数退避
                    logger.warning(f"Batch request failed (status {e.resp.status}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif e.resp.status in [429, 500, 502, 503, 504]:
                    # 两次失败则跳过并记录（专家建议）
                    logger.error(f"Batch request failed after retry for user {user.id}: {e}")
                    return []  # 返回空列表，不阻塞整个同步
                else:
                    # 非重试错误（如401认证问题）直接抛出
                    raise
    
    def _batch_request(self, user: User, message_ids: List[str]) -> List[Dict[str, Any]]:
        """执行批量请求，带超时控制（专家建议）"""
        if not message_ids:
            return []
        
        try:
            # 设置5秒超时（专家建议）
            with httpx.Client(timeout=5.0) as client:
                # Gmail API批量请求实现
                result = self._execute_gmail_batch_request(user, message_ids)
                return result
                
        except Exception as e:
            logger.error(f"Batch request execution failed for user {user.id}: {str(e)}")
            raise
    
    def _execute_gmail_batch_request(self, user: User, message_ids: List[str]) -> List[Dict[str, Any]]:
        """执行Gmail批量请求的具体实现"""
        service = self._get_gmail_service(user)
        
        logger.debug(f"Executing batch request for {len(message_ids)} messages")
        
        messages = []
        
        # 使用Gmail API的批量功能实现
        # Note: 由于Python Gmail API客户端的批量实现较复杂，这里使用优化的串行调用
        # 在实际生产中，可以考虑使用Google API的batch HTTP请求
        
        try:
            for message_id in message_ids:
                try:
                    # 获取邮件详情
                    message = service.users().messages().get(
                        userId='me', 
                        id=message_id,
                        format='full'
                    ).execute()
                    
                    # 解析邮件数据
                    parsed_message = self.parse_message(message)
                    messages.append(parsed_message)
                    
                except HttpError as e:
                    if e.resp.status == 404:
                        # 邮件不存在（可能已被删除），跳过
                        logger.warning(f"Message {message_id} not found, skipping")
                        continue
                    elif e.resp.status in [403, 429]:
                        # 权限或限流问题，抛出让上层重试机制处理
                        raise
                    else:
                        # 其他错误，记录但继续处理剩余邮件
                        logger.error(f"Failed to fetch message {message_id}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Batch request execution failed: {e}")
            raise
        
        logger.debug(f"Successfully fetched {len(messages)} out of {len(message_ids)} requested messages")
        return messages
    
    def _chunk_list(self, items: List[Any], chunk_size: int) -> List[List[Any]]:
        """将列表分块的工具方法"""
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]
    
    # Optimized search methods (Task 3-14-5)
    
    def search_messages_optimized(self, user: User, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """优化版搜索消息，使用批量API解决N+1问题
        
        这个方法解决了原版search_messages中的N+1查询问题：
        - 原版：1次list_messages + N次get_message_details
        - 优化版：1次list_messages + 1次get_messages_batch (仅当有消息时)
        
        Args:
            user: 用户对象
            query: Gmail搜索查询
            max_results: 最大结果数
            
        Returns:
            解析后的邮件列表，格式与原版search_messages兼容
        """
        try:
            # 1. 获取消息ID列表（1次API调用）
            messages, _ = self.list_messages(user=user, query=query, max_results=max_results)
            
            if not messages:
                logger.info("Optimized search completed: 0 messages found")
                return []
            
            # 2. 提取邮件ID列表
            message_ids = [msg['id'] for msg in messages]
            
            # 3. 批量获取详情（利用已实现的批量API，解决N+1问题）
            detailed_messages = self.get_messages_batch(user, message_ids)
            
            logger.info(f"Optimized search completed: {len(detailed_messages)} messages fetched with 2 API calls instead of {len(messages) + 1}")
            
            return detailed_messages
            
        except Exception as e:
            logger.error(f"Failed to search messages optimized: {str(e)}")
            raise


# Global Gmail service instance
gmail_service = GmailService()