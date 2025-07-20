"""
ConversationHandler Agent - 基于LangGraph的对话处理代理
"""
from typing import List, Dict, Any, Optional, Annotated, TypedDict, Sequence
from datetime import datetime, timezone
import uuid
from threading import Lock
import asyncio

from langchain.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages

from .base_agent import StatefulAgent
from .conversation_tools import create_conversation_tools
from ..core.config import settings
from ..core.logging import get_logger
from ..core.cache import CheckpointerCache
from ..core.errors import AppError, ErrorCategory, translate_error
from ..core.retry import with_retry, CONVERSATION_RETRY_POLICY
from ..models.conversation import ConversationMessage

logger = get_logger(__name__)

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str

class ConversationHandler(StatefulAgent):
    """对话处理Agent - 基于LangGraph，支持流式响应和工具调用可视化"""
    
    # 类级别缓存LLM实例，避免重复初始化
    # 使用 (provider, model, temperature) 作为缓存键
    _llm_cache = {}
    _cache_lock = Lock()  # 线程安全的缓存访问锁
    
    # 使用TTL缓存替代弱引用字典，解决竞态条件问题
    _checkpointer_cache = CheckpointerCache(max_size=1000, ttl_hours=24)
    
    def __init__(self, user_id: str, db_session, user=None):
        """初始化ConversationHandler"""
        super().__init__(user_id, db_session, user)
        
        # 创建LangGraph agent，使用更精确的缓存键
        cache_key = (
            settings.llm.default_provider,
            self._get_default_model(),
            self._get_temperature()
        )
        
        # 线程安全的缓存访问
        with self._cache_lock:
            if cache_key not in self._llm_cache:
                self._llm_cache[cache_key] = self.llm
            
        # 获取 checkpointer
        self.checkpointer = self._get_checkpointer()
        
        # 创建 agent，使用 prompt 参数（LangGraph 0.5.3 推荐）
        self.graph_agent = create_react_agent(
            model=self._llm_cache[cache_key],
            tools=self.tools,
            prompt=self._build_prompt,
            checkpointer=self.checkpointer
        )
    
    def _wrap_tool_with_error_handling(self, tool: Tool) -> Tool:
        """包装工具，添加统一的错误处理"""
        original_func = tool.func
        original_afunc = getattr(tool, 'afunc', None)
        
        def sync_wrapper(*args, **kwargs):
            try:
                return original_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool.name} failed", 
                           tool_name=tool.name,
                           error=str(e),
                           user_id=self.user_id)
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "success": False,
                    "message": self._get_user_friendly_error_message(e)
                }
        
        async def async_wrapper(*args, **kwargs):
            try:
                if original_afunc:
                    return await original_afunc(*args, **kwargs)
                else:
                    # 在异步上下文中运行同步函数
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, original_func, *args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool.name} failed (async)", 
                           tool_name=tool.name,
                           error=str(e),
                           user_id=self.user_id)
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "success": False,
                    "message": self._get_user_friendly_error_message(e)
                }
        
        # 创建新的工具实例，保留原有属性
        return Tool(
            name=tool.name,
            description=tool.description,
            func=sync_wrapper,
            afunc=async_wrapper,
            return_direct=tool.return_direct,
            args_schema=tool.args_schema
        )
    
    def _get_user_friendly_error_message(self, error: Exception) -> str:
        """将技术错误转换为用户友好的消息"""
        error_messages = {
            "ConnectionError": "连接服务失败，请稍后重试",
            "TimeoutError": "操作超时，请稍后重试",
            "ValueError": "输入参数有误，请检查后重试",
            "PermissionError": "权限不足，无法执行此操作"
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, f"操作失败: {str(error)}")
    
    def _create_tools(self) -> List[Tool]:
        """创建对话处理工具集，应用统一的错误处理"""
        user_context = {
            "user_id": self.user_id,
            "db_session": self.db,
            "user": self.user
        }
        
        # 获取原始工具列表
        raw_tools = create_conversation_tools(self.user_id, self.db, user_context)
        
        # 为每个工具应用错误处理包装
        wrapped_tools = []
        for tool in raw_tools:
            wrapped_tool = self._wrap_tool_with_error_handling(tool)
            wrapped_tools.append(wrapped_tool)
            logger.debug(f"Wrapped tool: {tool.name}", user_id=self.user_id)
        
        return wrapped_tools
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        return settings.agents.conversation_handler_default_model
    
    def _get_temperature(self) -> float:
        """获取温度参数"""
        return settings.agents.conversation_handler_temperature
    
    @with_retry(CONVERSATION_RETRY_POLICY)
    def _get_checkpointer(self):
        """根据策略获取 checkpointer - 默认使用 per_user 策略，带重试机制"""
        # 默认使用 per_user 策略，每个用户共享一个 checkpointer
        checkpointer_key = f"user_{self.user_id}"
        
        # 使用新的TTL缓存，自动处理线程安全和过期清理
        return self._checkpointer_cache.get_or_create(
            checkpointer_key,
            lambda: InMemorySaver()
        )
    
    def _build_prompt(self, state: Dict, config: Dict) -> List[BaseMessage]:
        """构建包含系统提示的消息列表"""
        system_prompt = self._build_system_prompt_for_graph()
        messages = state.get("messages", [])
        
        # 应用消息裁剪（如果启用）
        if settings.agents.message_pruning_enabled:
            messages = self._prune_messages(messages)
        
        return [SystemMessage(content=system_prompt)] + messages
    
    def _prune_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """裁剪消息以防止超过限制"""
        if settings.agents.pruning_strategy == "count":
            return self._prune_by_count(messages)
        elif settings.agents.pruning_strategy == "tokens":
            return self._prune_by_tokens(messages)
        else:
            return messages
    
    def _prune_by_count(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """基于消息数量的裁剪"""
        max_count = settings.agents.max_messages_count
        
        if len(messages) <= max_count:
            return messages
        
        # 保留最近的 N 条消息
        return messages[-max_count:]
    
    def _prune_by_tokens(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """基于 token 数量的智能裁剪"""
        max_tokens = settings.agents.max_tokens_count
        
        # 简化版实现：基于字符数估算 (约4个字符 = 1个token)
        # 生产环境建议使用 tiktoken 进行精确计算
        total_chars = 0
        result = []
        
        # 从后往前遍历，保留最新的消息
        for msg in reversed(messages):
            msg_chars = len(msg.content)
            estimated_tokens = msg_chars // 4
            
            if total_chars + msg_chars > max_tokens * 4:
                break
            
            result.insert(0, msg)
            total_chars += msg_chars
        
        return result
    
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
            # 构建输入状态（无需手动加载历史，checkpointer会自动管理）
            input_state = {
                "messages": [HumanMessage(content=message)],
                "user_id": self.user_id,
                "session_id": session_id
            }
            
            # 保存用户消息到数据库（用于前端展示）
            user_msg = ConversationMessage(
                user_id=self.user_id,
                session_id=session_id,
                role="user",
                content=message,
                message_type="user_message"
            )
            self.db.add(user_msg)
            self.db.commit()
            
            # 使用新的 astream API
            response_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": f"{self.user_id}_{session_id}"}}
            
            async for chunk in self.graph_agent.astream(
                input_state,
                config=config,
                stream_mode="updates"
            ):
                # 处理消息更新
                if "agent" in chunk:
                    for msg in chunk["agent"].get("messages", []):
                        if isinstance(msg, AIMessage) and msg.content:
                            yield {
                                "type": "agent_response_chunk",
                                "content": msg.content,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": response_id
                            }
                            
                            # 保存 AI 响应到数据库
                            ai_msg = ConversationMessage(
                                user_id=self.user_id,
                                session_id=session_id,
                                role="assistant",
                                content=msg.content,
                                message_type="ai_response"
                            )
                            self.db.add(ai_msg)
                            self.db.commit()
                
                # 处理工具调用 - 适配新的 patch 结构
                if "tool" in chunk:
                    tool_data = chunk["tool"]
                    # 工具开始事件
                    if "name" in tool_data and "args" in tool_data:
                        yield {
                            "type": "tool_call_start",
                            "tool_name": tool_data.get("name"),
                            "tool_args": tool_data.get("args"),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "id": str(uuid.uuid4())
                        }
                    # 工具结果事件
                    if "output" in tool_data:
                        output = tool_data.get("output")
                        # 检查是否是错误响应
                        if isinstance(output, dict) and "error" in output:
                            yield {
                                "type": "tool_error",
                                "tool_name": tool_data.get("name"),
                                "error": output["error"],
                                "error_type": output.get("error_type", "Unknown"),
                                "message": output.get("message", "工具执行失败"),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": str(uuid.uuid4())
                            }
                        else:
                            yield {
                                "type": "tool_call_result",
                                "tool_result": output,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": str(uuid.uuid4())
                            }
                
                # 保留原有的 tools chunk 处理作为后备
                elif "tools" in chunk:
                    for tool_call in chunk["tools"].get("messages", []):
                        if hasattr(tool_call, 'name') and hasattr(tool_call, 'args'):
                            yield {
                                "type": "tool_call_start",
                                "tool_name": tool_call.name,
                                "tool_args": tool_call.args,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": str(uuid.uuid4())
                            }
                        elif hasattr(tool_call, 'content'):
                            content = tool_call.content
                            # 检查是否是错误响应
                            if isinstance(content, dict) and "error" in content:
                                yield {
                                    "type": "tool_error",
                                    "tool_name": getattr(tool_call, 'name', 'unknown'),
                                    "error": content["error"],
                                    "error_type": content.get("error_type", "Unknown"),
                                    "message": content.get("message", "工具执行失败"),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "id": str(uuid.uuid4())
                                }
                            else:
                                yield {
                                    "type": "tool_call_result",
                                    "tool_result": content,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "id": str(uuid.uuid4())
                                }
                
        except Exception as e:
            # 转换为用户友好的错误
            if isinstance(e, AppError):
                app_error = e
            else:
                app_error = translate_error(e)
            
            logger.error("Stream response failed", 
                        user_id=self.user_id,
                        session_id=session_id,
                        error=str(e),
                        error_category=app_error.category.value)
            
            # 返回用户友好的错误信息
            error_response = app_error.to_dict()
            error_response['timestamp'] = datetime.now(timezone.utc).isoformat()
            yield error_response
    
    
    @classmethod
    def clear_llm_cache(cls):
        """清理 LLM 缓存（用于测试或内存管理）"""
        with cls._cache_lock:
            cls._llm_cache.clear()
            logger.info("LLM cache cleared")
    
    @classmethod
    def clear_checkpointer_cache(cls):
        """清理 checkpointer 缓存"""
        cls._checkpointer_cache.clear()
        logger.info("Checkpointer cache cleared")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with cls._cache_lock:
            llm_stats = {
                "size": len(cls._llm_cache),
                "keys": list(cls._llm_cache.keys()),
                "memory_usage_estimate": f"{len(cls._llm_cache) * 100}MB"  # 粗略估计
            }
        
        # 获取 checkpointer 缓存统计（TTL缓存自带统计方法）
        checkpointer_stats = cls._checkpointer_cache.get_stats()
        
        return {
            "llm_cache": llm_stats,
            "checkpointer_cache": checkpointer_stats
        }
    
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