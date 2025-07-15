"""
Agent WebSocket处理
"""
import json
import asyncio
from typing import Dict, Set, Any
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from datetime import datetime

from ..core.logging import get_logger
from ..core.config import settings
from ..api.auth import get_current_user_from_token
from ..models.user import User

logger = get_logger(__name__)

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃的WebSocket连接 {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 存储连接元数据
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str = None):
        """建立WebSocket连接"""
        await websocket.accept()
        
        connection_id = connection_id or f"ws_{datetime.now().timestamp()}"
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
            self.connection_metadata[user_id] = {}
            
        self.active_connections[user_id][connection_id] = websocket
        self.connection_metadata[user_id][connection_id] = {
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "message_count": 0
        }
        
        logger.info("WebSocket connected", 
                   user_id=user_id, 
                   connection_id=connection_id)
        
        # 发送连接确认
        await self.send_personal_message(user_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "WebSocket连接已建立"
        })
        
        return connection_id
        
    def disconnect(self, user_id: str, connection_id: str):
        """断开WebSocket连接"""
        try:
            if user_id in self.active_connections:
                if connection_id in self.active_connections[user_id]:
                    del self.active_connections[user_id][connection_id]
                    
                if connection_id in self.connection_metadata.get(user_id, {}):
                    del self.connection_metadata[user_id][connection_id]
                    
                # 如果用户没有活跃连接，清理用户记录
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    if user_id in self.connection_metadata:
                        del self.connection_metadata[user_id]
                        
            logger.info("WebSocket disconnected", 
                       user_id=user_id, 
                       connection_id=connection_id)
                       
        except Exception as e:
            logger.error("Error during WebSocket disconnect", 
                        user_id=user_id, 
                        connection_id=connection_id, 
                        error=str(e))
            
    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """发送消息给特定用户的所有连接"""
        if user_id not in self.active_connections:
            logger.warning("No active connections for user", user_id=user_id)
            return
            
        message_json = json.dumps(message, ensure_ascii=False)
        
        # 发送给用户的所有活跃连接
        disconnected_connections = []
        
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(message_json)
                
                # 更新连接元数据
                if connection_id in self.connection_metadata.get(user_id, {}):
                    self.connection_metadata[user_id][connection_id]["last_activity"] = datetime.utcnow()
                    self.connection_metadata[user_id][connection_id]["message_count"] += 1
                    
            except Exception as e:
                logger.warning("Failed to send message to connection", 
                              user_id=user_id, 
                              connection_id=connection_id, 
                              error=str(e))
                disconnected_connections.append(connection_id)
                
        # 清理断开的连接
        for connection_id in disconnected_connections:
            self.disconnect(user_id, connection_id)
            
    async def send_task_progress(self, user_id: str, task_id: str, progress: Dict[str, Any]):
        """发送任务进度更新"""
        message = {
            "type": "task_progress",
            "task_id": task_id,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(user_id, message)
        
    async def send_agent_response(self, user_id: str, agent_type: str, response: Dict[str, Any]):
        """发送Agent响应"""
        message = {
            "type": "agent_response",
            "agent_type": agent_type,
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(user_id, message)
        
    async def send_notification(self, user_id: str, notification: Dict[str, Any]):
        """发送通知"""
        message = {
            "type": "notification",
            "notification": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(user_id, message)
        
    def get_user_connections_count(self, user_id: str) -> int:
        """获取用户连接数"""
        return len(self.active_connections.get(user_id, {}))
        
    def get_total_connections_count(self) -> int:
        """获取总连接数"""
        return sum(len(connections) for connections in self.active_connections.values())
        
    def get_connection_info(self, user_id: str) -> Dict[str, Any]:
        """获取连接信息"""
        if user_id not in self.active_connections:
            return {"active_connections": 0, "connections": []}
            
        connections = []
        for connection_id, metadata in self.connection_metadata.get(user_id, {}).items():
            connections.append({
                "connection_id": connection_id,
                "connected_at": metadata["connected_at"].isoformat(),
                "last_activity": metadata["last_activity"].isoformat(),
                "message_count": metadata["message_count"]
            })
            
        return {
            "active_connections": len(connections),
            "connections": connections
        }

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()

async def websocket_handler(websocket: WebSocket, token: str = None):
    """WebSocket连接处理器"""
    user = None
    user_id = None
    connection_id = None
    
    try:
        # 验证用户身份
        if not token:
            await websocket.close(code=4001, reason="Missing authentication token")
            return
            
        try:
            user = await get_current_user_from_token(token)
            user_id = str(user.id)
        except Exception as e:
            await websocket.close(code=4003, reason="Invalid authentication token")
            return
            
        # 建立连接
        connection_id = await websocket_manager.connect(websocket, user_id)
        
        # 消息处理循环
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 处理消息
                await handle_websocket_message(user_id, connection_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error("Error processing WebSocket message", 
                           user_id=user_id, 
                           error=str(e))
                await websocket_manager.send_personal_message(user_id, {
                    "type": "error",
                    "message": f"Message processing failed: {str(e)}"
                })
                
    except Exception as e:
        logger.error("WebSocket handler error", error=str(e))
    finally:
        # 清理连接
        if user_id and connection_id:
            websocket_manager.disconnect(user_id, connection_id)

async def handle_websocket_message(user_id: str, connection_id: str, message: Dict[str, Any]):
    """处理WebSocket消息"""
    message_type = message.get("type", "")
    
    try:
        if message_type == "ping":
            # 心跳检测
            await websocket_manager.send_personal_message(user_id, {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        elif message_type == "subscribe":
            # 订阅特定类型的消息
            subscription_types = message.get("subscription_types", [])
            # TODO: 实现订阅机制
            await websocket_manager.send_personal_message(user_id, {
                "type": "subscription_confirmed",
                "subscription_types": subscription_types
            })
            
        elif message_type == "agent_message":
            # Agent相关消息
            agent_type = message.get("agent_type", "")
            agent_message = message.get("message", "")
            
            # TODO: 集成到Agent处理流程
            await websocket_manager.send_personal_message(user_id, {
                "type": "agent_response",
                "agent_type": agent_type,
                "response": {"message": f"Received message for {agent_type}: {agent_message}"}
            })
            
        else:
            await websocket_manager.send_personal_message(user_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            })
            
    except Exception as e:
        logger.error("Error handling WebSocket message", 
                    user_id=user_id, 
                    message_type=message_type, 
                    error=str(e))
        await websocket_manager.send_personal_message(user_id, {
            "type": "error",
            "message": f"Failed to process message: {str(e)}"
        })