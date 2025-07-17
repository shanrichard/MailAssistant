"""
OAuth Flow Manager with Database Storage
使用PostgreSQL数据库存储OAuth会话，解决开发模式热重载导致会话丢失的问题
"""

import os
import uuid
import json
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from ..core.config import settings
from ..core.logging import get_logger
from ..core.database import get_db
from ..models.oauth_session import OAuthSession, SessionStatus

logger = get_logger(__name__)


class OAuthFlowManager:
    """
    OAuth Flow Manager with Database Backend
    
    使用PostgreSQL数据库存储OAuth会话，解决开发模式热重载问题：
    1. 每个OAuth请求使用唯一的session_id
    2. Flow对象在整个OAuth流程中保持一致
    3. 正确的状态管理和过期清理
    4. 数据库持久化存储，不受进程重启影响
    """
    
    def __init__(self):
        # Google OAuth配置
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.scopes = [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        
        # Session配置
        self.session_ttl_minutes = 30  # 30分钟
        
        logger.info("OAuth Flow Manager (Database) initialized", 
                   client_id=self.client_id, 
                   redirect_uri=self.redirect_uri,
                   scopes=len(self.scopes))
    
    def _serialize_flow(self, flow: Flow) -> Dict[str, Any]:
        """序列化Flow对象为可存储的格式"""
        return {
            'client_config': {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            'scopes': self.scopes,
            'redirect_uri': self.redirect_uri,
            'state': flow.state if hasattr(flow, 'state') else None
        }
    
    def _deserialize_flow(self, flow_data: Dict[str, Any]) -> Flow:
        """从存储格式反序列化Flow对象"""
        flow = Flow.from_client_config(
            flow_data['client_config'],
            scopes=flow_data['scopes'],
            redirect_uri=flow_data['redirect_uri']
        )
        
        # 恢复state
        if flow_data.get('state'):
            flow.state = flow_data['state']
            
        return flow
    
    def create_session(self) -> Tuple[str, str, str]:
        """
        创建新的OAuth会话
        
        Returns:
            Tuple[session_id, authorization_url, state]
        """
        # 生成唯一session ID
        session_id = str(uuid.uuid4())
        
        # 创建Flow对象
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri],
                }
            },
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        # 生成授权URL
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # 创建数据库会话
        db = next(get_db())
        try:
            # 清理过期会话
            self._cleanup_expired_sessions(db)
            
            # 创建新会话
            oauth_session = OAuthSession(
                session_id=session_id,
                status=SessionStatus.PENDING,
                flow_data=json.dumps(self._serialize_flow(flow)),
                authorization_url=authorization_url,
                state=state,
                expires_at=datetime.utcnow() + timedelta(minutes=self.session_ttl_minutes)
            )
            
            db.add(oauth_session)
            db.commit()
            
            logger.info("New OAuth session created in database", 
                       session_id=session_id,
                       state=state,
                       status=SessionStatus.PENDING.value,
                       expires_at=oauth_session.expires_at.isoformat())
            
            return session_id, authorization_url, state
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to create OAuth session", error=str(e))
            raise
        finally:
            db.close()
    
    def exchange_code_for_tokens(self, session_id: str, authorization_response: str) -> Dict[str, Any]:
        """
        使用authorization_response交换tokens
        
        Args:
            session_id: OAuth会话ID
            authorization_response: 完整的授权响应URL
            
        Returns:
            Dict containing tokens and user_info
        """
        logger.info("Starting token exchange", 
                   session_id=session_id,
                   authorization_response_preview=authorization_response[:100] + "...")
        
        db = next(get_db())
        try:
            # 获取会话
            oauth_session = db.query(OAuthSession).filter(
                OAuthSession.session_id == session_id
            ).first()
            
            if not oauth_session:
                logger.error("Session not found in database",
                            session_id=session_id)
                raise ValueError(f"Invalid or expired session: {session_id}")
            
            # 检查会话是否过期
            if oauth_session.is_expired():
                logger.error("Session expired",
                            session_id=session_id,
                            expires_at=oauth_session.expires_at.isoformat())
                raise ValueError(f"Session expired: {session_id}")
            
            # 检查会话状态
            if oauth_session.status != SessionStatus.PENDING:
                logger.error("Session not in PENDING status",
                            session_id=session_id,
                            current_status=oauth_session.status.value)
                raise ValueError(f"Session {session_id} has already been used or is invalid")
            
            logger.info("Session found in database for token exchange",
                       session_id=session_id,
                       session_status=oauth_session.status.value,
                       session_state=oauth_session.state)
            
            try:
                # 重建Flow对象
                flow_data = json.loads(oauth_session.flow_data)
                flow = self._deserialize_flow(flow_data)
                
                logger.info("Calling flow.fetch_token with authorization_response",
                           session_id=session_id)
                
                # 使用authorization_response交换tokens
                flow.fetch_token(authorization_response=authorization_response)
                
                credentials = flow.credentials
                
                # 获取用户信息
                user_info = self._get_user_info(credentials)
                
                # 准备token数据
                token_data = {
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes,
                    'expiry': credentials.expiry.isoformat() if credentials.expiry else None
                }
                
                # 更新会话状态为CONSUMED
                oauth_session.status = SessionStatus.CONSUMED
                db.commit()
                
                logger.info("Successfully exchanged authorization_response for tokens",
                           session_id=session_id,
                           user_email=user_info.get('email'),
                           scopes=len(credentials.scopes))
                
                return {
                    'tokens': token_data,
                    'user_info': user_info
                }
                
            except Exception as e:
                error_str = str(e)
                logger.error("Failed to exchange authorization_response", 
                            session_id=session_id,
                            error=error_str,
                            error_type=type(e).__name__)
                
                # 标记会话为失败
                oauth_session.status = SessionStatus.EXPIRED
                db.commit()
                
                # 提供更有用的错误信息
                if "invalid_grant" in error_str:
                    raise Exception("invalid_grant: Authorization code has expired or been used already. Please try logging in again.")
                else:
                    raise Exception(f"Failed to exchange authorization_response: {error_str}")
                    
        except Exception as e:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_session_status(self, session_id: str) -> Optional[str]:
        """获取会话状态"""
        db = next(get_db())
        try:
            oauth_session = db.query(OAuthSession).filter(
                OAuthSession.session_id == session_id
            ).first()
            
            if not oauth_session:
                return None
                
            return oauth_session.status.value
        finally:
            db.close()
    
    def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            # 构建OAuth2服务
            service = build('oauth2', 'v2', credentials=credentials)
            
            # 获取用户信息
            user_info = service.userinfo().get().execute()
            
            logger.info("Retrieved user info", user_email=user_info.get('email'))
            
            return user_info
        except Exception as e:
            logger.error("Failed to get user info", error=str(e))
            raise Exception(f"Failed to get user info: {str(e)}")
    
    def _cleanup_expired_sessions(self, db: Session):
        """清理过期会话"""
        try:
            expired_count = db.query(OAuthSession).filter(
                OAuthSession.expires_at < datetime.utcnow()
            ).delete()
            
            if expired_count > 0:
                db.commit()
                logger.info("Cleaned up expired sessions", count=expired_count)
        except Exception as e:
            logger.error("Failed to cleanup expired sessions", error=str(e))
            db.rollback()