"""
Gmail API service for email operations
"""
import json
import base64
import email
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


# Global Gmail service instance
gmail_service = GmailService()