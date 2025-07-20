"""
Socket.IO WebSocket服务
"""
import socketio
import jwt
from datetime import datetime
from typing import Optional

from .core.config import settings
from .core.logging import get_logger
from .core.database import SessionLocal
from .core.errors import translate_error, AppError
from .models.user import User
from .agents.conversation_handler import ConversationHandler

logger = get_logger(__name__)

# 创建Socket.IO服务器
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    logger=True,  # 启用日志以调试连接问题
    engineio_logger=True,  # 启用引擎日志
    # 添加更多配置以支持WebSocket升级
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    allow_upgrades=True,  # 明确允许传输升级
    http_compression=True
)

# 存储用户会话信息
user_sessions = {}

def get_user_from_token(token: str) -> Optional[User]:
    """从JWT token获取用户信息"""
    try:
        payload = jwt.decode(
            token, 
            settings.security.secret_key, 
            algorithms=[settings.security.jwt_algorithm]
        )
        user_id = payload.get("sub")
        
        if not user_id:
            return None
            
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user
        finally:
            db.close()
            
    except jwt.PyJWTError as e:
        logger.warning("JWT decode error", error=str(e))
        return None

@sio.event
async def connect(sid, environ, auth):
    """处理WebSocket连接"""
    try:
        logger.info("WebSocket connection attempt", sid=sid, auth=auth, 
                   headers=dict(environ.get('asgi', {}).get('headers', [])),
                   query_string=environ.get('QUERY_STRING', ''))
        
        if not auth or 'token' not in auth:
            logger.warning("No auth token provided", sid=sid, auth=auth)
            # 不立即断开连接，而是返回False让客户端知道认证失败
            return False
            
        user = get_user_from_token(auth['token'])
        if not user:
            logger.warning("Invalid auth token", sid=sid)
            return False
            
        # 存储用户会话信息
        user_sessions[sid] = {
            'user_id': str(user.id),  # 确保是字符串
            'user': user,
            'connected_at': datetime.now()
        }
        
        logger.info("WebSocket connected", sid=sid, user_id=str(user.id))
        await sio.emit('connected', {'status': 'connected'}, room=sid)
        return True
    except Exception as e:
        logger.error("Error in connect handler", sid=sid, error=str(e), exc_info=True)
        return False

@sio.event
async def disconnect(sid):
    """处理WebSocket断开"""
    if sid in user_sessions:
        user_id = user_sessions[sid]['user_id']
        del user_sessions[sid]
        logger.info("WebSocket disconnected", sid=sid, user_id=user_id)
    else:
        logger.info("WebSocket disconnected", sid=sid)

@sio.event
async def agent_message(sid, data):
    """处理来自前端的消息"""
    if sid not in user_sessions:
        await sio.emit('error', {'message': 'Unauthorized'}, room=sid)
        return
        
    user_info = user_sessions[sid]
    user_id = user_info['user_id']
    user = user_info['user']
    message = data.get('message', '')
    session_id = data.get('session_id', 'default')
    
    logger.info("Received agent message", 
               sid=sid, 
               user_id=user_id, 
               session_id=session_id,
               message_length=len(message))
    
    # 检查速率限制
    from .services.rate_limiter import check_rate_limit
    
    if not await check_rate_limit(user_id):
        await sio.emit('agent_event', {
            'type': 'agent_error',
            'error': '请求过于频繁，请稍后再试',
            'timestamp': datetime.now().isoformat()
        }, room=sid)
        return
    
    try:
        # 创建数据库会话
        db = SessionLocal()
        try:
            # 创建ConversationHandler实例
            handler = ConversationHandler(user_id, db, user)
            
            # 流式传输响应
            async for event in handler.stream_response(message, session_id):
                if event:  # 忽略None事件
                    await sio.emit('agent_event', event, room=sid)
                    
            # 发送完成事件
            await sio.emit('agent_event', {
                'type': 'stream_end',
                'timestamp': datetime.now().isoformat()
            }, room=sid)
            
        finally:
            db.close()
            
    except Exception as e:
        # 将异常转换为用户友好的错误
        if isinstance(e, AppError):
            app_error = e
        else:
            app_error = translate_error(e)
        
        logger.error("Error processing agent message", 
                    sid=sid, 
                    user_id=user_id, 
                    error=str(e),
                    error_category=app_error.category.value)
        
        # 发送用户友好的错误消息
        error_response = app_error.to_dict()
        error_response['timestamp'] = datetime.now().isoformat()
        await sio.emit('agent_event', error_response, room=sid)

@sio.event
async def typing_start(sid, data):
    """用户开始输入"""
    if sid in user_sessions:
        session_id = data.get('session_id', 'default')
        logger.debug("User typing", sid=sid, session_id=session_id)

@sio.event
async def typing_stop(sid, data):
    """用户停止输入"""
    if sid in user_sessions:
        session_id = data.get('session_id', 'default')
        logger.debug("User stopped typing", sid=sid, session_id=session_id)

# 创建Socket.IO ASGI应用
def create_socketio_app():
    """创建Socket.IO ASGI应用"""
    return socketio.ASGIApp(sio)