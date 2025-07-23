#!/usr/bin/env python3
"""
测试并发控制机制
验证多个同步请求的并发处理
"""
import sys
import os
import time
import threading
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

class ConcurrentSyncTest:
    """并发同步测试类"""
    
    def __init__(self):
        self.results = []
        self.test_user_id = None
        self.lock = threading.Lock()
    
    def setup_test_user(self):
        """设置测试用户"""
        db = SessionLocal()
        try:
            # 查找或创建测试用户
            test_email = "concurrent_test@example.com"
            user = db.query(User).filter(User.email == test_email).first()
            
            if not user:
                user = User(
                    email=test_email,
                    google_id="concurrent_test_google_id",
                    name="Concurrent Test User"
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            self.test_user_id = user.id
            
            # 清理现有同步状态
            existing_status = db.query(UserSyncStatus).filter(
                UserSyncStatus.user_id == user.id
            ).first()
            
            if existing_status:
                db.delete(existing_status)
                db.commit()
            
            # 创建初始同步状态
            sync_status = UserSyncStatus(
                user_id=user.id,
                is_syncing=False,
                progress_percentage=0
            )
            db.add(sync_status)
            db.commit()
            
            print(f"✅ 测试用户准备完成: {user.email}")
            return True
            
        except Exception as e:
            print(f"❌ 测试用户设置失败: {e}")
            return False
        finally:
            db.close()
    
    def simulate_sync_request(self, request_id, delay=0):
        """模拟同步请求"""
        if delay > 0:
            time.sleep(delay)
        
        db = SessionLocal()
        result = {
            'request_id': request_id,
            'success': False,
            'acquired_lock': False,
            'timestamp': datetime.now().isoformat(),
            'error': None
        }
        
        try:
            # 尝试获取行锁
            sync_status = db.query(UserSyncStatus).filter(
                UserSyncStatus.user_id == self.test_user_id
            ).with_for_update(nowait=True).first()
            
            if sync_status:
                result['acquired_lock'] = True
                
                # 检查是否已在同步
                if sync_status.is_syncing:
                    result['error'] = 'Already syncing'
                    with self.lock:
                        self.results.append(result)
                    return result
                
                # 开始同步
                sync_status.is_syncing = True
                sync_status.started_at = datetime.utcnow()
                sync_status.task_id = f"task_{request_id}"
                db.commit()
                
                # 模拟同步工作
                time.sleep(1)  # 模拟同步耗时
                
                # 完成同步
                sync_status.is_syncing = False
                sync_status.progress_percentage = 100
                db.commit()
                
                result['success'] = True
                print(f"  ✅ 请求 {request_id}: 同步完成")
            else:
                result['error'] = 'Sync status not found'
                
        except Exception as e:
            result['error'] = str(e)
            if "could not obtain lock" in str(e) or "nowait" in str(e).lower():
                result['error'] = 'Lock timeout - concurrent access blocked'
                print(f"  🔒 请求 {request_id}: 被并发控制阻止")
            else:
                print(f"  ❌ 请求 {request_id}: 错误 - {e}")
        finally:
            db.close()
            with self.lock:
                self.results.append(result)
        
        return result
    
    def test_concurrent_requests(self, num_requests=5):
        """测试并发请求"""
        print(f"\n🔍 测试 {num_requests} 个并发同步请求")
        
        threads = []
        self.results = []
        
        # 启动多个并发请求
        for i in range(num_requests):
            thread = threading.Thread(
                target=self.simulate_sync_request,
                args=(i + 1, i * 0.1)  # 稍微错开启动时间
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        return self.analyze_results()
    
    def analyze_results(self):
        """分析测试结果"""
        print("\n📊 并发控制测试结果分析:")
        
        successful_syncs = [r for r in self.results if r['success']]
        blocked_requests = [r for r in self.results if 'concurrent access blocked' in str(r['error'])]
        failed_requests = [r for r in self.results if r['error'] and 'concurrent access blocked' not in str(r['error'])]
        
        print(f"   成功的同步: {len(successful_syncs)}")
        print(f"   被阻止的请求: {len(blocked_requests)}")
        print(f"   失败的请求: {len(failed_requests)}")
        
        # 详细结果
        for result in self.results:
            status = "✅" if result['success'] else "🔒" if 'concurrent access blocked' in str(result['error']) else "❌"
            print(f"   {status} 请求 {result['request_id']}: {result['error'] or 'Success'}")
        
        # 验证并发控制是否正确工作
        if len(successful_syncs) == 1 and len(blocked_requests) >= 1:
            print("\n🎉 并发控制机制工作正常!")
            print("   - 只有一个请求成功获得锁并完成同步")
            print("   - 其他请求被正确阻止")
            return True
        elif len(successful_syncs) > 1:
            print("\n⚠️  并发控制可能有问题:")
            print("   - 多个请求同时成功，可能存在竞态条件")
            return False
        elif len(successful_syncs) == 0:
            print("\n⚠️  所有请求都失败:")
            print("   - 可能存在配置问题")
            return False
        else:
            print("\n✅ 并发控制基本正常")
            return True
    
    def test_sequential_requests(self):
        """测试顺序请求"""
        print("\n🔍 测试顺序同步请求")
        
        self.results = []
        
        # 发送两个顺序请求
        self.simulate_sync_request(1)
        time.sleep(0.5)  # 确保第一个请求完成
        self.simulate_sync_request(2)
        
        successful_syncs = [r for r in self.results if r['success']]
        
        if len(successful_syncs) == 2:
            print("   ✅ 顺序请求都成功完成")
            return True
        else:
            print("   ❌ 顺序请求处理有问题")
            return False

def test_database_lock_mechanism():
    """测试数据库锁机制"""
    print("🔍 测试数据库行锁机制")
    
    test = ConcurrentSyncTest()
    
    if not test.setup_test_user():
        return False
    
    # 测试1: 并发请求
    concurrent_result = test.test_concurrent_requests(5)
    
    # 测试2: 顺序请求  
    sequential_result = test.test_sequential_requests()
    
    return concurrent_result and sequential_result

def test_sync_status_consistency():
    """测试同步状态一致性"""
    print("\n🔍 测试同步状态一致性")
    
    db = SessionLocal()
    try:
        # 检查所有用户的同步状态
        sync_statuses = db.query(UserSyncStatus).all()
        
        inconsistent_count = 0
        for status in sync_statuses:
            # 检查是否有长时间停留在同步状态的记录
            if status.is_syncing and status.started_at:
                # 处理时区问题
                from datetime import timezone
                now = datetime.now(timezone.utc)
                started_at = status.started_at
                if started_at.tzinfo is None:
                    # 如果数据库时间没有时区信息，假设为UTC
                    started_at = started_at.replace(tzinfo=timezone.utc)
                
                time_diff = now - started_at
                if time_diff.total_seconds() > 3600:  # 超过1小时
                    inconsistent_count += 1
                    print(f"   ⚠️  用户 {status.user_id} 同步状态异常 (同步中超过1小时)")
        
        if inconsistent_count == 0:
            print("   ✅ 所有同步状态一致")
            return True
        else:
            print(f"   ❌ 发现 {inconsistent_count} 个异常同步状态")
            return False
            
    except Exception as e:
        print(f"   ❌ 状态检查失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主测试函数"""
    print("🚀 开始测试并发控制机制")
    print("=" * 60)
    
    tests = [
        test_database_lock_mechanism,
        test_sync_status_consistency
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
        print("🎉 所有并发控制测试通过!")
        return True
    else:
        print("⚠️  部分并发控制测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)