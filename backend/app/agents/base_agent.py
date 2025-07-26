"""
LLM-Driven Agent基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool

from ..core.database import get_db
from ..core.config import settings
from ..core.logging import get_logger
from ..models.user import User
from .llm_provider import llm_provider_manager

logger = get_logger(__name__)

class BaseAgent(ABC):
    """LLM-Driven Agent基类"""
    
    def __init__(self, user_id: str, db_session: Session = None):
        self.user_id = user_id
        self.db = db_session or next(get_db())
        self.user = self._load_user()
        self.user_preferences = self._load_user_preferences()
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
    def _load_user(self) -> User:
        """加载用户信息"""
        user = self.db.query(User).filter(User.id == self.user_id).first()
        if not user:
            raise ValueError(f"User not found: {self.user_id}")
        return user
        
    def _load_user_preferences(self) -> Dict[str, Any]:
        """加载用户偏好"""
        try:
            # 直接从User模型获取preferences_text
            prefs_data = {
                "preferences_text": self.user.preferences_text or "",
                "schedule_preferences": {
                    "daily_report_time": self.user.daily_report_time.strftime("%H:%M") if self.user.daily_report_time else "09:00",
                    "timezone": self.user.timezone or "Asia/Shanghai"
                }
            }
            
            logger.info("User preferences loaded", 
                       user_id=self.user_id, 
                       has_preferences=bool(self.user.preferences_text))
                       
            return prefs_data
            
        except Exception as e:
            logger.error("Failed to load user preferences", user_id=self.user_id, error=str(e))
            return {
                "preferences_text": "",
                "schedule_preferences": {
                    "daily_report_time": "09:00",
                    "timezone": "Asia/Shanghai"
                }
            }
        
    def _create_llm(self):
        """创建LLM实例"""
        return llm_provider_manager.get_llm(
            provider=settings.llm.default_provider,
            model=self._get_default_model(),
            temperature=self._get_temperature()
        )
        
    def _create_agent(self):
        """创建LangChain Agent"""
        prompt = self._build_system_prompt()
        return create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
    def _build_system_prompt(self) -> ChatPromptTemplate:
        """构建LangChain系统prompt"""
        user_preferences_text = self._format_user_preferences()
        
        system_message = f"""你是用户 {self.user.email} 的专业邮件智能助手。

用户偏好信息：
{user_preferences_text}

请基于用户偏好，以自然、友好的方式与用户交流。根据用户请求智能选择和使用工具完成任务。
你的回复应该简洁明了，必要时主动询问澄清信息。

工具使用原则：
1. 根据用户意图自动选择合适的工具
2. 工具执行后，用自然语言总结结果
3. 遇到错误时，优雅地向用户解释并提供建议
4. 保持对话连贯性，记住之前的上下文"""
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
    def _format_user_preferences(self) -> str:
        """格式化用户偏好为自然语言"""
        if not self.user_preferences:
            return "暂无特定偏好设置"
            
        parts = []
        
        # 用户偏好文本
        preferences_text = self.user_preferences.get("preferences_text", "")
        if preferences_text:
            parts.append("用户偏好：")
            parts.append(preferences_text)
                
        # 调度偏好
        schedule_prefs = self.user_preferences.get("schedule_preferences", {})
        if schedule_prefs:
            parts.append("\n调度偏好：")
            if schedule_prefs.get("daily_report_time"):
                parts.append(f"  - 日报时间: {schedule_prefs['daily_report_time']}")
            if schedule_prefs.get("timezone"):
                parts.append(f"  - 时区: {schedule_prefs['timezone']}")
                
        return "\n".join(parts) if parts else "暂无特定偏好设置"
        
    async def process(self, message: str, **kwargs) -> str:
        """处理用户消息，返回Agent响应"""
        try:
            # 使用Agent处理消息
            response = await self.agent.ainvoke({
                "input": message,
                **kwargs
            })
            
            # 提取输出
            output = response.get("output", "")
            
            logger.info("Agent response generated", 
                       user_id=self.user_id,
                       message_length=len(message),
                       response_length=len(output))
                       
            return output
            
        except Exception as e:
            logger.error("Agent processing failed", 
                        user_id=self.user_id, 
                        error=str(e))
            # 返回友好的错误消息
            return f"抱歉，处理您的请求时出现了问题：{str(e)}。请稍后再试或换个方式表达。"
            
    def refresh_preferences(self):
        """刷新用户偏好（当偏好更新时调用）"""
        self.user_preferences = self._load_user_preferences()
        # 重新创建Agent以更新系统prompt
        self.agent = self._create_agent()
        logger.info("User preferences refreshed", user_id=self.user_id)
        
    def get_available_tools(self) -> List[str]:
        """获取可用工具列表"""
        return [tool.name for tool in self.tools]
        
    def get_context_info(self) -> Dict[str, Any]:
        """获取Agent上下文信息"""
        return {
            "user_id": self.user_id,
            "user_email": self.user.email,
            "has_preferences": bool(self.user_preferences.get("preferences_text")),
            "schedule_preferences": self.user_preferences.get("schedule_preferences", {}),
            "agent_type": self.__class__.__name__,
            "available_tools": self.get_available_tools()
        }
        
    @abstractmethod
    def _create_tools(self) -> List[Tool]:
        """创建Agent工具集"""
        pass
        
    @abstractmethod
    def _get_default_model(self) -> str:
        """获取默认模型"""
        pass
        
    @abstractmethod
    def _get_temperature(self) -> float:
        """获取温度参数"""
        pass


class StatefulAgent(BaseAgent):
    """有状态的Agent（带对话记忆）"""
    
    def __init__(self, user_id: str, db_session: Session = None, session_id: str = None):
        self.session_id = session_id or f"session_{user_id}_{datetime.now().timestamp()}"
        super().__init__(user_id, db_session)
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            input_key="input",
            output_key="output"
        )
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
        
    async def process(self, message: str, **kwargs) -> str:
        """处理用户消息，自动管理对话历史"""
        try:
            response = await self.executor.ainvoke({
                "input": message,
                **kwargs
            })
            
            output = response.get("output", "")
            
            logger.info("Stateful agent response generated", 
                       user_id=self.user_id,
                       session_id=self.session_id,
                       message_length=len(message),
                       response_length=len(output))
                       
            return output
            
        except Exception as e:
            logger.error("Stateful agent processing failed", 
                        user_id=self.user_id, 
                        session_id=self.session_id,
                        error=str(e))
            return f"抱歉，处理您的请求时出现了问题：{str(e)}。请稍后再试或换个方式表达。"
            
    def clear_history(self):
        """清除对话历史"""
        self.memory.clear()
        logger.info("Conversation history cleared", 
                   user_id=self.user_id, 
                   session_id=self.session_id)
                   
    def get_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            messages = self.memory.chat_memory.messages
            return [
                {
                    "type": "user" if hasattr(msg, 'content') and msg.type == "human" else "assistant",
                    "content": msg.content,
                    "timestamp": getattr(msg, 'timestamp', datetime.now().isoformat())
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error("Failed to get conversation history", 
                        user_id=self.user_id, 
                        session_id=self.session_id,
                        error=str(e))
            return []