#!/usr/bin/env python3
"""
测试数据库同步状态管理
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
from backend.app.models.user import User
from sqlalchemy import text
from datetime import datetime
import uuid

def test_user_sync_status_model():
    """测试 UserSyncStatus 模型"""
    print("🔍 测试 UserSyncStatus 数据库模型")
    
    db = SessionLocal()
    try:
        # 检查表是否存在
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'user_sync_status'
        """))
        table_exists = result.fetchone() is not None
        
        if table_exists:
            print("   ✅ user_sync_status 表存在")
        else:
            print("   ❌ user_sync_status 表不存在")
            return False
        
        # 检查表结构
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user_sync_status'
            ORDER BY ordinal_position
        """))
        columns = result.fetchall()
        
        expected_columns = {
            'user_id', 'is_syncing', 'sync_type', 'started_at', 
            'progress_percentage', 'current_stats', 'task_id', 
            'error_message', 'created_at', 'updated_at'
        }
        
        actual_columns = {col[0] for col in columns}
        
        if expected_columns.issubset(actual_columns):
            print("   ✅ 表结构正确包含所有必需字段")
            for col in columns:
                print(f"      - {col[0]}: {col[1]}")
        else:
            missing = expected_columns - actual_columns
            print(f"   ❌ 缺少字段: {missing}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 数据库测试失败: {e}")
        return False
    finally:
        db.close()

def test_user_sync_status_operations():
    """测试 UserSyncStatus 基本操作"""
    print("\n🔍 测试 UserSyncStatus 基本操作")
    
    db = SessionLocal()
    try:
        # 查找或创建测试用户
        test_email = "test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        
        if not user:
            print("   📝 创建测试用户")
            user = User(
                email=test_email,
                google_id="test_google_id",
                name="Test User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"   ✅ 创建用户: {user.email}")
        else:
            print(f"   ✅ 使用现有用户: {user.email}")
        
        # 测试创建同步状态记录
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user.id
        ).first()
        
        if sync_status:
            print("   📝 清理现有同步状态")
            db.delete(sync_status)
            db.commit()
        
        # 创建新的同步状态
        print("   📝 创建新的同步状态记录")
        sync_status = UserSyncStatus(
            user_id=user.id,
            is_syncing=False,
            sync_type='incremental',
            progress_percentage=0
        )
        db.add(sync_status)
        db.commit()
        db.refresh(sync_status)
        print("   ✅ 同步状态记录创建成功")
        
        # 测试更新操作
        print("   📝 测试状态更新")
        sync_status.is_syncing = True
        sync_status.progress_percentage = 50
        sync_status.current_stats = {"new": 10, "updated": 5}
        sync_status.started_at = datetime.utcnow()
        db.commit()
        print("   ✅ 状态更新成功")
        
        # 验证更新
        updated_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user.id
        ).first()
        
        if updated_status and updated_status.is_syncing and updated_status.progress_percentage == 50:
            print("   ✅ 状态验证成功")
            print(f"      - is_syncing: {updated_status.is_syncing}")
            print(f"      - progress: {updated_status.progress_percentage}%")
            print(f"      - stats: {updated_status.current_stats}")
        else:
            print("   ❌ 状态验证失败")
            return False
        
        # 测试并发控制 (行锁)
        print("   📝 测试并发控制")
        locked_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user.id
        ).with_for_update().first()
        
        if locked_status:
            print("   ✅ 行锁获取成功")
        else:
            print("   ❌ 行锁获取失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 操作测试失败: {e}")
        return False
    finally:
        db.close()

def test_sync_status_constraints():
    """测试同步状态约束"""
    print("\n🔍 测试同步状态约束和边界情况")
    
    db = SessionLocal()
    try:
        # 测试用户
        test_email = "test@example.com"
        user = db.query(User).filter(User.email == test_email).first()
        
        if not user:
            print("   ❌ 测试用户不存在")
            return False
        
        # 测试进度百分比边界
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user.id
        ).first()
        
        if sync_status:
            # 测试进度范围
            test_values = [0, 50, 100, 150, -10]  # 包含边界值
            for value in test_values:
                sync_status.progress_percentage = value
                db.commit()
                
                refreshed = db.query(UserSyncStatus).filter(
                    UserSyncStatus.user_id == user.id
                ).first()
                
                print(f"      进度设置 {value}% -> 存储为 {refreshed.progress_percentage}%")
            
            print("   ✅ 进度百分比测试完成")
        
        # 测试 JSON 字段
        test_stats = {
            "fetched": 100,
            "new": 50,
            "updated": 30,
            "errors": 2,
            "sync_time": datetime.utcnow().isoformat()
        }
        
        sync_status.current_stats = test_stats
        db.commit()
        
        refreshed = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user.id
        ).first()
        
        if refreshed.current_stats == test_stats:
            print("   ✅ JSON 字段存储测试成功")
        else:
            print("   ❌ JSON 字段存储测试失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 约束测试失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主测试函数"""
    print("🚀 开始测试数据库同步状态管理")
    print("=" * 60)
    
    tests = [
        test_user_sync_status_model,
        test_user_sync_status_operations,
        test_sync_status_constraints
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
                print("   🎉 测试通过")
            else:
                print("   ❌ 测试失败")
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
        
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有数据库测试通过!")
        return True
    else:
        print("⚠️  部分数据库测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)