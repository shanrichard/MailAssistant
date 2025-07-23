#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import json
from datetime import datetime
from collections import defaultdict

def monitor_websocket_realtime():
    print("实时监控WebSocket连接...\n")
    
    seen_events = set()
    connection_count = defaultdict(int)
    
    while True:
        try:
            # 获取日志
            response = requests.post(
                'http://localhost:8000/api/debug/logs/all',
                json={"frontend_errors": []},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logs = response.json()
                
                # 处理每条日志
                for error in logs.get('errors', []):
                    # 创建唯一标识符
                    event_id = f"{error.get('timestamp')}_{error.get('message', '')[:50]}"
                    
                    # 跳过已处理的事件
                    if event_id in seen_events:
                        continue
                    
                    seen_events.add(event_id)
                    message = error.get('message', '')
                    
                    # 检查WebSocket事件
                    if 'WebSocket connection attempt' in message:
                        try:
                            sid = message.split('"sid": "')[1].split('"')[0]
                            timestamp = error.get('timestamp', '')
                            print(f"[{timestamp}] 🔵 连接尝试: {sid}")
                        except:
                            pass
                    elif 'WebSocket connected' in message:
                        try:
                            sid = message.split('"sid": "')[1].split('"')[0]
                            timestamp = error.get('timestamp', '')
                            connection_count[sid] += 1
                            print(f"[{timestamp}] ✅ 连接成功: {sid} (第{connection_count[sid]}次)")
                        except:
                            pass
                    elif 'WebSocket disconnected' in message:
                        try:
                            sid = message.split('"sid": "')[1].split('"')[0]
                            timestamp = error.get('timestamp', '')
                            print(f"[{timestamp}] ❌ 断开连接: {sid}")
                        except:
                            pass
                    
                    # 检查前端错误
                    if error.get('source') == 'frontend':
                        if 'auth' in message.lower() or 'token' in message.lower():
                            print(f"[{error.get('timestamp')}] ⚠️  前端错误: {message[:100]}")
        
        except Exception as e:
            print(f"监控错误: {e}")
        
        # 每秒检查一次
        time.sleep(1)

if __name__ == "__main__":
    try:
        monitor_websocket_realtime()
    except KeyboardInterrupt:
        print("\n监控已停止")