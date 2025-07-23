#!/usr/bin/env python3
"""直接测试心跳机制"""
import asyncio
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

from app.services.heartbeat_sync_service import execute_background_sync_with_heartbeat
from app.core.database import SessionLocal
from app.models.user_sync_status import UserSyncStatus
from datetime import datetime
import time

async def test_heartbeat():
    user_id = "60f2ccbd-d754-4fa0-aa4d-35a7d6551d38"
    task_id = f"test_heartbeat_{int(time.time())}"
    
    print(f"测试任务ID: {task_id}")
    
    # 创建测试任务
    db = SessionLocal()
    try:
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user_id
        ).first()
        
        if sync_status:
            sync_status.is_syncing = True
            sync_status.task_id = task_id
            sync_status.progress_percentage = 0
            sync_status.started_at = datetime.utcnow()
            sync_status.updated_at = datetime.utcnow()
            db.commit()
            print("✓ 任务创建成功")
        else:
            print("❌ 找不到用户同步状态")
            return
    finally:
        db.close()
    
    # 启动后台任务
    print("启动后台任务...")
    task = asyncio.create_task(
        execute_background_sync_with_heartbeat(user_id, False, task_id)
    )
    
    # 监控心跳更新
    print("\n监控心跳更新（30秒）...")
    last_update = None
    update_count = 0
    
    for i in range(6):
        await asyncio.sleep(5)
        
        db = SessionLocal()
        try:
            sync_status = db.query(UserSyncStatus).filter(
                UserSyncStatus.task_id == task_id
            ).first()
            
            if sync_status:
                current_update = sync_status.updated_at
                print(f"[{i+1}] 更新时间: {current_update}, 进度: {sync_status.progress_percentage}%, 运行中: {sync_status.is_syncing}")
                
                if last_update and current_update != last_update:
                    update_count += 1
                    print("    ✓ 检测到心跳更新！")
                
                last_update = current_update
                
                if not sync_status.is_syncing:
                    print("任务已完成")
                    break
        finally:
            db.close()
    
    # 取消任务
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    print(f"\n测试结果：")
    if update_count > 0:
        print(f"✅ 测试通过！检测到 {update_count} 次心跳更新")
    else:
        print("❌ 测试失败：没有检测到心跳更新")

if __name__ == "__main__":
    asyncio.run(test_heartbeat())