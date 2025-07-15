"""
简化的Agent API路由 - LLM-Driven架构
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import uuid

from ..core.database import get_db
from ..api.auth import get_current_user
from ..models.user import User
from ..agents.email_processor import EmailProcessorAgent
from ..agents.conversation_handler import ConversationHandler
from ..core.logging import get_logger

router = APIRouter(prefix="/agents", tags=["AI Agents"])
logger = get_logger(__name__)

# Pydantic models
class AgentMessageRequest(BaseModel):
    message: str = Field(..., description="用户消息", example="帮我生成今天的邮件日报")
    session_id: Optional[str] = Field(default=None, description="会话ID（仅对话Agent需要）")

class AgentResponse(BaseModel):
    response: str = Field(..., description="Agent响应")
    session_id: Optional[str] = Field(None, description="会话ID")
    agent_type: str = Field(..., description="Agent类型")
    tool_calls: Optional[list] = Field(default=[], description="执行的工具调用")

@router.post("/email-processor", response_model=AgentResponse)
async def chat_with_email_processor(
    request: AgentMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """与EmailProcessor Agent对话"""
    try:
        # 创建EmailProcessor实例
        processor = EmailProcessorAgent(str(current_user.id), db)
        
        # 处理用户消息
        response = await processor.process(request.message)
        
        logger.info("EmailProcessor response generated", 
                   user_id=current_user.id,
                   message_length=len(request.message),
                   response_length=len(response))
        
        return AgentResponse(
            response=response,
            agent_type="email_processor",
            tool_calls=[]  # 这里可以后续添加工具调用跟踪
        )
        
    except Exception as e:
        logger.error("EmailProcessor failed", 
                    user_id=current_user.id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"EmailProcessor处理失败: {str(e)}"
        )

@router.post("/conversation", response_model=AgentResponse)
async def chat_with_conversation_handler(
    request: AgentMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """与ConversationHandler Agent对话"""
    try:
        # 创建或获取ConversationHandler实例
        session_id = request.session_id or f"session_{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        handler = ConversationHandler(
            str(current_user.id), 
            db, 
            session_id=session_id
        )
        
        # 处理用户消息
        response = await handler.process(request.message)
        
        logger.info("ConversationHandler response generated", 
                   user_id=current_user.id,
                   session_id=session_id,
                   message_length=len(request.message),
                   response_length=len(response))
        
        return AgentResponse(
            response=response,
            session_id=session_id,
            agent_type="conversation_handler",
            tool_calls=[]  # 这里可以后续添加工具调用跟踪
        )
        
    except Exception as e:
        logger.error("ConversationHandler failed", 
                    user_id=current_user.id, 
                    session_id=request.session_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ConversationHandler处理失败: {str(e)}"
        )

@router.get("/conversation/{session_id}/history")
async def get_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取对话历史"""
    try:
        handler = ConversationHandler(
            str(current_user.id), 
            db, 
            session_id=session_id
        )
        
        history = handler.get_history()
        
        return {
            "session_id": session_id,
            "history": history,
            "total_messages": len(history)
        }
        
    except Exception as e:
        logger.error("Get conversation history failed", 
                    user_id=current_user.id, 
                    session_id=session_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话历史失败: {str(e)}"
        )

@router.delete("/conversation/{session_id}")
async def clear_conversation_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清除对话历史"""
    try:
        handler = ConversationHandler(
            str(current_user.id), 
            db, 
            session_id=session_id
        )
        
        handler.clear_history()
        
        return {
            "message": "对话历史已清除",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error("Clear conversation history failed", 
                    user_id=current_user.id, 
                    session_id=session_id,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清除对话历史失败: {str(e)}"
        )

@router.get("/capabilities")
async def get_agent_capabilities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取Agent能力信息"""
    try:
        # 创建临时实例获取能力信息
        processor = EmailProcessorAgent(str(current_user.id), db)
        handler = ConversationHandler(str(current_user.id), db)
        
        return {
            "email_processor": {
                "capabilities": processor.get_capabilities(),
                "available_tools": processor.get_available_tools(),
                "context_info": processor.get_context_info()
            },
            "conversation_handler": {
                "capabilities": handler.get_capabilities(),
                "available_tools": handler.get_available_tools(),
                "context_info": handler.get_context_info()
            }
        }
        
    except Exception as e:
        logger.error("Get agent capabilities failed", 
                    user_id=current_user.id, 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Agent能力失败: {str(e)}"
        )

# 简单的健康检查端点
@router.get("/health")
async def agents_health_check():
    """Agent服务健康检查"""
    try:
        from ..agents.llm_provider import llm_provider_manager
        
        available_providers = llm_provider_manager.get_available_providers()
        
        return {
            "status": "healthy",
            "available_llm_providers": available_providers,
            "total_providers": len(available_providers)
        }
        
    except Exception as e:
        logger.error("Agent health check failed", error=str(e))
        return {
            "status": "unhealthy", 
            "error": str(e)
        }