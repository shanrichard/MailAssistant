"""
ConversationHandler Agent - 基于LangGraph的对话处理代理
"""
from typing import List, Dict, Any, Optional, Annotated, TypedDict
from datetime import datetime, timezone
import uuid
import json
from operator import add
import asyncio

from langchain.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
# from langgraph.prebuilt import create_react_agent
# from langgraph.graph import StateGraph, END

from .base_agent import StatefulAgent
from .conversation_tools import create_conversation_tools
from ..core.config import settings
from ..core.logging import get_logger
from ..models.conversation import ConversationMessage

logger = get_logger(__name__)

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[list, add]
    user_id: str
    session_id: str

class ConversationHandler(StatefulAgent):
    """对话处理Agent - 基于LangGraph，支持流式响应和工具调用可视化"""
    
    # 类级别缓存LLM实例，避免重复初始化
    _llm_cache = {}
    
    def __init__(self, user_id: str, db_session, user=None):
        """初始化ConversationHandler"""
        super().__init__(user_id, db_session, user)
        
        # 创建LangGraph agent - 暂时注释以避免版本兼容性问题
        if not self._llm_cache.get('llm'):
            self._llm_cache['llm'] = self.llm
            
        # TODO: 修复LangGraph版本兼容性后启用
        # self.graph_agent = create_react_agent(
        #     model=self._llm_cache['llm'],
        #     tools=self.tools,
        #     state_modifier=self._build_system_prompt_for_graph()
        # )
        self.graph_agent = None
    
    def _create_tools(self) -> List[Tool]:
        """创建对话处理工具集"""
        user_context = {
            "user_id": self.user_id,
            "db_session": self.db,
            "user": self.user
        }
        
        return create_conversation_tools(self.user_id, self.db, user_context)
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        return settings.agents.conversation_handler_default_model
    
    def _get_temperature(self) -> float:
        """获取温度参数"""
        return settings.agents.conversation_handler_temperature
    
    def _build_system_prompt_for_graph(self) -> str:
        """构建LangGraph使用的系统prompt"""
        return """你是用户的贴心邮件管家，负责理解用户需求并协调各种邮件管理任务。你的专业领域包括：

1. 自然语言理解和意图识别
2. 任务调度和工作流管理
3. 用户偏好学习和更新
4. 邮件搜索和历史查询
5. 批量操作和智能建议
6. 实时状态反馈和进度跟踪

交互原则：
- 以友好、专业的方式与用户交流
- 主动理解用户的隐含需求
- 提供个性化的建议和解决方案
- 及时反馈任务执行状态
- 学习用户习惯并优化服务体验
- 在不确定时主动询问澄清

可用工具说明：
- search_email_history: 搜索历史邮件
- read_daily_report: 读取邮件日报
- bulk_mark_read: 批量标记邮件为已读
- update_user_preferences: 更新用户偏好
- trigger_email_processor: 触发邮件处理任务
- get_task_status: 查询任务执行状态

常见用户需求处理：
- "帮我分析今天的邮件" → 触发日报生成并呈现结果
- "把广告邮件都标记为已读" → 使用批量操作工具
- "我觉得XX类邮件很重要" → 更新用户偏好设置
- "帮我找XX相关的邮件" → 搜索邮件历史
- "现在的任务进展如何" → 查询任务状态

请根据用户的自然语言请求，智能选择合适的工具组合来完成任务。记住要保持对话的连贯性和上下文感知。"""
    
    async def stream_response(self, message: str, session_id: str):
        """流式传输响应，包含工具调用信息"""
        try:
            # 加载历史对话上下文（限制最近20条）
            history_messages = await self._load_conversation_history(session_id, limit=20)
            
            # 构建输入状态
            input_state = {
                "messages": history_messages + [HumanMessage(content=message)],
                "user_id": self.user_id,
                "session_id": session_id
            }
            
            # 配置流式传输选项
            config = {
                "configurable": {"thread_id": f"{self.user_id}_{session_id}"},  # 避免用户间串话
                "stream_mode": "values",  # 获取完整状态更新
                "include_names": ["agent", "tools"]  # 包含工具调用
            }
            
            # 保存用户消息
            user_msg = ConversationMessage(
                user_id=self.user_id,
                session_id=session_id,
                role="user",
                content=message,
                message_type="user_message"
            )
            self.db.add(user_msg)
            self.db.commit()
            
            # 流式传输事件 - 暂时使用简单实现
            # TODO: 修复LangGraph版本兼容性后启用
            # async for event in self.graph_agent.astream_events(
            #     input_state, 
            #     config=config,
            #     version="v2"
            # ):
            #     yield self._format_stream_event(event)
            
            # 临时实现：使用普通响应模拟流式
            response = self.process(message)
            
            # 模拟流式响应
            words = response.split()
            chunk_size = 3
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i+chunk_size])
                yield {
                    "type": "agent_response_chunk",
                    "content": chunk + ' ',
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "id": str(uuid.uuid4())
                }
                await asyncio.sleep(0.1)  # 模拟延迟
            
            # 发送结束信号
            yield {
                "type": "stream_end",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
                
        except Exception as e:
            logger.error("Stream response failed", 
                        user_id=self.user_id,
                        session_id=session_id,
                        error=str(e))
            yield {
                "type": "agent_error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _load_conversation_history(self, session_id: str, limit: int = 20) -> List:
        """加载历史对话，限制条数避免token超限"""
        messages = self.db.query(ConversationMessage).filter(
            ConversationMessage.user_id == self.user_id,
            ConversationMessage.session_id == session_id
        ).order_by(ConversationMessage.created_at.desc()).limit(limit).all()
        
        # 转换为LangChain消息格式
        history = []
        for msg in reversed(messages):  # 倒序以保持时间顺序
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(AIMessage(content=msg.content))
                
        return history
    
    def _format_stream_event(self, event) -> Dict[str, Any]:
        """格式化流式事件为前端可用格式"""
        timestamp = datetime.now(timezone.utc).isoformat()
        # 生成稳定的消息ID，而不依赖run_id
        message_id = str(uuid.uuid4())
        
        if event["event"] == "on_chat_model_stream":
            # LLM token流
            return {
                "type": "agent_response_chunk",
                "content": event["data"]["chunk"].content,
                "timestamp": timestamp,
                "id": message_id
            }
        elif event["event"] == "on_tool_start":
            # 工具调用开始
            return {
                "type": "tool_call_start",
                "tool_name": event["name"],
                "tool_args": event["data"].get("input", {}),
                "timestamp": timestamp,
                "id": message_id
            }
        elif event["event"] == "on_tool_end":
            # 工具调用结束
            return {
                "type": "tool_call_result",
                "tool_name": event["name"],
                "tool_result": event["data"].get("output", ""),
                "timestamp": timestamp,
                "id": message_id
            }
        elif event["event"] == "on_tool_error":
            # 工具调用错误
            return {
                "type": "tool_call_error",
                "tool_name": event["name"],
                "error": str(event["data"]),
                "timestamp": timestamp,
                "id": message_id
            }
        elif event["event"] == "on_chain_error":
            # 链执行错误
            return {
                "type": "agent_error",
                "error": str(event["data"]),
                "timestamp": timestamp
            }
        
        # 其他事件暂时忽略
        return None
    
    def process(self, message: str) -> str:
        """同步处理消息（保持向后兼容）"""
        try:
            # 使用基类的process方法
            return super().process(message)
        except Exception as e:
            logger.error("Process message failed", 
                        user_id=self.user_id,
                        error=str(e))
            return f"处理失败：{str(e)}"
    
    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [
            "natural_language_understanding",  # 自然语言理解
            "task_orchestration",             # 任务编排
            "preference_management",          # 偏好管理
            "email_search",                   # 邮件搜索
            "bulk_operations",                # 批量操作
            "status_tracking",                # 状态跟踪
            "conversation_management",        # 对话管理
            "intelligent_suggestions",       # 智能建议
            "workflow_automation",            # 工作流自动化
            "context_awareness",              # 上下文感知
            "streaming_response",             # 流式响应
            "tool_visualization"              # 工具可视化
        ]