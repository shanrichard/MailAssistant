#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import time
import json

print("检查前端WebSocket优化效果...\n")

# 获取认证cookie
login_session = requests.Session()

# 先访问主页
response = login_session.get('http://localhost:3000/')
print(f"访问主页状态: {response.status_code}")

# 等待一下让WebSocket建立连接
print("\n等待5秒观察WebSocket连接...")
time.sleep(5)

# 检查后端日志
print("\n检查最近10秒的WebSocket连接情况:")
logs_response = requests.post(
    'http://localhost:8000/api/debug/logs/all',
    json={"frontend_errors": []},
    headers={"Content-Type": "application/json"}
)

if logs_response.status_code == 200:
    logs = logs_response.json()
    ws_events = []
    
    # 过滤最近10秒的WebSocket事件
    current_time = time.time()
    for error in logs.get('errors', []):
        if 'WebSocket connected' in error.get('message', '') or 'WebSocket disconnected' in error.get('message', ''):
            # 解析时间戳
            timestamp_str = error.get('timestamp', '').split(',')[0]
            try:
                # 简单处理，假设是今天的日志
                ws_events.append({
                    'time': timestamp_str,
                    'event': 'connected' if 'connected' in error['message'] else 'disconnected',
                    'sid': error['message'].split('"sid": "')[1].split('"')[0] if '"sid": "' in error['message'] else 'unknown'
                })
            except:
                pass
    
    # 统计连接情况
    if ws_events:
        # 只看最后20个事件
        recent_events = ws_events[-20:]
        
        print(f"\n最近的WebSocket事件:")
        for event in recent_events[-10:]:
            print(f"  {event['time']} - {event['event']} - SID: {event['sid']}")
        
        # 统计
        connect_count = sum(1 for e in recent_events if e['event'] == 'connected')
        disconnect_count = sum(1 for e in recent_events if e['event'] == 'disconnected')
        
        print(f"\n统计(最近20个事件):")
        print(f"  连接次数: {connect_count}")
        print(f"  断开次数: {disconnect_count}")
        
        # 检查是否有快速重连模式
        if len(recent_events) >= 4:
            # 检查是否在1秒内有多次连接
            print(f"\n诊断结果:")
            if connect_count > 5 and disconnect_count > 5:
                print("  ❌ 发现频繁的连接/断开模式")
                print("  可能原因:")
                print("  1. 前端代码未正确应用优化")
                print("  2. React.StrictMode仍在导致双重渲染")
                print("  3. 组件生命周期管理仍有问题")
            else:
                print("  ✅ WebSocket连接相对稳定")
    else:
        print("没有找到WebSocket事件")
else:
    print(f"获取日志失败: {logs_response.status_code}")