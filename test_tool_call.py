#!/usr/bin/env python3
"""
测试工具调用功能
"""
import asyncio
import socketio
import json
from datetime import datetime

# Socket.IO 客户端
sio = socketio.AsyncClient(logger=True, engineio_logger=True)

# 服务器配置
SERVER_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMTExNDkyLCJpYXQiOjE3NTMwMjUwOTJ9.zBVom0vqSWBKAQTyHfw4f_BwEPmHIkkg-5nt95bCouw"

# 事件记录
events_log = []

@sio.event
async def connect():
    print("[Connected] WebSocket连接成功")
    events_log.append({"event": "connect", "time": datetime.now().isoformat()})

@sio.event
async def disconnect():
    print("[Disconnected] WebSocket断开连接")
    events_log.append({"event": "disconnect", "time": datetime.now().isoformat()})

@sio.event
async def connected(data):
    print(f"[Connected Event] 服务器确认连接: {data}")
    events_log.append({"event": "connected", "data": data, "time": datetime.now().isoformat()})

@sio.event
async def agent_event(data):
    print(f"\n[Agent Event] 类型: {data.get('type')}")
    print(f"详细数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
    events_log.append({"event": "agent_event", "data": data, "time": datetime.now().isoformat()})
    
    # 特别关注工具调用事件
    if data.get('type') in ['tool_call_start', 'tool_call_result', 'tool_error']:
        print("\n>>> 工具调用事件 <<<")
        print(f"工具名称: {data.get('tool_name')}")
        print(f"工具参数: {data.get('tool_args')}")
        print(f"工具结果: {data.get('tool_result')}")
        if data.get('error'):
            print(f"错误信息: {data.get('error')}")

@sio.event
async def error(data):
    print(f"[Error] 错误事件: {data}")
    events_log.append({"event": "error", "data": data, "time": datetime.now().isoformat()})

async def test_tool_calls():
    """测试各种工具调用"""
    try:
        # 连接到服务器
        print(f"正在连接到 {SERVER_URL}...")
        await sio.connect(
            SERVER_URL,
            auth={'token': TOKEN},
            transports=['polling', 'websocket']
        )
        
        # 等待连接确认
        await asyncio.sleep(2)
        
        # 测试用例
        test_cases = [
            {
                "name": "搜索邮件",
                "message": "帮我搜索最近一周的重要邮件",
                "expected_tool": "search_email_history"
            },
            {
                "name": "读取日报",
                "message": "显示今天的邮件日报",
                "expected_tool": "read_daily_report"
            },
            {
                "name": "批量标记",
                "message": "把所有促销邮件标记为已读",
                "expected_tool": "bulk_mark_read"
            },
            {
                "name": "更新偏好",
                "message": "把newsletter类邮件设为低优先级",
                "expected_tool": "update_user_preferences"
            }
        ]
        
        for test_case in test_cases:
            print(f"\n{'='*60}")
            print(f"测试: {test_case['name']}")
            print(f"消息: {test_case['message']}")
            print(f"期望工具: {test_case['expected_tool']}")
            print(f"{'='*60}")
            
            # 清空事件日志
            events_log.clear()
            
            # 发送消息
            await sio.emit('agent_message', {
                'message': test_case['message'],
                'session_id': f'test_session_{test_case["name"]}'
            })
            
            # 等待响应
            print("等待响应...")
            await asyncio.sleep(10)  # 等待10秒以确保收到所有事件
            
            # 分析结果
            print(f"\n收到 {len(events_log)} 个事件:")
            tool_events = [e for e in events_log if e.get('data', {}).get('type') in ['tool_call_start', 'tool_call_result', 'tool_error']]
            print(f"工具相关事件: {len(tool_events)}")
            
            for event in tool_events:
                data = event['data']
                print(f"  - {data.get('type')}: {data.get('tool_name')}")
            
            # 短暂延迟
            await asyncio.sleep(2)
        
        # 保存所有事件日志
        with open('tool_call_events.json', 'w', encoding='utf-8') as f:
            json.dump(events_log, f, ensure_ascii=False, indent=2)
        print("\n事件日志已保存到 tool_call_events.json")
        
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sio.disconnect()

async def main():
    """主函数"""
    await test_tool_calls()

if __name__ == "__main__":
    asyncio.run(main())