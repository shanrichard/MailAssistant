#!/usr/bin/env python3
"""清理僵死任务"""
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

from app.core.database import SessionLocal
from app.models.user_sync_status import UserSyncStatus

def clean_zombie_task():
    db = SessionLocal()
    try:
        # 清理指定的僵死任务
        task_id = 'sync_60f2ccbd-d754-4fa0-aa4d-35a7d6551d38_2a62648a_1753179053'
        
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.task_id == task_id
        ).first()
        
        if sync_status:
            sync_status.is_syncing = False
            sync_status.progress_percentage = 100
            db.commit()
            print(f"✓ 已清理僵死任务: {task_id}")
        else:
            print(f"未找到任务: {task_id}")
            
    except Exception as e:
        print(f"清理失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clean_zombie_task()