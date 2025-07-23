#!/usr/bin/env python3
"""测试FastAPI BackgroundTasks"""
import requests
import time
import json

def test_background_tasks():
    """测试后台任务是否正常启动"""
    
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMjUyNzIwLCJpYXQiOjE3NTMxNjYzMjB9.H6CjDP5L3wwwO1lrdJyEwX8id7TxU_9J7BQ52v4IMUM"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 先清理可能的僵死任务
    print("1. 清理可能的僵死任务...")
    # （这里可以添加清理逻辑）
    
    # 创建同步任务
    print("\n2. 创建同步任务...")
    response = requests.post(
        "http://localhost:8000/api/gmail/sync/smart",
        headers=headers,
        params={"background": True}  # 明确要求后台执行
    )
    
    if response.status_code != 200:
        print(f"❌ 创建任务失败: {response.text}")
        return
    
    data = response.json()
    task_id = data.get("task_id")
    print(f"✓ 任务创建成功: {task_id}")
    
    # 等待一下让后台任务启动
    time.sleep(2)
    
    # 查看日志
    print("\n3. 查看后端日志...")
    log_response = requests.get("http://localhost:8000/api/debug/logs/backend")
    if log_response.status_code == 200:
        logs = log_response.json()
        recent_logs = logs.get("errors", [])[-20:]
        
        print("\n最近的相关日志:")
        for log in recent_logs:
            msg = log.get("message", "")
            if any(keyword in msg for keyword in ["准备启动", "使用Background", "开始执行带心跳", task_id]):
                print(f"  - {log.get('timestamp')}: {msg[:100]}")
    
    # 监控进度
    print(f"\n4. 监控任务进度...")
    for i in range(6):
        time.sleep(5)
        
        progress_response = requests.get(
            f"http://localhost:8000/api/gmail/sync/progress/{task_id}",
            headers=headers
        )
        
        if progress_response.status_code == 200:
            progress_data = progress_response.json()
            print(f"[{i+1}] 更新时间: {progress_data.get('updatedAt')}, "
                  f"进度: {progress_data.get('progress')}%, "
                  f"运行中: {progress_data.get('isRunning')}")

if __name__ == "__main__":
    test_background_tasks()