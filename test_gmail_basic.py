#!/usr/bin/env python3
"""
测试 Gmail 服务的基础功能
独立测试，不依赖 Agent 或 Tools
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.database import SessionLocal, engine
from backend.app.models.user import User
from backend.app.services.gmail_service import gmail_service
import json
from datetime import datetime

def test_gmail_basic():
    """测试基础的 Gmail 功能"""
    db = SessionLocal()
    
    try:
        # 1. 获取测试用户
        print("=== 步骤 1: 获取测试用户 ===")
        test_email = "james.shan@signalplus.com"
        user = db.query(User).filter(User.email == test_email).first()
        
        if not user:
            print(f"错误: 找不到用户 {test_email}")
            return
        
        print(f"找到用户: {user.email} (ID: {user.id})")
        
        # 2. 检查用户的 Gmail tokens
        print("\n=== 步骤 2: 检查 Gmail Tokens ===")
        if not user._encrypted_gmail_tokens:
            print("错误: 用户没有 Gmail tokens")
            return
        
        # 尝试解密 tokens
        try:
            tokens = user.get_decrypted_gmail_tokens()
            print(f"成功解密 tokens: {list(tokens.keys())}")
        except Exception as e:
            print(f"解密 tokens 失败: {e}")
            return
        
        # 3. 测试获取用户 Gmail profile
        print("\n=== 步骤 3: 测试获取用户 Profile ===")
        try:
            profile = gmail_service.get_user_profile(user)
            print(f"成功获取 profile: {json.dumps(profile, indent=2)}")
        except Exception as e:
            print(f"获取 profile 失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        
        # 4. 测试列出邮件
        print("\n=== 步骤 4: 测试列出邮件 ===")
        try:
            messages, next_token = gmail_service.list_messages(user, max_results=5)
            print(f"成功获取 {len(messages)} 封邮件")
            for i, msg in enumerate(messages):
                print(f"  邮件 {i+1}: ID={msg.get('id')}, ThreadID={msg.get('threadId')}")
        except Exception as e:
            print(f"列出邮件失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        
        # 5. 测试获取邮件详情
        print("\n=== 步骤 5: 测试获取邮件详情 ===")
        if messages:
            try:
                first_msg_id = messages[0]['id']
                msg_detail = gmail_service.get_message_details(user, first_msg_id)
                
                # 解析邮件
                parsed = gmail_service.parse_message(msg_detail)
                print(f"成功获取邮件详情:")
                print(f"  主题: {parsed['subject']}")
                print(f"  发件人: {parsed['sender']}")
                print(f"  时间: {parsed['received_at']}")
                print(f"  有附件: {parsed['has_attachments']}")
                print(f"  正文长度: {len(parsed.get('body_plain', ''))}")
            except Exception as e:
                print(f"获取邮件详情失败: {e}")
                print(f"错误类型: {type(e).__name__}")
                import traceback
                traceback.print_exc()
        
        # 6. 测试搜索功能
        print("\n=== 步骤 6: 测试搜索功能 ===")
        try:
            # 搜索最近1天的邮件
            recent_messages = gmail_service.get_recent_messages(user, days=1, max_results=3)
            print(f"最近1天的邮件数: {len(recent_messages)}")
            for msg in recent_messages:
                print(f"  - {msg['subject']} (from: {msg['sender']})")
        except Exception as e:
            print(f"搜索邮件失败: {e}")
            print(f"错误类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
        
        # 7. 测试标记已读功能
        print("\n=== 步骤 7: 测试标记已读功能 ===")
        if messages:
            try:
                # 注意: mark_as_read 需要消息ID列表
                test_msg_id = messages[0]['id']
                success = gmail_service.mark_as_read(user, [test_msg_id])
                print(f"标记已读结果: {success}")
            except Exception as e:
                print(f"标记已读失败: {e}")
                print(f"错误类型: {type(e).__name__}")
                import traceback
                traceback.print_exc()
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"\n意外错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_gmail_basic()