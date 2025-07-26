"""
Socket.IO 服务器配置和事件处理
完整实现：认证、缓存管理、错误处理、流式响应
"""
import socketio
import asyncio
from typing import Dict, Any, Tuple, Optional
from time import time
from contextlib import asynccontextmanager
from weakref import WeakSet
from .core.logging import get_logger
from .core.config import settings
from .agents.conversation_handler import ConversationHandler
from .core.database import get_db, SessionLocal
from .api.auth import get_current_user_from_token
from .models.user import User

logger = get_logger(__name__)

# 创建 Socket.IO 服务器
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "null"  # 允许文件系统访问用于测试
    ],
    logger=True,
    engineio_logger=True
)

# 连接会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 优化的Handler缓存：{(user_id, session_id): handler}
conversation_handlers: Dict[Tuple[str, str], ConversationHandler] = {}
handler_locks: Dict[Tuple[str, str], asyncio.Lock] = {}
active_handlers: WeakSet[ConversationHandler] = WeakSet()

# 消息去重缓存：存储最近处理的message_id，防止重复处理
processed_messages: Dict[str, float] = {}
MESSAGE_DEDUP_TTL = 300  # 5分钟TTL

# 错误类型定义
class SocketErrorType:
    AUTHENTICATION_REQUIRED = "authentication_required"
    PROCESSING_ERROR = "processing_error"
    TOOL_ERROR = "tool_error"
    RATE_LIMIT = "rate_limit"
    VALIDATION_ERROR = "validation_error"


