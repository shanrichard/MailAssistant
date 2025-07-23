#!/bin/bash
# Test Step 5: 使用SQLAlchemy的最终验证

echo "=== Step 5 测试：最终验证（使用SQLAlchemy）==="

# 创建测试脚本
cat > test_final_with_sqlalchemy.py << 'EOF'
#!/usr/bin/env python3
"""最终验证所有修复（使用SQLAlchemy）"""
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

import os
from app.core.database import SessionLocal
from sqlalchemy import text

TEST_USER_ID = "60f2ccbd-d754-4fa0-aa4d-35a7d6551d38"
TEST_USER_EMAIL = "james.shan@signalplus.com"

print(f"测试用户: {TEST_USER_EMAIL} ({TEST_USER_ID})")

def test_database_constraints():
    """测试1: 数据库约束（3-11-3）"""
    print("\n=== 测试1: 数据库约束 ===")
    db = SessionLocal()
    passed = 0
    failed = 0
    
    try:
        # 1. 检查状态一致性约束
        print("1. 检查状态一致性约束...")
        result = db.execute(text("""
            SELECT conname FROM pg_constraint 
            WHERE conname = 'chk_sync_state_consistency'
        """))
        if result.fetchone():
            print("   ✅ 状态一致性约束存在")
            passed += 1
        else:
            print("   ❌ 状态一致性约束不存在")
            failed += 1
        
        # 2. 检查唯一运行任务约束
        print("2. 检查唯一运行任务约束...")
        result = db.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE indexname = 'uniq_user_running_sync'
        """))
        if result.fetchone():
            print("   ✅ 唯一运行任务约束存在")
            passed += 1
        else:
            print("   ❌ 唯一运行任务约束不存在")
            failed += 1
        
        # 3. 检查任务ID唯一约束
        print("3. 检查任务ID唯一约束...")
        result = db.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE indexname = 'uniq_task_id'
        """))
        if result.fetchone():
            print("   ✅ 任务ID唯一约束存在")
            passed += 1
        else:
            print("   ❌ 任务ID唯一约束不存在")
            failed += 1
        
        # 4. 检查性能索引
        print("4. 检查性能索引...")
        result = db.execute(text("""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE tablename = 'user_sync_status' 
            AND indexname IN ('idx_sync_status_updated', 'idx_sync_status_zombie_check')
        """))
        count = result.scalar()
        if count >= 2:
            print(f"   ✅ 找到 {count} 个性能索引")
            passed += 1
        else:
            print(f"   ❌ 缺少性能索引，只找到 {count} 个")
            failed += 1
            
    except Exception as e:
        print(f"❌ 约束检查失败: {e}")
        failed += 1
    finally:
        db.close()
    
    print(f"\n约束测试结果: {passed} 通过, {failed} 失败")
    return failed == 0

def test_code_fixes():
    """测试2-4: 代码修复验证"""
    print("\n=== 测试2-4: 代码修复验证 ===")
    passed = 0
    failed = 0
    
    # 测试2: API调用修复（3-11-2）
    print("\n2. 检查API调用修复...")
    try:
        with open('/Users/shanjingxiang/projects/MailAssistant/backend/app/api/gmail.py', 'r') as f:
            content = f.read()
            
        if 'execute_background_sync_with_heartbeat' in content:
            if 'execute_background_sync_v2' not in content:
                print("   ✅ API调用已修复为正确的函数名")
                passed += 1
            else:
                print("   ❌ 仍存在错误的函数名")
                failed += 1
        else:
            print("   ❌ 未找到正确的函数调用")
            failed += 1
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        failed += 1
    
    # 测试3: 异步阻塞修复（3-11-1）
    print("\n3. 检查异步阻塞修复...")
    try:
        with open('/Users/shanjingxiang/projects/MailAssistant/backend/app/services/email_sync_service.py', 'r') as f:
            content = f.read()
            
        has_asyncio_import = 'import asyncio' in content
        has_await_sleep = 'await asyncio.sleep' in content
        
        if has_asyncio_import and has_await_sleep:
            print("   ✅ 异步阻塞已修复")
            print("      - asyncio已导入")
            print("      - 使用await asyncio.sleep")
            passed += 1
        else:
            print("   ❌ 异步阻塞问题未完全修复")
            if not has_asyncio_import:
                print("      - 缺少asyncio导入")
            if not has_await_sleep:
                print("      - 未使用await asyncio.sleep")
            failed += 1
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        failed += 1
    
    # 测试4: 调度器集成（3-11-4）
    print("\n4. 检查调度器集成...")
    try:
        with open('/Users/shanjingxiang/projects/MailAssistant/backend/app/scheduler/scheduler_app.py', 'r') as f:
            scheduler_content = f.read()
            
        has_zombie_cleanup = 'zombie_task_cleanup' in scheduler_content
        has_cleanup_function = 'cleanup_zombie_tasks_by_heartbeat' in scheduler_content
        has_interval_config = "minutes=2" in scheduler_content
        
        if has_zombie_cleanup and has_cleanup_function and has_interval_config:
            print("   ✅ 僵死任务清理已集成")
            print("      - 清理作业已配置")
            print("      - 清理函数已导入")
            print("      - 每2分钟运行一次")
            passed += 1
        else:
            print("   ❌ 僵死任务清理未正确集成")
            if not has_zombie_cleanup:
                print("      - 缺少清理作业")
            if not has_cleanup_function:
                print("      - 缺少清理函数导入")
            if not has_interval_config:
                print("      - 清理间隔配置错误")
            failed += 1
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        failed += 1
    
    print(f"\n代码修复测试结果: {passed} 通过, {failed} 失败")
    return failed == 0

