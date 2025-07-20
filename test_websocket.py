#!/usr/bin/env python3
"""
测试 WebSocket 连接的脚本
"""
import asyncio
import socketio
import sys
import os

# 添加backend到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.core.config import settings

# 测试token（需要从前端获取一个有效的token）
# 请在浏览器控制台运行以下命令获取token：
# JSON.parse(localStorage.getItem('mailassistant_auth_token')).state.token
TEST_TOKEN = "YOUR_TOKEN_HERE"  # 请替换为实际的token

async def test_connection():
    """测试Socket.IO连接"""
    sio = socketio.AsyncClient(
        logger=True,
        engineio_logger=True
    )
    
    @sio.event
    async def connect():
        print("✅ Connected to Socket.IO server")
        
    @sio.event
    async def connect_error(data):
        print(f"❌ Connection error: {data}")
        
    @sio.event
    async def disconnect():
        print("🔌 Disconnected from Socket.IO server")
        
    @sio.event
    async def connected(data):
        print(f"📨 Received 'connected' event: {data}")
        
    @sio.event
    async def error(data):
        print(f"❌ Received error: {data}")
    
    try:
        print(f"🔌 Attempting to connect to {settings.api_url}")
        print(f"🔑 Using token: {TEST_TOKEN[:20]}...")
        
        # 尝试连接
        await sio.connect(
            settings.api_url,
            auth={'token': TEST_TOKEN},
            transports=['polling', 'websocket']  # 先polling后websocket
        )
        
        # 等待一会儿看看连接状态
        print("⏳ Waiting for connection events...")
        await asyncio.sleep(5)
        
        # 尝试发送消息
        if sio.connected:
            print("📤 Sending test message...")
            await sio.emit('agent_message', {
                'message': 'Hello from test script',
                'session_id': 'test'
            })
            await asyncio.sleep(2)
        
        # 断开连接
        await sio.disconnect()
        
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 WebSocket Connection Test")
    print("=" * 50)
    asyncio.run(test_connection())