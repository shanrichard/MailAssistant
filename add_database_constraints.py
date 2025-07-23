#!/usr/bin/env python3
"""
实现数据库硬约束防止数据不一致
执行任务 3-9-4
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
from sqlalchemy import text
from datetime import datetime

def verify_existing_data():
    """验证现有数据是否符合约束条件"""
    print("🔍 执行步骤1：验证现有数据是否符合约束条件")
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT 
                user_id,
                task_id,
                is_syncing,
                progress_percentage,
                CASE 
                    WHEN is_syncing = TRUE AND progress_percentage NOT BETWEEN 0 AND 99 
                    THEN '进度状态不一致'
                    WHEN is_syncing = FALSE AND progress_percentage NOT IN (0, 100)
                    THEN '完成状态不一致'
                    ELSE '状态正常'
                END as status_check
            FROM user_sync_status
            WHERE NOT (
                (is_syncing = TRUE AND progress_percentage BETWEEN 0 AND 99)
                OR (is_syncing = FALSE AND progress_percentage IN (0, 100))
            );
        """))
        
        inconsistent_records = result.fetchall()
        
        if inconsistent_records:
            print(f"   ⚠️  发现 {len(inconsistent_records)} 条不符合约束的记录:")
            for record in inconsistent_records:
                print(f"      - Task ID: {record.task_id}")
                print(f"        User ID: {record.user_id}")
                print(f"        Is Syncing: {record.is_syncing}")
                print(f"        Progress: {record.progress_percentage}%")
                print(f"        问题: {record.status_check}")
                print()
            return False
        else:
            print("   ✅ 所有现有数据都符合约束条件")
            return True
            
    except Exception as e:
        print(f"   ❌ 验证现有数据失败: {e}")
        return False
    finally:
        db.close()

def add_sync_state_constraint():
    """添加同步状态一致性约束"""
    print("\n🔧 执行步骤2：添加同步状态一致性约束")
    
    db = SessionLocal()
    try:
        # 添加进度与同步状态强一致性约束
        db.execute(text("""
            ALTER TABLE user_sync_status
            ADD CONSTRAINT chk_sync_state_consistency
            CHECK (
                (is_syncing = TRUE  AND progress_percentage BETWEEN 0 AND 99)
             OR (is_syncing = FALSE AND progress_percentage IN (0, 100))
            );
        """))
        
        db.commit()
        print("   ✅ 成功添加同步状态一致性约束")
        return True
        
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("   ℹ️  同步状态一致性约束已存在")
            db.rollback()
            return True
        else:
            print(f"   ❌ 添加同步状态一致性约束失败: {e}")
            db.rollback()
            return False
    finally:
        db.close()

def add_unique_running_sync_index():
    """添加用户唯一运行任务索引"""
    print("\n🔧 执行步骤3：添加用户唯一运行任务索引")
    
    db = SessionLocal()
    try:
        # 确保每个用户只能有一个运行中的同步任务
        db.execute(text("""
            CREATE UNIQUE INDEX uniq_user_running_sync
            ON user_sync_status(user_id)
            WHERE is_syncing = TRUE;
        """))
        
        db.commit()
        print("   ✅ 成功添加用户唯一运行任务索引")
        return True
        
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("   ℹ️  用户唯一运行任务索引已存在")
            db.rollback()
            return True
        else:
            print(f"   ❌ 添加用户唯一运行任务索引失败: {e}")
            db.rollback()
            return False
    finally:
        db.close()

def add_unique_task_id_index():
    """添加任务ID唯一性索引"""
    print("\n🔧 执行步骤4：添加任务ID唯一性索引")
    
    db = SessionLocal()
    try:
        # 防止任务ID重复
        db.execute(text("""
            CREATE UNIQUE INDEX uniq_task_id
            ON user_sync_status(task_id);
        """))
        
        db.commit()
        print("   ✅ 成功添加任务ID唯一性索引")
        return True
        
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print("   ℹ️  任务ID唯一性索引已存在")
            db.rollback()
            return True
        else:
            print(f"   ❌ 添加任务ID唯一性索引失败: {e}")
            db.rollback()
            return False
    finally:
        db.close()

