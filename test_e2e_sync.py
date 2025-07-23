#!/usr/bin/env python3
"""完整的端到端测试脚本"""
import asyncio
import requests
import time
import sys
import os
import psycopg2
from datetime import datetime

# 配置
API_BASE = os.environ.get('API_BASE', 'http://localhost:8000/api/v1')
TEST_USER_ID = os.environ.get('TEST_USER_ID')
DB_URL = "postgresql://dev_user:dev_password@localhost:5432/mailassistant_dev"

# 测试令牌（需要先登录获取）
TOKEN = None

def get_auth_headers():
    """获取认证头"""
    if not TOKEN:
        print("❌ 未设置认证令牌")
        return {}
    return {"Authorization": f"Bearer {TOKEN}"}

def cleanup_database():
    """清理数据库中的测试数据"""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        # 清理同步状态
        cur.execute("""
            UPDATE user_sync_status 
            SET is_syncing = false, 
                progress_percentage = 0,
                error_message = NULL,
                task_id = NULL
            WHERE user_id = %s
        """, (TEST_USER_ID,))
        conn.commit()
        print("✅ 数据库清理完成")
    except Exception as e:
        print(f"❌ 数据库清理失败: {e}")
    finally:
        cur.close()
        conn.close()

def test_api_endpoint():
    """测试1: API端点是否正确（测试3-11-2修复）"""
    print("\n1. 测试API端点...")
    
    # 发起同步请求
    response = requests.post(
        f"{API_BASE}/gmail/sync/smart",
        headers=get_auth_headers(),
        json={"force_full": True}
    )
    
    if response.status_code == 200:
        data = response.json()
        if "task_id" in data:
            print(f"✅ API端点正常，任务ID: {data['task_id']}")
            return data["task_id"]
        else:
            print("❌ API响应缺少task_id")
            return None
    else:
        print(f"❌ API请求失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return None

def test_heartbeat_mechanism(task_id):
    """测试2: 心跳机制是否工作（测试3-11-1修复）"""
    print("\n2. 测试心跳机制...")
    
    # 等待几秒让心跳开始
    time.sleep(3)
    
    # 检查心跳状态
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        # 检查最近5秒的心跳
        cur.execute("""
            SELECT COUNT(*) FROM sync_task_heartbeat 
            WHERE task_id = %s 
            AND last_heartbeat > NOW() - INTERVAL '5 seconds'
        """, (task_id,))
        
        count = cur.fetchone()[0]
        if count > 0:
            print(f"✅ 心跳机制正常工作，找到 {count} 个活跃心跳")
            return True
        else:
            print("❌ 未找到活跃心跳")
            return False
    except Exception as e:
        print(f"❌ 心跳检查失败: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def test_scheduler_cleanup():
    """测试3: 调度器僵死任务清理（测试3-11-4修复）"""
    print("\n3. 测试调度器清理...")
    
    # 检查调度器状态
    response = requests.get(
        f"{API_BASE}/scheduler/status",
        headers=get_auth_headers()
    )
    
    if response.status_code == 200:
        data = response.json()
        jobs = data.get("jobs", [])
        
        # 查找僵死任务清理作业
        cleanup_job = None
        for job in jobs:
            if job.get("id") == "zombie_task_cleanup":
                cleanup_job = job
                break
        
        if cleanup_job:
            print(f"✅ 僵死任务清理作业已配置")
            print(f"   下次运行: {cleanup_job.get('next_run_time')}")
            return True
        else:
            print("❌ 未找到僵死任务清理作业")
            return False
    else:
        print(f"❌ 调度器状态查询失败: {response.status_code}")
        return False

def test_database_constraints():
    """测试4: 数据库约束（测试3-11-3修复）"""
    print("\n4. 测试数据库约束...")
    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    test_passed = True
    
    try:
        # 测试1: 尝试创建不一致的状态
        print("   - 测试状态一致性约束...")
        try:
            cur.execute("""
                UPDATE user_sync_status 
                SET is_syncing = true, progress_percentage = 100
                WHERE user_id = %s
            """, (TEST_USER_ID,))
            conn.commit()
            print("     ❌ 状态一致性约束未触发")
            test_passed = False
        except Exception as e:
            conn.rollback()
            if "chk_sync_state_consistency" in str(e):
                print("     ✅ 状态一致性约束正常")
            else:
                print(f"     ❌ 意外错误: {e}")
                test_passed = False
        
        # 测试2: 检查索引
        print("   - 检查性能索引...")
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'user_sync_status' 
            AND indexname IN ('idx_sync_status_updated', 'idx_sync_status_zombie_check')
        """)
        indexes = [row[0] for row in cur.fetchall()]
        
        if len(indexes) >= 2:
            print(f"     ✅ 找到 {len(indexes)} 个性能索引")
        else:
            print(f"     ❌ 缺少索引，只找到: {indexes}")
            test_passed = False
            
        return test_passed
        
    except Exception as e:
        print(f"❌ 约束测试失败: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def test_concurrent_sync():
    """测试5: 并发同步请求（综合测试）"""
    print("\n5. 测试并发同步请求...")
    
    # 先清理状态
    cleanup_database()
    
    # 发起第一个同步请求
    response1 = requests.post(
        f"{API_BASE}/gmail/sync/smart",
        headers=get_auth_headers(),
        json={"force_full": False}
    )
    
    if response1.status_code != 200:
        print(f"❌ 第一个请求失败: {response1.status_code}")
        return False
    
    task_id_1 = response1.json().get("task_id")
    print(f"   第一个任务: {task_id_1}")
    
    # 立即发起第二个请求（应该被拒绝或返回相同任务）
    time.sleep(0.5)
    response2 = requests.post(
        f"{API_BASE}/gmail/sync/smart",
        headers=get_auth_headers(),
        json={"force_full": False}
    )
    
    if response2.status_code == 200:
        task_id_2 = response2.json().get("task_id")
        if task_id_2 == task_id_1:
            print(f"✅ 并发保护正常，返回相同任务ID")
            return True
        else:
            print(f"❌ 创建了新任务: {task_id_2}")
            return False
    elif response2.status_code == 409:
        print("✅ 并发保护正常，拒绝了第二个请求")
        return True
    else:
        print(f"❌ 意外响应: {response2.status_code}")
        return False

def test_progress_tracking(task_id):
    """测试6: 进度跟踪"""
    print("\n6. 测试进度跟踪...")
    
    # 等待一段时间让任务运行
    max_wait = 30
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < max_wait:
        response = requests.get(
            f"{API_BASE}/gmail/sync/status",
            headers=get_auth_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            progress = data.get("progress_percentage", 0)
            is_syncing = data.get("is_syncing", False)
            
            if progress != last_progress:
                print(f"   进度: {progress}% (同步中: {is_syncing})")
                last_progress = progress
            
            # 如果完成或出错，退出
            if not is_syncing:
                if progress == 100:
                    print("✅ 同步完成，进度跟踪正常")
                    return True
                elif data.get("error_message"):
                    print(f"❌ 同步出错: {data['error_message']}")
                    return False
                break
        
        time.sleep(2)
    
    print("❌ 同步超时")
    return False

async def main():
    """主测试函数"""
    print("="*50)
    print("完整端到端测试开始")
    print("="*50)
    
    # 先获取认证令牌
    global TOKEN
    print("\n获取认证令牌...")
    # 这里需要实际的登录流程，暂时使用环境变量
    TOKEN = os.environ.get('TEST_AUTH_TOKEN')
    if not TOKEN:
        print("❌ 请设置 TEST_AUTH_TOKEN 环境变量")
        print("   提示：可以从浏览器开发者工具中复制令牌")
        return False
    
    # 清理初始状态
    cleanup_database()
    
    # 运行测试
    results = {
        "API端点": False,
        "心跳机制": False,
        "调度器清理": False,
        "数据库约束": False,
        "并发保护": False,
        "进度跟踪": False
    }
    
    # 测试1: API端点
    task_id = test_api_endpoint()
    results["API端点"] = task_id is not None
    
    if task_id:
        # 测试2: 心跳机制
        results["心跳机制"] = test_heartbeat_mechanism(task_id)
        
        # 测试6: 进度跟踪
        results["进度跟踪"] = test_progress_tracking(task_id)
    
    # 测试3: 调度器清理
    results["调度器清理"] = test_scheduler_cleanup()
    
    # 测试4: 数据库约束
    results["数据库约束"] = test_database_constraints()
    
    # 测试5: 并发保护
    results["并发保护"] = test_concurrent_sync()
    
    # 输出结果
    print("\n" + "="*50)
    print("测试结果汇总:")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n总计: {passed_tests}/{total_tests} 通过")
    
    # 清理
    cleanup_database()
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
