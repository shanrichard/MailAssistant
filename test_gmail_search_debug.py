#!/usr/bin/env python3
"""
调试 Gmail API 搜索功能
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.gmail_service import gmail_service
from backend.app.models.user import User
from backend.app.core.database import SessionLocal
import json

def test_gmail_search():
    """测试不同的 Gmail 搜索查询"""
    db = SessionLocal()
    
    try:
        # 获取第一个有 Gmail tokens 的用户
        users = db.query(User).all()
        user = None
        for u in users:
            if u._encrypted_gmail_tokens:
                user = u
                break
                
        if not user:
            print("错误：没有找到有 Gmail 授权的用户")
            return
        
        print(f"使用用户: {user.email}")
        
        # 测试不同的查询
        test_queries = [
            # 基本时间查询
            ("newer_than:7d", "最近7天的邮件"),
            ("newer_than:30d", "最近30天的邮件"),
            
            # 使用 after/before 的日期查询
            ("after:2025-05-01 before:2025-06-01", "5月份的邮件（横线格式）"),
            ("after:2025/5/1 before:2025/6/1", "5月份的邮件（斜线格式）"),
            
            # 带主题的查询
            ("subject:sofa after:2025-05-01 before:2025-06-01", "5月份关于sofa的邮件"),
            
            # 简单查询
            ("sofa", "包含sofa的邮件"),
        ]
        
        for query, description in test_queries:
            print(f"\n测试: {description}")
            print(f"查询: {query}")
            
            try:
                # 直接调用 list_messages 看看返回什么
                messages, _ = gmail_service.list_messages(
                    user=user,
                    query=query,
                    max_results=5
                )
                
                print(f"找到邮件数: {len(messages)}")
                
                if messages:
                    # 获取第一封邮件的详情
                    first_msg = gmail_service.get_message_details(user, messages[0]['id'])
                    parsed = gmail_service.parse_message(first_msg)
                    print(f"第一封邮件:")
                    print(f"  - 主题: {parsed.get('subject', 'N/A')}")
                    print(f"  - 发件人: {parsed.get('sender', 'N/A')}")
                    print(f"  - 时间: {parsed.get('received_at', 'N/A')}")
                
            except Exception as e:
                print(f"错误: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 测试 search_messages_optimized
        print("\n\n测试 search_messages_optimized 方法:")
        query = "subject:sofa after:2025-05-01 before:2025-06-01"
        print(f"查询: {query}")
        try:
            results = gmail_service.search_messages_optimized(
                user=user,
                query=query,
                max_results=10
            )
            print(f"找到邮件数: {len(results)}")
            if results:
                print(f"第一封邮件主题: {results[0].get('subject', 'N/A')}")
        except Exception as e:
            print(f"错误: {str(e)}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    test_gmail_search()