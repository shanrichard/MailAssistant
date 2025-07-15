#!/usr/bin/env python3
"""
Test script for Gmail API integration
"""
import os
import sys
import asyncio
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import get_db
from app.models.user import User
from app.services.gmail_service import gmail_service
from app.services.email_sync_service import email_sync_service


async def test_gmail_integration():
    """Test Gmail API integration"""
    print("🧪 Testing Gmail API Integration")
    print("=" * 50)
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find a user with Gmail tokens (you may need to create one first)
        user = db.query(User).filter(User.is_active == True).first()
        
        if not user:
            print("❌ No active user found. Please authenticate a user first.")
            return
        
        tokens = user.get_decrypted_gmail_tokens()
        if not tokens:
            print(f"❌ User {user.email} has no Gmail tokens. Please authenticate first.")
            return
        
        print(f"✅ Found user: {user.email}")
        
        # Test 1: Get Gmail profile
        print("\n📧 Testing Gmail profile...")
        try:
            profile = gmail_service.get_user_profile(user)
            print(f"✅ Gmail profile: {profile.get('emailAddress')}")
            print(f"   Messages total: {profile.get('messagesTotal')}")
            print(f"   Threads total: {profile.get('threadsTotal')}")
        except Exception as e:
            print(f"❌ Failed to get Gmail profile: {e}")
            return
        
        # Test 2: List recent messages
        print("\n📬 Testing recent messages...")
        try:
            messages, next_token = gmail_service.list_messages(user, max_results=5)
            print(f"✅ Found {len(messages)} recent messages")
            if next_token:
                print(f"   Next page token available: {next_token[:20]}...")
        except Exception as e:
            print(f"❌ Failed to list messages: {e}")
            return
        
        # Test 3: Get message details
        if messages:
            print("\n📄 Testing message details...")
            try:
                message_id = messages[0]['id']
                message_details = gmail_service.get_message_details(user, message_id)
                parsed_message = gmail_service.parse_message(message_details)
                
                print(f"✅ Parsed message:")
                print(f"   Subject: {parsed_message.get('subject', 'No subject')[:50]}...")
                print(f"   From: {parsed_message.get('sender', 'Unknown')}")
                print(f"   Received: {parsed_message.get('received_at')}")
                print(f"   Has attachments: {parsed_message.get('has_attachments')}")
                
            except Exception as e:
                print(f"❌ Failed to get message details: {e}")
                return
        
        # Test 4: Search messages
        print("\n🔍 Testing message search...")
        try:
            search_results = gmail_service.search_messages(user, "is:unread", max_results=3)
            print(f"✅ Found {len(search_results)} unread messages")
            
            for i, msg in enumerate(search_results[:2]):
                print(f"   {i+1}. {msg.get('subject', 'No subject')[:40]}...")
                
        except Exception as e:
            print(f"❌ Failed to search messages: {e}")
            return
        
        # Test 5: Email sync service
        print("\n🔄 Testing email sync...")
        try:
            sync_stats = email_sync_service.sync_user_emails(
                db=db, 
                user=user, 
                days=1, 
                max_messages=10
            )
            print(f"✅ Email sync completed:")
            print(f"   Fetched: {sync_stats['fetched']}")
            print(f"   New: {sync_stats['new']}")
            print(f"   Updated: {sync_stats['updated']}")
            print(f"   Errors: {sync_stats['errors']}")
            
        except Exception as e:
            print(f"❌ Failed to sync emails: {e}")
            return
        
        # Test 6: Sync status
        print("\n📊 Testing sync status...")
        try:
            sync_status = email_sync_service.get_sync_status(db, user)
            print(f"✅ Sync status:")
            print(f"   Total emails: {sync_status['total_emails']}")
            print(f"   Unread emails: {sync_status['unread_emails']}")
            print(f"   Latest sync: {sync_status['latest_sync']}")
            
        except Exception as e:
            print(f"❌ Failed to get sync status: {e}")
            return
        
        print("\n🎉 All Gmail API tests passed!")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        
    finally:
        db.close()


def main():
    """Main function"""
    try:
        asyncio.run(test_gmail_integration())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()