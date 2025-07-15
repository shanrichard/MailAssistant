"""
Authentication API routes
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from ..core.database import get_db
from ..core.security import jwt_manager
from ..core.logging import get_logger
from ..services.oauth_service import oauth_token_manager
from ..models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
logger = get_logger(__name__)


class GoogleAuthRequest(BaseModel):
    """Google OAuth authentication request"""
    code: str


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class AuthStatus(BaseModel):
    """Authentication status response"""
    user: Dict[str, Any]
    gmail_connected: bool


@router.get("/google-auth-url")
async def get_google_auth_url() -> Dict[str, str]:
    """Get Google OAuth authorization URL"""
    try:
        auth_url, state = oauth_token_manager.get_authorization_url()
        logger.info("Generated Google auth URL", state=state)
        return {
            "authorization_url": auth_url,
            "state": state
        }
    except Exception as e:
        logger.error("Failed to generate Google auth URL", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate authorization URL"
        )


@router.post("/google", response_model=TokenResponse)
async def google_oauth_callback(
    request: GoogleAuthRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Handle Google OAuth callback"""
    try:
        # Exchange code for tokens
        oauth_result = oauth_token_manager.exchange_code_for_tokens(request.code)
        
        tokens = oauth_result['tokens']
        user_info = oauth_result['user_info']
        
        # Find or create user
        user = db.query(User).filter(User.google_id == user_info['id']).first()
        
        if not user:
            # Create new user
            user = User(
                email=user_info['email'],
                google_id=user_info['id'],
                name=user_info.get('name', ''),
                avatar_url=user_info.get('picture', ''),
                gmail_tokens=tokens  # This will be encrypted in the model
            )
            db.add(user)
            logger.info("Created new user", user_email=user_info['email'])
        else:
            # Update existing user
            user.name = user_info.get('name', user.name)
            user.avatar_url = user_info.get('picture', user.avatar_url)
            user.gmail_tokens = tokens  # This will be encrypted in the model
            logger.info("Updated existing user", user_email=user_info['email'])
        
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        jwt_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "access"
        }
        access_token = jwt_manager.create_access_token(jwt_data)
        
        # Prepare user data for response
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "gmail_connected": True
        }
        
        logger.info("Successfully authenticated user", user_id=user.id)
        return TokenResponse(
            access_token=access_token,
            user=user_data
        )
        
    except Exception as e:
        logger.error("Google OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TokenResponse:
    """Refresh JWT token"""
    try:
        # Verify current token
        payload = jwt_manager.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new JWT token
        jwt_data = {
            "sub": str(user.id),
            "email": user.email,
            "type": "access"
        }
        new_access_token = jwt_manager.create_access_token(jwt_data)
        
        # Prepare user data
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "gmail_connected": bool(user.gmail_tokens)
        }
        
        logger.info("Successfully refreshed token", user_id=user.id)
        return TokenResponse(
            access_token=new_access_token,
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.delete("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Logout user and revoke tokens"""
    try:
        # Verify current token
        payload = jwt_manager.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if user and user.gmail_tokens:
            # Revoke Gmail tokens
            oauth_token_manager.revoke_token(user.gmail_tokens)
            
            # Clear stored tokens
            user.gmail_tokens = None
            db.commit()
        
        logger.info("Successfully logged out user", user_id=user_id)
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/status", response_model=AuthStatus)
async def get_auth_status(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AuthStatus:
    """Get current authentication status"""
    try:
        # Verify token
        payload = jwt_manager.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Check Gmail token status
        gmail_connected = False
        if user.gmail_tokens:
            gmail_connected = oauth_token_manager.validate_token(user.gmail_tokens)
            
            # If token is invalid, try to refresh it
            if not gmail_connected:
                new_tokens, refreshed = oauth_token_manager.refresh_token_if_needed(user.gmail_tokens)
                if refreshed and new_tokens:
                    user.gmail_tokens = new_tokens
                    db.commit()
                    gmail_connected = True
        
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url
        }
        
        return AuthStatus(
            user=user_data,
            gmail_connected=gmail_connected
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get auth status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get authentication status"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user (dependency)"""
    try:
        payload = jwt_manager.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get current user", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

async def get_current_user_from_token(token: str, db: Session = None) -> User:
    """从token获取当前用户（用于WebSocket认证）"""
    if not db:
        db = next(get_db())
        
    try:
        # Verify token
        payload = jwt_manager.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed"
        )