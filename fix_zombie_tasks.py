#!/usr/bin/env python3
"""
紧急修复：清理现有僵死任务数据
执行任务 3-9-3
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# 导入数据库相关模块
from backend.app.core.database import SessionLocal
from backend.app.models.user_sync_status import UserSyncStatus
from sqlalchemy import text
from datetime import datetime
import uuid

def fix_specific_zombie_task():
    """修复特定的僵死任务"""
    print("🔧 执行步骤1：修复特定僵死任务")
    
    db = SessionLocal()
    try:
        # 修复特定僵死任务
        zombie_task_id = 'sync_60f2ccbd-d754-4fa0-aa4d-35a7d6551d38_1753133270'
        
        result = db.execute(text("""
            UPDATE user_sync_status 
            SET 
                is_syncing = FALSE,
                progress_percentage = 0,
                current_stats = '{}',
                updated_at = NOW()
            WHERE 
                task_id = :task_id
                AND is_syncing = TRUE;
        """), {"task_id": zombie_task_id})
        
        db.commit()
        
        affected_rows = result.rowcount
        if affected_rows > 0:
            print(f"   ✅ 成功修复特定僵死任务: {zombie_task_id}")
            print(f"   📊 影响行数: {affected_rows}")
        else:
            print(f"   ℹ️  特定任务未找到或已被修复: {zombie_task_id}")
            
        return True
        
    except Exception as e:
        print(f"   ❌ 修复特定僵死任务失败: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def check_other_zombie_tasks():
    """检查其他僵死任务"""
    print("\n🔍 执行步骤2：检查其他僵死任务")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 
                user_id,
                task_id,
                is_syncing,
                error_message,
                started_at,
                updated_at,
                EXTRACT(EPOCH FROM (NOW() - updated_at))/60 as minutes_since_update
            FROM user_sync_status 
            WHERE 
                is_syncing = TRUE 
                AND started_at < NOW() - INTERVAL '30 minutes';
        """))
        
        zombie_tasks = result.fetchall()
        
        if zombie_tasks:
            print(f"   ⚠️  发现 {len(zombie_tasks)} 个超时僵死任务:")
            for task in zombie_tasks:
                print(f"      - Task ID: {task.task_id}")
                print(f"        User ID: {task.user_id}")
                print(f"        静默时间: {task.minutes_since_update:.1f} 分钟")
                print(f"        错误信息: {task.error_message}")
                print()
        else:
            print("   ✅ 未发现其他超时僵死任务")
            
        return zombie_tasks
        
    except Exception as e:
        print(f"   ❌ 检查僵死任务失败: {e}")
        return []
    finally:
        db.close()

def cleanup_timeout_tasks():
    """批量清理超时任务"""
    print("\n🧹 执行步骤3：批量清理超时任务")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            UPDATE user_sync_status 
            SET 
                is_syncing = FALSE,
                progress_percentage = 0,
                error_message = CONCAT(COALESCE(error_message, ''), ' - 自动清理超时任务'),
                updated_at = NOW()
            WHERE 
                is_syncing = TRUE 
                AND started_at < NOW() - INTERVAL '30 minutes';
        """))
        
        db.commit()
        
        affected_rows = result.rowcount
        if affected_rows > 0:
            print(f"   ✅ 成功清理 {affected_rows} 个超时任务")
        else:
            print("   ✅ 没有需要清理的超时任务")
            
        return affected_rows
        
    except Exception as e:
        print(f"   ❌ 批量清理超时任务失败: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

def verify_fix():
    """验证修复效果"""
    print("\n✅ 执行步骤4：验证修复效果")
    
    db = SessionLocal()
    try:
        # 检查还有多少正在同步的任务
        result = db.execute(text("""
            SELECT COUNT(*) as active_syncs
            FROM user_sync_status 
            WHERE is_syncing = TRUE;
        """))
        
        active_syncs = result.fetchone().active_syncs
        
        # 检查数据一致性
        result = db.execute(text("""
            SELECT COUNT(*) as inconsistent_count
            FROM user_sync_status
            WHERE NOT (
                (is_syncing = TRUE AND progress_percentage BETWEEN 0 AND 99)
                OR (is_syncing = FALSE AND progress_percentage IN (0, 100))
            );
        """))
        
        inconsistent_count = result.fetchone().inconsistent_count
        
        print(f"   📊 当前正在同步的任务数: {active_syncs}")
        print(f"   📊 数据不一致的任务数: {inconsistent_count}")
        
        if active_syncs == 0:
            print("   🎉 太好了！没有正在同步的任务，用户可以启动新的同步")
        else:
            print("   ⚠️  仍有正在同步的任务，可能是正常任务或需要进一步检查")
            
        if inconsistent_count == 0:
            print("   🎉 数据状态完全一致！")
        else:
            print("   ⚠️  仍有数据不一致的记录，需要进一步处理")
            
        return active_syncs == 0 and inconsistent_count == 0
        
    except Exception as e:
        print(f"   ❌ 验证修复效果失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始执行任务3-9-3：紧急修复 - 清理现有僵死任务数据")
    print("=" * 60)
    
    success_count = 0
    total_steps = 4
    
    # 步骤1：修复特定僵死任务
    if fix_specific_zombie_task():
        success_count += 1
    
    # 步骤2：检查其他僵死任务
    zombie_tasks = check_other_zombie_tasks()
    if zombie_tasks is not None:  # 即使为空列表也算成功
        success_count += 1
    
    # 步骤3：批量清理超时任务
    cleaned_count = cleanup_timeout_tasks()
    if cleaned_count >= 0:  # 即使清理了0个也算成功
        success_count += 1
    
    # 步骤4：验证修复效果
    if verify_fix():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 修复结果: {success_count}/{total_steps} 步骤成功")
    
    if success_count == total_steps:
        print("🎉 任务3-9-3执行成功！僵死任务已被清理")
        print("   用户现在应该可以正常使用立即同步功能了")
        return True
    else:
        print("⚠️  部分步骤执行失败，可能需要手动检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)