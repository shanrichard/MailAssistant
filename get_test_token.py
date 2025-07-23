#!/usr/bin/env python3
"""获取测试用的认证令牌"""
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import JWTManager
import os

TEST_USER_EMAIL = os.environ.get('TEST_USER_EMAIL', 'single.shan@gmail.com')

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
    if user:
        token_manager = JWTManager()
        token = token_manager.create_access_token(data={"sub": user.email})
        print(f"export TEST_AUTH_TOKEN={token}")
    else:
        print(f"用户 {TEST_USER_EMAIL} 不存在")
except Exception as e:
    print(f"错误: {e}")
finally:
    db.close()
