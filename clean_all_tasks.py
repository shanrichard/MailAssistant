#!/usr/bin/env python3
"""清理所有同步任务"""
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

from app.core.database import SessionLocal
from app.models.user_sync_status import UserSyncStatus

def clean_all_tasks():
    db = SessionLocal()
    try:
        # 查找所有同步任务
        sync_statuses = db.query(UserSyncStatus).filter(
            UserSyncStatus.is_syncing == True
        ).all()
        
        for sync_status in sync_statuses:
            print(f"清理任务: {sync_status.task_id}")
            sync_status.is_syncing = False
            sync_status.progress_percentage = 100
        
        db.commit()
        print(f"\n✓ 已清理 {len(sync_statuses)} 个任务")
            
    except Exception as e:
        print(f"清理失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_all_tasks()