@asynccontextmanager
async def get_db_session():
    """异步数据库会话管理器"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_conversation_handler(user_id: str, session_id: str, db_session, user):
    """线程安全的Handler获取和管理"""
    cache_key = (user_id, session_id)
    
    # 获取或创建锁
    if cache_key not in handler_locks:
        handler_locks[cache_key] = asyncio.Lock()
    
    async with handler_locks[cache_key]:
        # 获取或创建Handler
        if cache_key not in conversation_handlers:
            handler = ConversationHandler(user_id, db_session, user)
            conversation_handlers[cache_key] = handler
            active_handlers.add(handler)
            logger.info(f"Created new handler for {cache_key}")
        else:
            handler = conversation_handlers[cache_key]
            logger.debug(f"Reusing existing handler for {cache_key}")
        
        try:
            yield handler
        finally:
            # 这里可以添加清理逻辑
            pass


async def emit_error(sid: str, error_type: str, message: str, details: dict = None):
    """统一的错误事件发送"""
    error_data = {
        'type': error_type,
        'message': message,
        'timestamp': time(),
        'session_id': sid
    }
    
    if details and settings.environment == 'development':
        error_data['details'] = details
    
    await sio.emit('error', error_data, room=sid)
    logger.error(f"Socket error for {sid}", error_type=error_type, message=message, extra={'details': details})


@sio.event
async def connect(sid: str, environ: dict, auth: dict = None):
    """客户端连接事件 - 支持认证"""
    try:
        logger.info(f"Client connecting: {sid}")
        
        # 提取认证token
        token = None
        if auth and 'token' in auth:
            token = auth['token']
        elif environ.get('HTTP_AUTHORIZATION'):
            # 从header提取Bearer token
            auth_header = environ['HTTP_AUTHORIZATION']
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        user = None
        if token:
            try:
                async with get_db_session() as db:
                    user = await get_current_user_from_token(token, db)
                    logger.info(f"Authenticated user: {user.email}", extra={'user_id': str(user.id)})
            except Exception as e:
                logger.warning(f"Authentication failed for {sid}: {str(e)}")
                await emit_error(sid, SocketErrorType.AUTHENTICATION_REQUIRED, 
                               "认证失败，请重新登录", {'error': str(e)})
                return False
        else:
            logger.info(f"No token provided for {sid}, proceeding as guest")
        
        # 存储会话信息
        active_sessions[sid] = {
            'connected_at': time(),
            'user_id': str(user.id) if user else None,
            'user': user,
            'environ': environ,
            'authenticated': user is not None
        }
        
        # 发送连接确认
        await sio.emit('connection_established', {
            'status': 'connected',
            'session_id': sid,
            'authenticated': user is not None,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name
            } if user else None,
            'timestamp': time()
        }, room=sid)
        
        logger.info(f"Client connected successfully: {sid}, authenticated: {user is not None}")
        return True
        
    except Exception as e:
        logger.error(f"Connection error for {sid}: {str(e)}")
        return False


@sio.event
async def disconnect(sid: str):
    """客户端断开连接事件 - 增强版清理"""
    try:
        logger.info(f"Client disconnecting: {sid}")
        
        # 获取会话信息
        session_info = active_sessions.get(sid, {})
        user_id = session_info.get('user_id')
        
        # 清理会话信息
        if sid in active_sessions:
            session = active_sessions.pop(sid)
            duration = time() - session['connected_at']
            logger.info(f"Session ended for {sid}, duration: {duration:.2f}s")
        
        # 检查是否还有其他连接使用同一用户的Handler
        if user_id:
            user_has_other_connections = any(
                s.get('user_id') == user_id 
                for s in active_sessions.values()
            )
            
            # 如果用户没有其他活跃连接，清理Handler
            if not user_has_other_connections:
                keys_to_remove = [
                    key for key in conversation_handlers.keys() 
                    if key[0] == user_id
                ]
                for key in keys_to_remove:
                    handler = conversation_handlers.pop(key, None)
                    if handler:
                        logger.info(f"Cleaned up handler for {key}")
                
                # 清理对应的锁
                for key in keys_to_remove:
                    handler_locks.pop(key, None)
        
        logger.info(f"Client disconnected: {sid}")
        
    except Exception as e:
        logger.error(f"Disconnect error for {sid}: {str(e)}")


def cleanup_old_messages():
    """清理过期的消息ID"""
    current_time = time()
    expired_ids = [
        msg_id for msg_id, timestamp in processed_messages.items()
        if current_time - timestamp > MESSAGE_DEDUP_TTL
    ]
    for msg_id in expired_ids:
        processed_messages.pop(msg_id, None)


@sio.event
async def user_message(sid: str, data: dict):
    """完整的用户消息处理器 - 认证+缓存+错误处理+去重"""
    session_info = active_sessions.get(sid, {})
    user = session_info.get('user')
    user_id = session_info.get('user_id')
    
    # 认证检查
    if not user or not user_id:
        await emit_error(sid, SocketErrorType.AUTHENTICATION_REQUIRED, 
                        '请先登录后再发送消息')
        return
    
    try:
        logger.info(f"Received message from {sid}: {data}", extra={'user_id': user_id})
        
        message_content = data.get('content', '')
        session_id = data.get('session_id', 'default')
        message_id = data.get('message_id')
        
        if not message_content.strip():
            await emit_error(sid, SocketErrorType.VALIDATION_ERROR, 
                           '消息内容不能为空')
            return
        
        # 消息去重检查
        if message_id:
            current_time = time()
            if message_id in processed_messages:
                logger.warning(f"Duplicate message ignored: {message_id}", extra={'user_id': user_id})
                return
            
            # 记录消息ID
            processed_messages[message_id] = current_time
            
            # 清理过期消息（异步执行，不阻塞当前处理）
            if len(processed_messages) % 100 == 0:  # 每100条消息清理一次
                cleanup_old_messages()
        
        # 使用上下文管理器安全管理数据库和Handler
        async with get_db_session() as db:
            async with get_conversation_handler(user_id, session_id, db, user) as handler:
                # 流式响应处理
                async for chunk in handler.stream_response(message_content, session_id):
                    event_type = chunk.get('type', 'agent_response_chunk')
                    await sio.emit(event_type, chunk, room=sid)
                
                # 发送对话完成事件
                await sio.emit('conversation_complete', {
                    'session_id': session_id,
                    'timestamp': time()
                }, room=sid)
                
    except Exception as e:
        logger.error(f"Message handling error for {sid}: {str(e)}", 
                    extra={'user_id': user_id, 'session_id': data.get('session_id', 'default')})
        await emit_error(sid, SocketErrorType.PROCESSING_ERROR, 
                        '消息处理出错，请稍后重试', 
                        {'error': str(e)})


@sio.event
async def ping(sid: str, data: dict = None):
    """心跳检测事件"""
    try:
        await sio.emit('pong', {
            'timestamp': time(),
            'session_id': sid
        }, room=sid)
        
    except Exception as e:
        logger.error(f"Ping handler error for {sid}: {str(e)}")


def get_active_sessions_count() -> int:
    """获取活跃连接数"""
    return len(active_sessions)


def get_session_info(sid: str) -> Dict[str, Any]:
    """获取会话信息"""
    return active_sessions.get(sid, {})


def get_handler_stats() -> Dict[str, Any]:
    """获取Handler统计信息"""
    return {
        'active_handlers': len(conversation_handlers),
        'active_locks': len(handler_locks),
        'sessions': len(active_sessions)
    }


# 创建 ASGI 应用
socket_app = socketio.ASGIApp(sio)