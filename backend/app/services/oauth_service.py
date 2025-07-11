"""
OAuth service for Google authentication and token management
"""
from typing import Optional, Dict, Any, Tuple
import time
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import httpx

from ..core.config import settings
from ..core.security import encryption_manager
from ..core.logging import get_logger

logger = get_logger(__name__)


class OAuthTokenManager:
    """Manages OAuth tokens with automatic refresh"""
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.scopes = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]
    
    def get_authorization_url(self) -> Tuple[str, str]:
        """Get authorization URL for OAuth flow"""
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
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        logger.info("Generated authorization URL", state=state)
        return authorization_url, state
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
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
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info
            user_info = self._get_user_info(credentials)
            
            # Prepare token data
            token_data = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                'created_at': datetime.utcnow().isoformat()
            }
            
            logger.info("Successfully exchanged code for tokens", user_email=user_info.get('email'))
            return {
                'tokens': token_data,
                'user_info': user_info
            }
            
        except Exception as e:
            logger.error("Failed to exchange code for tokens", error=str(e))
            raise Exception(f"Failed to exchange code for tokens: {str(e)}")
    
    def _get_user_info(self, credentials: Credentials) -> Dict[str, Any]:
        """Get user information from Google API"""
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            logger.error("Failed to get user info", error=str(e))
            raise Exception(f"Failed to get user info: {str(e)}")
    
    def refresh_token_if_needed(self, encrypted_tokens: str) -> Tuple[Optional[str], bool]:
        """
        Check if tokens need refresh and refresh if necessary
        Returns: (new_encrypted_tokens, was_refreshed)
        """
        try:
            # Decrypt tokens
            token_data = encryption_manager.decrypt_json(encrypted_tokens)
            
            # Check if token is expired or will expire soon (within 5 minutes)
            if not token_data.get('expiry'):
                logger.warning("Token has no expiry, cannot determine if refresh needed")
                return None, False
            
            expiry = datetime.fromisoformat(token_data['expiry'])
            now = datetime.utcnow()
            
            # If token expires within 5 minutes, refresh it
            if expiry <= now + timedelta(minutes=5):
                logger.info("Token needs refresh", expiry=expiry.isoformat())
                return self._refresh_access_token(token_data)
            
            logger.debug("Token is still valid", expiry=expiry.isoformat())
            return None, False
            
        except Exception as e:
            logger.error("Failed to check token expiry", error=str(e))
            return None, False
    
    def _refresh_access_token(self, token_data: Dict[str, Any]) -> Tuple[Optional[str], bool]:
        """Refresh access token using refresh token"""
        try:
            if not token_data.get('refresh_token'):
                logger.error("No refresh token available")
                return None, False
            
            # Create credentials object
            credentials = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            # Update token data
            token_data.update({
                'access_token': credentials.token,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None,
                'refreshed_at': datetime.utcnow().isoformat()
            })
            
            # Encrypt and return new tokens
            new_encrypted_tokens = encryption_manager.encrypt_json(token_data)
            
            logger.info("Successfully refreshed access token")
            return new_encrypted_tokens, True
            
        except Exception as e:
            logger.error("Failed to refresh access token", error=str(e))
            return None, False
    
    def validate_token(self, encrypted_tokens: str) -> bool:
        """Validate if token is valid and not expired"""
        try:
            token_data = encryption_manager.decrypt_json(encrypted_tokens)
            
            if not token_data.get('access_token'):
                return False
            
            # Check expiry
            if token_data.get('expiry'):
                expiry = datetime.fromisoformat(token_data['expiry'])
                if expiry <= datetime.utcnow():
                    return False
            
            # Try to make a simple API call to validate
            credentials = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            service = build('oauth2', 'v2', credentials=credentials)
            service.userinfo().get().execute()
            
            return True
            
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            return False
    
    def revoke_token(self, encrypted_tokens: str) -> bool:
        """Revoke OAuth token"""
        try:
            token_data = encryption_manager.decrypt_json(encrypted_tokens)
            access_token = token_data.get('access_token')
            
            if not access_token:
                return False
            
            # Revoke token
            response = httpx.post(
                'https://oauth2.googleapis.com/revoke',
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data={'token': access_token}
            )
            
            success = response.status_code == 200
            if success:
                logger.info("Successfully revoked token")
            else:
                logger.error("Failed to revoke token", status_code=response.status_code)
            
            return success
            
        except Exception as e:
            logger.error("Failed to revoke token", error=str(e))
            return False


# Global instance
oauth_token_manager = OAuthTokenManager()