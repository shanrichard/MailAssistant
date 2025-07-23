"""
OAuth service for Google authentication and token management
Google OAuth 2.0 认证服务 - 重构版本使用OAuthFlowManager
"""

import json
import secrets
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from ..core.config import settings
from ..utils.datetime_utils import utc_now
from ..core.security import encryption_manager
from ..core.logging import get_logger
from .oauth_flow_manager import oauth_flow_manager

logger = get_logger(__name__)


class OAuthTokenManager:
    """
    OAuth Token管理器 - 重构版本
    
    现在使用OAuthFlowManager来处理Flow对象的生命周期，
    确保符合Google OAuth Client Library最佳实践。
    
    主要改进：
    1. 使用OAuthFlowManager管理Flow对象
    2. 使用authorization_response进行token exchange
    3. 更好的错误处理和日志记录
    """
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        
        logger.info("OAuth Token Manager initialized (using OAuthFlowManager)", 
                   client_id=self.client_id, 
                   redirect_uri=self.redirect_uri)
    
    def get_authorization_url(self) -> Tuple[str, str]:
        """
        获取Google OAuth授权URL
        
        Returns:
            Tuple[authorization_url, session_id]: 授权URL和会话ID
        """
        try:
            session_id, authorization_url, state = oauth_flow_manager.create_session()
            
            logger.info("Generated authorization URL", 
                       session_id=session_id,
                       state=state)
            
            return authorization_url, session_id
            
        except Exception as e:
            logger.error("Failed to generate authorization URL", error=str(e))
            raise Exception(f"Failed to generate authorization URL: {str(e)}")
    
    def exchange_code_for_tokens(self, authorization_response: str, session_id: str) -> Dict[str, Any]:
        """
        使用authorization_response交换tokens
        
        Args:
            authorization_response: 完整的授权响应URL
            session_id: OAuth会话ID
            
        Returns:
            Dict containing tokens and user_info
        """
        try:
            result = oauth_flow_manager.exchange_code_for_tokens(
                session_id=session_id,
                authorization_response=authorization_response
            )
            
            logger.info("Successfully exchanged authorization_response for tokens", 
                       session_id=session_id,
                       user_email=result['user_info'].get('email'))
            
            return result
            
        except Exception as e:
            logger.error("Failed to exchange authorization_response for tokens", 
                        session_id=session_id,
                        error=str(e))
            raise Exception(f"Failed to exchange authorization_response for tokens: {str(e)}")
    
    def refresh_token_if_needed(self, encrypted_tokens: str) -> Tuple[Optional[str], bool]:
        """
        检查并刷新token（如果需要）
        
        Args:
            encrypted_tokens: 加密的token数据
            
        Returns:
            Tuple[new_encrypted_tokens, was_refreshed]: 新的加密token和是否刷新的标志
        """
        try:
            # 解密token数据
            token_dict = encryption_manager.decrypt_json(encrypted_tokens)
            
            # 创建Credentials对象（兼容不同的token字段名）
            access_token = token_dict.get('access_token') or token_dict.get('token')
            credentials = Credentials(
                token=access_token,
                refresh_token=token_dict.get('refresh_token'),
                token_uri=token_dict.get('token_uri'),
                client_id=token_dict.get('client_id'),
                client_secret=token_dict.get('client_secret'),
                scopes=token_dict.get('scopes')
            )
            
            # 检查是否需要刷新
            if credentials.expired and credentials.refresh_token:
                logger.info("Token expired, refreshing...")
                
                # 刷新token
                request = Request()
                credentials.refresh(request)
                
                # 更新token数据
                updated_token_data = {
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_uri': credentials.token_uri,
                    'client_id': credentials.client_id,
                    'client_secret': credentials.client_secret,
                    'scopes': credentials.scopes,
                    'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                    'refreshed_at': utc_now().isoformat()
                }
                
                # 加密更新后的token数据
                new_encrypted_tokens = encryption_manager.encrypt_json(updated_token_data)
                
                logger.info("Token refreshed successfully")
                return new_encrypted_tokens, True
            else:
                logger.debug("Token is still valid, no refresh needed")
                return None, False
                
        except Exception as e:
            logger.error("Failed to refresh token", error=str(e))
            raise Exception(f"Failed to refresh token: {str(e)}")
    
    def validate_token(self, encrypted_tokens: str) -> bool:
        """
        验证token是否有效
        
        Args:
            encrypted_tokens: 加密的token数据
            
        Returns:
            bool: token是否有效
        """
        try:
            # 解密token数据
            token_dict = encryption_manager.decrypt_json(encrypted_tokens)
            
            # 创建Credentials对象（兼容不同的token字段名）
            access_token = token_dict.get('access_token') or token_dict.get('token')
            credentials = Credentials(
                token=access_token,
                refresh_token=token_dict.get('refresh_token'),
                token_uri=token_dict.get('token_uri'),
                client_id=token_dict.get('client_id'),
                client_secret=token_dict.get('client_secret'),
                scopes=token_dict.get('scopes')
            )
            
            # 尝试使用token获取用户信息
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            logger.debug("Token validation successful", user_email=user_info.get('email'))
            return True
            
        except Exception as e:
            logger.warning("Token validation failed", error=str(e))
            return False
    
    def get_user_info_from_token(self, encrypted_tokens: str) -> Dict[str, Any]:
        """
        从token获取用户信息
        
        Args:
            encrypted_tokens: 加密的token数据
            
        Returns:
            Dict: 用户信息
        """
        try:
            # 解密token数据
            token_dict = encryption_manager.decrypt_json(encrypted_tokens)
            
            # 创建Credentials对象（兼容不同的token字段名）
            access_token = token_dict.get('access_token') or token_dict.get('token')
            credentials = Credentials(
                token=access_token,
                refresh_token=token_dict.get('refresh_token'),
                token_uri=token_dict.get('token_uri'),
                client_id=token_dict.get('client_id'),
                client_secret=token_dict.get('client_secret'),
                scopes=token_dict.get('scopes')
            )
            
            # 获取用户信息
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            logger.debug("Retrieved user info from token", user_email=user_info.get('email'))
            return user_info
            
        except Exception as e:
            logger.error("Failed to get user info from token", error=str(e))
            raise Exception(f"Failed to get user info from token: {str(e)}")
    
    def revoke_token(self, encrypted_tokens: str) -> bool:
        """
        撤销token
        
        Args:
            encrypted_tokens: 加密的token数据
            
        Returns:
            bool: 是否成功撤销
        """
        try:
            # 解密token数据
            token_dict = encryption_manager.decrypt_json(encrypted_tokens)
            
            # 创建Credentials对象（兼容不同的token字段名）
            access_token = token_dict.get('access_token') or token_dict.get('token')
            credentials = Credentials(
                token=access_token,
                refresh_token=token_dict.get('refresh_token'),
                token_uri=token_dict.get('token_uri'),
                client_id=token_dict.get('client_id'),
                client_secret=token_dict.get('client_secret'),
                scopes=token_dict.get('scopes')
            )
            
            # 撤销token
            request = Request()
            credentials.revoke(request)
            
            logger.info("Token revoked successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to revoke token", error=str(e))
            return False


# 全局OAuth Token Manager实例
oauth_token_manager = OAuthTokenManager()