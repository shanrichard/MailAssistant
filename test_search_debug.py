#!/usr/bin/env python
"""
Debug script to test Gmail search functionality
测试Gmail搜索功能的调试脚本
"""

import os
import sys
sys.path.append('backend')

from backend.app.core.database import SessionLocal
from backend.app.models.email import Email
from backend.app.models.user import User
from sqlalchemy import func, or_

def test_database_search():
    """测试数据库中的邮件搜索"""
    print("=== Testing Database Search ===")
    
    db = SessionLocal()
    try:
        # 搜索包含openai的邮件（不区分大小写）
        search_query = 'openai'
        
        emails = db.query(Email).filter(
            or_(
                func.lower(Email.subject).contains(search_query.lower()),
                func.lower(Email.sender).contains(search_query.lower()),
                func.lower(Email.body_plain).contains(search_query.lower())
            )
        ).all()
        
        print(f"Found {len(emails)} emails containing '{search_query}' in database")
        
        for i, email in enumerate(emails[:5]):  # Show first 5
            print(f"\n{i+1}. Email ID: {email.gmail_id}")
            print(f"   Subject: {email.subject}")
            print(f"   From: {email.sender}")
            print(f"   Date: {email.received_at}")
            
            # 检查在哪个字段找到了关键词
            if search_query.lower() in email.subject.lower():
                print(f"   *** Found in SUBJECT")
            if search_query.lower() in email.sender.lower():
                print(f"   *** Found in SENDER")
            if search_query.lower() in (email.body_plain or '').lower():
                print(f"   *** Found in BODY")
                # 显示包含关键词的部分
                body = email.body_plain or ''
                start = body.lower().find(search_query.lower())
                if start >= 0:
                    snippet = body[max(0, start-50):start+50]
                    print(f"   Body snippet: ...{snippet}...")
        
        return emails
        
    finally:
        db.close()

def analyze_gmail_search_behavior():
    """分析Gmail搜索行为"""
    print("\n=== Analyzing Gmail Search Behavior ===")
    
    # Gmail搜索语法说明
    print("Gmail search query syntax:")
    print("- 'openai' - searches all fields for the word 'openai'")
    print("- 'from:openai' - searches only sender field")
    print("- 'subject:openai' - searches only subject field")
    print("- 'OpenAI' vs 'openai' - Gmail search is case-insensitive")
    
    # 可能的问题
    print("\nPossible issues:")
    print("1. Gmail API search vs local database content mismatch")
    print("2. Gmail search only searches synced/indexed content")
    print("3. Search query syntax differences")
    print("4. Authentication or service issues")
    print("5. Email might be in different folders/labels not being searched")

def suggest_debugging_steps():
    """建议调试步骤"""
    print("\n=== Debugging Steps ===")
    print("1. Check if emails containing 'openai' exist in database")
    print("2. Verify Gmail API authentication is working")
    print("3. Test different search queries:")
    print("   - 'openai'")
    print("   - 'OpenAI'") 
    print("   - 'from:openai'")
    print("   - 'subject:openai'")
    print("4. Check Gmail web interface with same search")
    print("5. Verify email sync is complete and up-to-date")
    print("6. Check if search is limited to specific labels/folders")

if __name__ == "__main__":
    try:
        emails_found = test_database_search()
        analyze_gmail_search_behavior()
        suggest_debugging_steps()
        
        if emails_found:
            print(f"\n=== CONCLUSION ===")
            print(f"✓ Database contains {len(emails_found)} emails with 'openai'")
            print(f"✗ Gmail search API is not finding these emails")
            print(f"→ The issue is likely in the Gmail API search implementation or query syntax")
            
            print(f"\nRecommended actions:")
            print(f"1. Test Gmail search with different query formats")
            print(f"2. Check if emails are in the right Gmail folders/labels") 
            print(f"3. Verify Gmail API search scope and permissions")
            print(f"4. Compare with Gmail web interface search results")
        else:
            print(f"\n=== CONCLUSION ===")
            print(f"✗ No emails with 'openai' found in database")
            print(f"→ Need to sync more emails or check if they exist in Gmail")
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()