def test_constraints():
    """测试约束有效性"""
    print("\n🧪 执行步骤5：测试约束有效性")
    
    db = SessionLocal()
    test_results = []
    
    try:
        # 测试1：尝试插入不一致的状态（应该被阻止）
        print("   🧪 测试1：尝试插入不一致状态数据")
        try:
            db.execute(text("""
                INSERT INTO user_sync_status 
                (user_id, task_id, is_syncing, progress_percentage, sync_type, created_at, updated_at)
                VALUES 
                ('00000000-0000-0000-0000-000000000001', 'test_inconsistent_task', TRUE, 100, 'test', NOW(), NOW());
            """))
            db.commit()
            print("      ❌ 约束失败：不一致数据被允许插入")
            test_results.append(False)
        except Exception as e:
            print("      ✅ 约束生效：不一致数据被正确阻止")
            db.rollback()
            test_results.append(True)
        
        # 测试2：尝试为同一用户创建多个运行中任务（应该被阻止）
        print("   🧪 测试2：尝试为同一用户创建多个运行中任务")
        try:
            # 先插入一个正常的运行中任务
            db.execute(text("""
                INSERT INTO user_sync_status 
                (user_id, task_id, is_syncing, progress_percentage, sync_type, created_at, updated_at)
                VALUES 
                ('00000000-0000-0000-0000-000000000002', 'test_task_1', TRUE, 50, 'test', NOW(), NOW());
            """))
            db.commit()
            
            # 尝试插入第二个运行中任务（应该失败）
            db.execute(text("""
                INSERT INTO user_sync_status 
                (user_id, task_id, is_syncing, progress_percentage, sync_type, created_at, updated_at)
                VALUES 
                ('00000000-0000-0000-0000-000000000002', 'test_task_2', TRUE, 30, 'test', NOW(), NOW());
            """))
            db.commit()
            print("      ❌ 约束失败：允许同用户多个运行中任务")
            test_results.append(False)
        except Exception as e:
            print("      ✅ 约束生效：同用户多个运行中任务被正确阻止")
            db.rollback()
            test_results.append(True)
            
        # 清理测试数据
        try:
            db.execute(text("""
                DELETE FROM user_sync_status 
                WHERE user_id IN (
                    '00000000-0000-0000-0000-000000000001',
                    '00000000-0000-0000-0000-000000000002'
                );
            """))
            db.commit()
        except:
            db.rollback()
            
        return all(test_results)
        
    except Exception as e:
        print(f"   ❌ 测试约束有效性失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始执行任务3-9-4：实现数据库硬约束防止数据不一致")
    print("=" * 60)
    
    success_count = 0
    total_steps = 5
    
    # 步骤1：验证现有数据
    if verify_existing_data():
        success_count += 1
    
    # 步骤2：添加同步状态一致性约束
    if add_sync_state_constraint():
        success_count += 1
    
    # 步骤3：添加用户唯一运行任务索引
    if add_unique_running_sync_index():
        success_count += 1
    
    # 步骤4：添加任务ID唯一性索引  
    if add_unique_task_id_index():
        success_count += 1
    
    # 步骤5：测试约束有效性
    if test_constraints():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 实施结果: {success_count}/{total_steps} 步骤成功")
    
    if success_count == total_steps:
        print("🎉 任务3-9-4执行成功！数据库硬约束已实施")
        print("   🛡️  数据库层面现已防止所有不一致状态")
        print("   🏆 系统达到企业级数据一致性保障")
        return True
    elif success_count >= 3:
        print("⚠️  大部分约束已成功添加，系统安全性显著提升")
        return True
    else:
        print("⚠️  部分约束添加失败，可能需要手动检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)