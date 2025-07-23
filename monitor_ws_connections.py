#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import time
import json
from datetime import datetime

def monitor_websocket_connections():
    print("监控WebSocket连接状态...\n")
    
    # 存储已见过的SID
    seen_sids = set()
    connection_count = 0
    disconnection_count = 0
    
    # 监控30秒
    start_time = time.time()
    while time.time() - start_time < 30:
        try:
            # 获取日志
            response = requests.post(
                'http://localhost:8000/api/debug/logs/all',
                json={"frontend_errors": []},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logs = response.json()
                
                # 处理每条错误日志
                for error in logs.get('errors', []):
                    message = error.get('message', '')
                    
                    # 检查WebSocket事件
                    if 'WebSocket connected' in message:
                        try:
                            sid = message.split('"sid": "')[1].split('"')[0]
                            if sid not in seen_sids:
                                seen_sids.add(sid)
                                connection_count += 1
                                timestamp = error.get('timestamp', '')
                                print(f"[{timestamp}] 新连接: {sid}")
                        except:
                            pass
                    elif 'WebSocket disconnected' in message:
                        try:
                            sid = message.split('"sid": "')[1].split('"')[0]
                            disconnection_count += 1
                            timestamp = error.get('timestamp', '')
                            print(f"[{timestamp}] 断开连接: {sid}")
                        except:
                            pass
        
        except Exception as e:
            print(f"错误: {e}")
        
        # 每2秒检查一次
        time.sleep(2)
    
    print(f"\n=== 30秒监控结果 ===")
    print(f"总连接数: {connection_count}")
    print(f"总断开数: {disconnection_count}")
    print(f"活跃连接数: {connection_count - disconnection_count}")
    print(f"不同的连接ID数: {len(seen_sids)}")
    
    if connection_count > 5:
        print("\n⚠️ 警告: 连接数过多，可能存在重复连接问题")
    else:
        print("\n✅ 连接数正常")

if __name__ == "__main__":
    monitor_websocket_connections()