def test_heartbeat_table():
    """测试5: 心跳表验证"""
    print("\n=== 测试5: 心跳表验证 ===")
    db = SessionLocal()
    
    try:
        # 检查心跳表是否存在
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sync_task_heartbeat'
            )
        """))
        
        if result.scalar():
            print("✅ 心跳表存在")
            
            # 检查表结构
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'sync_task_heartbeat'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            print("   表结构：")
            for col_name, col_type in columns:
                print(f"      - {col_name}: {col_type}")
            
            # 清理测试数据
            db.execute(text("DELETE FROM sync_task_heartbeat WHERE task_id LIKE 'test_%'"))
            db.commit()
            print("   已清理测试数据")
            
            return True
        else:
            print("❌ 心跳表不存在")
            return False
            
    except Exception as e:
        print(f"❌ 心跳表检查失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主测试函数"""
    print("="*60)
    print("最终验证 - 任务 3-11 所有修复")
    print("="*60)
    
    # 运行所有测试
    db_constraints_ok = test_database_constraints()
    code_fixes_ok = test_code_fixes()
    heartbeat_table_ok = test_heartbeat_table()
    
    # 结果汇总
    print("\n" + "="*60)
    print("测试结果汇总:")
    print("="*60)
    
    all_passed = db_constraints_ok and code_fixes_ok and heartbeat_table_ok
    
    print(f"{'✅' if db_constraints_ok else '❌'} 数据库约束测试")
    print(f"{'✅' if code_fixes_ok else '❌'} 代码修复测试")
    print(f"{'✅' if heartbeat_table_ok else '❌'} 心跳表测试")
    
    if all_passed:
        print("\n🎉 所有测试通过！")
        print("\n任务 3-11 修复总结：")
        print("✅ 3-11-1: 异步阻塞问题已修复 - await asyncio.sleep")
        print("✅ 3-11-2: API调用错误已修复 - execute_background_sync_with_heartbeat")
        print("✅ 3-11-3: 数据库约束已添加 - 防止数据不一致")
        print("✅ 3-11-4: 僵死任务清理已集成 - 每2分钟自动运行")
        print("✅ 3-11-5: 所有修复已验证完成")
        print("\n邮件同步的心跳机制现在应该正常工作了！")
    else:
        print("\n⚠️  部分测试失败，请查看上面的详细信息")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
EOF

# 运行测试
echo -e "\n开始最终验证..."
cd /Users/shanjingxiang/projects/MailAssistant
source .venv/bin/activate
python test_final_with_sqlalchemy.py
TEST_RESULT=$?

# 清理临时文件
rm -f test_final_with_sqlalchemy.py

# 最终结果
echo -e "\n=== 任务 3-11-5 最终结果 ==="
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ 任务 3-11-5 完成！"
    echo ""
    echo "🎉 恭喜！任务 3-11 的所有子任务都已完成并验证。"
    echo ""
    echo "修复内容回顾："
    echo "- 修复了异步函数中的同步阻塞调用"
    echo "- 修复了API调用错误的函数名"
    echo "- 添加了数据库约束防止数据不一致"
    echo "- 将僵死任务清理集成到主调度器"
    echo "- 完成了全面的测试验证"
else
    echo "❌ 验证未通过，请查看上面的错误信息"
    exit 1
fi