"""
邮件处理工具 - 使用LangChain @tool装饰器
"""
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, date, timedelta
from functools import wraps
import time
from langchain.tools import tool

from ..core.logging import get_logger
from ..services.email_sync_service import email_sync_service

logger = get_logger(__name__)

def safe_tool_wrapper(tool_func: Callable) -> Callable:
    """统一的tool异常包装器"""
    # 将tool_name移到正确的作用域
    tool_name = tool_func.__name__
    
    @wraps(tool_func)
    def wrapper(*args, **kwargs) -> str:
        start_time = time.time()
        try:
            result = tool_func(*args, **kwargs)
            # 确保结果是字符串
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            
            # 记录执行时间
            execution_time = time.time() - start_time
            logger.info(f"Tool {tool_name} executed successfully", 
                       execution_time_ms=int(execution_time * 1000))
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Tool {tool_name} JSON error", exc_info=True)
            return json.dumps({
                "status": "error",
                "tool": tool_name,
                "error_type": "json_decode_error",
                "message": f"JSON解析错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed", exc_info=True)
            return json.dumps({
                "status": "error",
                "tool": tool_name,
                "error_type": type(e).__name__,
                "message": f"工具执行失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
    
    # 保留tool的元数据 - 现在tool_name在正确的作用域中
    wrapper.name = tool_name
    wrapper.description = getattr(tool_func, 'description', '')
    
    return wrapper

def create_email_tools(user_id: str, db_session, user_context: Dict[str, Any]):
    """创建邮件处理工具集"""
    import uuid
    # 确保 user_id 是 UUID 对象
    if isinstance(user_id, str):
        user_id_uuid = uuid.UUID(user_id)
    else:
        user_id_uuid = user_id
    
    @tool
    @safe_tool_wrapper
    def sync_emails(days: int = 1) -> str:
        """同步Gmail邮件到本地数据库。
        
        Args:
            days: 同步最近多少天的邮件，默认1天
            
        Returns:
            同步结果的JSON字符串，包含新邮件数量等信息
        """
        sync_stats = email_sync_service.sync_user_emails(
            db_session, 
            user_id, 
            days=days,
            max_messages=100
        )
        
        result = {
            "status": "success",
            "new_emails": sync_stats.get("new_emails", 0),
            "updated_emails": sync_stats.get("updated_emails", 0),
            "total_processed": sync_stats.get("total_processed", 0),
            "sync_time": datetime.now().isoformat()
        }
        
        logger.info("Email sync completed", 
                   user_id=user_id, 
                   new_emails=result["new_emails"])
        
        return json.dumps(result, ensure_ascii=False)
    
    return [sync_emails]