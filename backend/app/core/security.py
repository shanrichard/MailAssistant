"""
Security utilities for JWT tokens and encryption
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
import json
from .config import settings


class JWTManager:
    """JWT token management"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = settings.jwt_expire_minutes
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        from ..utils.datetime_utils import utc_now
        
        if expires_delta:
            expire = utc_now() + expires_delta
        else:
            expire = utc_now() + timedelta(minutes=self.expire_minutes)
        
        to_encode.update({"exp": expire, "iat": utc_now()})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode JWT token without verification (for debugging)"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except jwt.JWTError:
            return None


class EncryptionManager:
    """Encryption/decryption for sensitive data"""
    
    def __init__(self):
        # Ensure the key is properly formatted for Fernet
        key = settings.encryption_key.encode()
        # If key is not 32 bytes, derive it
        if len(key) != 32:
            key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        else:
            key = base64.urlsafe_b64encode(key)
        
        self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """Encrypt JSON data"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt JSON data"""
        decrypted_str = self.decrypt(encrypted_data)
        return json.loads(decrypted_str)


class PasswordManager:
    """Password hashing and verification"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def hash_password(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        return self.pwd_context.verify(plain_password, hashed_password)


# Global instances
jwt_manager = JWTManager()
encryption_manager = EncryptionManager()
password_manager = PasswordManager()