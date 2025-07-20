#!/usr/bin/env python
"""
测试 checkpointer 相关错误
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User
from app.agents.conversation_handler import ConversationHandler
import asyncio

async def test_conversation_handler():
    """测试 ConversationHandler 初始化"""
    db = SessionLocal()
    try:
        # 获取测试用户
        user = db.query(User).filter(User.id == "60f2ccbd-d754-4fa0-aa4d-35a7d6551d38").first()
        if not user:
            print("用户不存在")
            return
        
        print(f"找到用户: {user.email}")
        
        # 创建 ConversationHandler
        print("创建 ConversationHandler...")
        try:
            handler = ConversationHandler(str(user.id), db, user)
            print("ConversationHandler 创建成功")
            
            # 测试简单的消息
            print("\n测试消息处理...")
            async for event in handler.stream_response("你好", "test-session"):
                print(f"收到事件: {event}")
                
        except Exception as e:
            print(f"错误类型: {type(e)}")
            print(f"错误消息: {str(e)}")
            print(f"错误详情: {repr(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_conversation_handler())