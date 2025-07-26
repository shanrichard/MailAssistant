"""
ConversationHandler Agent - 基于LangGraph的对话处理代理
"""
from typing import List, Dict, Any, Optional, Annotated, TypedDict, Sequence
from datetime import datetime, timezone
import uuid
import json
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
from ..utils.chunk_accumulator import ChunkAccumulator

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

## 重要：输出格式要求

**你必须使用 Markdown 格式来组织所有回答**，这样可以让信息更清晰、更易读。请遵循以下格式化原则：

- 使用 **粗体** 标记重要信息和关键词
- 使用标题（## 或 ###）来组织内容结构
- 使用列表（- 或 1. 2. 3.）展示多个项目
- 使用 `行内代码` 标记邮件地址、时间等具体信息
- 使用引用（>）来突出重要提示或总结
- 使用表格展示对比信息（如有需要）
- 使用分隔线（---）区分不同部分

### Markdown 示例：
```
## 📧 邮件搜索结果

找到 **3 封** 符合条件的邮件：

### 重要邮件
1. **张三** - `2024-01-20 14:30`
   > 关于项目进度的重要更新

2. **李四** - `2024-01-20 10:15`  
   > 会议安排确认

### 普通邮件
- 系统通知 - `2024-01-20 09:00`

---
💡 **建议**：您有 2 封重要邮件需要及时处理。
```

邮件搜索指导原则：

1. 时间相关查询：
   - "最近"、"这几天" → 使用 days_back=3
   - "今天" → 使用 days_back=1
   - "本周"、"这周" → 使用 days_back=7
   - "上周" → 使用 days_back=14
   - "本月"、"这个月" → 使用 days_back=30

2. 发件人相关查询：
   重要：数据库中 sender 字段存储的是完整格式，例如：
   - "Google <no-reply@accounts.google.com>"
   - "张三 <zhangsan@example.com>"
   - "Microsoft 帐户团队 <account-security-noreply@accountprotection.microsoft.com>"
   - "support@alphavantage.co"（有些只有邮箱地址）
   
   使用 sender 参数的示例：
   - "张三发的邮件" → 使用 sender="张三"
   - "google的邮件" → 使用 sender="google"（会匹配 "Google <...>"、"googlecloud@google.com" 等）
   - "微软的邮件" → 使用 sender="微软" 或 sender="microsoft"
   - "@gmail.com的邮件" → 使用 sender="gmail.com"
   - "最近有什么人给我发邮件" → 仅使用 days_back，不设置 sender，查看 sender_summary

   sender 参数特性：
   - 部分匹配：输入的文本会在整个 sender 字段中搜索
   - 大小写不敏感：google 能匹配 Google，microsoft 能匹配 Microsoft
   - 可以搜索：姓名（张三）、公司名（Google）、邮箱地址（gmail.com）、邮箱用户名（no-reply）

3. 状态相关查询：
   - "未读邮件" → 使用 is_read=False
   - "已读邮件" → 使用 is_read=True
   - "有附件的邮件" → 使用 has_attachments=True

5. 组合查询示例：
   - "张三最近发的重要邮件" → sender="张三", days_back=3，然后根据用户偏好分析结果
   - "本周的未读邮件" → days_back=7, is_read=False
   - "最近有什么人给我发邮件" → days_back=3, 不设置其他参数，查看sender_summary统计

搜索无结果时的处理：
当邮件搜索返回0条结果时，请：
1. 告知用户没有找到符合条件的邮件
2. 重要：查看返回数据中的 sender_summary 字段，它包含最近邮件的发件人统计
3. 向用户展示 sender_summary 中的前几个发件人，让用户了解实际的发件人格式
4. 建议用户：
   - 如果搜索 "Microsoft"，可以试试 "微软" 或 "microsoft"
   - 如果搜索公司名没结果，可以试试域名如 "microsoft.com"
   - 查看 sender_summary 中的发件人，选择正确的关键词重试
   - 使用 query 参数进行全文搜索

交互原则：
- 以友好、专业的方式与用户交流
- 主动理解用户的隐含需求
- 提供个性化的建议和解决方案
- 及时反馈任务执行状态
- 学习用户习惯并优化服务体验
- 在不确定时主动询问澄清

可用工具说明：
- search_email_history: 搜索历史邮件
  重要：必须使用关键字参数调用，例如：
  search_email_history(days_back=3, sender="google")
  search_email_history(query="会议", is_read=False)
  不要使用位置参数如 search_email_history(3, "google")
- read_daily_report: 读取邮件日报
- bulk_mark_read: 批量标记邮件为已读
- update_user_preferences: 更新用户偏好
- trigger_email_processor: 触发邮件处理任务
- get_task_status: 查询任务执行状态

常见用户需求处理：
- "帮我分析今天的邮件" → 使用 trigger_email_processor(action="generate_daily_report")
- "把广告邮件都标记为已读" → 使用 bulk_mark_read(criteria="广告邮件")
- "我觉得XX类邮件很重要" → 使用 update_user_preferences(preference_description="XX类邮件很重要")
- "帮我找google的邮件" → 使用 search_email_history(sender="google")
- "最近3天的邮件" → 使用 search_email_history(days_back=3)
- "最近3天google的邮件" → 使用 search_email_history(days_back=3, sender="google")
- "现在的任务进展如何" → 使用 get_task_status(task_type="all")

请根据用户的自然语言请求，智能选择合适的工具组合来完成任务。记住要保持对话的连贯性和上下文感知，并始终使用 Markdown 格式输出。"""
    
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
            
            # 使用新的 astream API（切换到messages模式以获取tool_call_chunks）
            response_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": f"{self.user_id}_{session_id}"}}
            
            # 初始化工具调用状态跟踪
            if not hasattr(self, '_active_tool_calls'):
                self._active_tool_calls = {}
            
            # 初始化 chunk 累积器
            accumulator = ChunkAccumulator(
                min_chunk_size=settings.chunk_min_size,
                max_wait_time=settings.chunk_max_wait,
                delimiter_pattern=settings.chunk_delimiter_pattern
            )
            accumulated_content = ""  # 用于数据库写入
            
            async for chunk, metadata in self.graph_agent.astream(
                input_state,
                config=config,
                stream_mode="messages"  # 切换到messages模式以获取tool_call_chunks
            ):
                # 🎯 处理tool_call_chunks（LangGraph工具调用流）
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tool_chunk in chunk.tool_call_chunks:
                        async for event in self._handle_tool_call_chunk(tool_chunk):
                            yield event
                
                # 处理AI响应内容
                if hasattr(chunk, 'content') and chunk.content:
                    # 🔍 检查是否是工具执行结果
                    tool_result_event = self._extract_tool_result_from_content(chunk.content)
                    if tool_result_event:
                        # 这是工具执行结果，发送工具结果事件而不是普通响应
                        yield tool_result_event
                    else:
                        # 使用累积器处理普通AI响应内容
                        emit_content = accumulator.add(chunk.content)
                        accumulated_content += chunk.content
                        
                        if emit_content:
                            yield {
                                "type": "agent_response_chunk",
                                "content": emit_content,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": response_id
                            }
                
                # 🗑️ 移除所有基于错误假设的工具调用处理代码
                # 现在使用正确的tool_call_chunks处理机制
            
            # 发送剩余内容
            final_content = accumulator.flush()
            if final_content:
                yield {
                    "type": "agent_response_chunk",
                    "content": final_content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "id": response_id
                }
            
            # 一次性写入完整消息到数据库
            if accumulated_content:
                ai_msg = ConversationMessage(
                    user_id=self.user_id,
                    session_id=session_id,
                    role="assistant",
                    content=accumulated_content,
                    message_type="ai_response"
                )
                self.db.add(ai_msg)
                self.db.commit()
            
            # 发送完成信号
            yield {
                "type": "conversation_complete",
                "timestamp": datetime.now(timezone.utc).isoformat()
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
    
    async def _handle_tool_call_chunk(self, tool_chunk):
        """处理单个工具调用chunk - 基于真实的LangGraph结构"""
        
        # 🎯 第一个chunk：包含完整工具信息 (name, id, type)
        if tool_chunk.get('name') and tool_chunk.get('id'):
            tool_id = tool_chunk['id']
            tool_name = tool_chunk['name']
            
            # 初始化工具调用状态
            self._active_tool_calls[tool_id] = {
                'name': tool_name,
                'args_fragments': [tool_chunk.get('args', '')],  # 开始收集参数片段
                'status': 'building_args',
                'start_time': datetime.now(timezone.utc)
            }
            
            logger.debug(f"Tool call started: {tool_name} (ID: {tool_id})", 
                        user_id=self.user_id, tool_name=tool_name, tool_id=tool_id)
            
            # 🚀 发送工具调用开始事件
            yield {
                "type": "tool_call_start",
                "tool_name": tool_name,
                "tool_args": None,  # 参数还在构建中
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "id": tool_id
            }
        
        # 🎯 后续chunks：累积参数片段 (只有args字段，name和id为None)
        elif tool_chunk.get('args') is not None:
            # 找到对应的活跃工具调用（最近的正在构建参数的调用）
            active_call = None
            for call_id, call_data in self._active_tool_calls.items():
                if call_data['status'] == 'building_args':
                    active_call = (call_id, call_data)
                    break
            
            if active_call:
                call_id, call_data = active_call
                call_data['args_fragments'].append(tool_chunk['args'])
                
                # 🔧 尝试解析完整参数
                full_args_str = ''.join(call_data['args_fragments'])
                try:
                    args_dict = json.loads(full_args_str)
                    # 参数构建完成
                    call_data['status'] = 'args_complete'
                    call_data['args'] = args_dict
                    
                    logger.debug(f"Tool call args complete: {call_data['name']}", 
                                user_id=self.user_id, tool_args=args_dict, tool_id=call_id)
                    
                    # 🎯 发送参数完整事件
                    yield {
                        "type": "tool_call_args_complete",
                        "tool_name": call_data['name'],
                        "tool_args": args_dict,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "id": call_id
                    }
                except json.JSONDecodeError:
                    # 参数还在构建中，继续等待
                    logger.debug(f"Tool call args building: {len(full_args_str)} chars", 
                                user_id=self.user_id, args_preview=full_args_str[:100])
                    pass
            else:
                # 没有找到对应的活跃工具调用，记录警告
                logger.warning("Received tool args chunk but no active tool call found", 
                              user_id=self.user_id, chunk_args=tool_chunk.get('args', '')[:50])

    def _extract_tool_result_from_content(self, content):
        """从AI响应内容中提取工具执行结果"""
        try:
            # 🔍 检查是否是JSON格式的工具结果
            if content.strip().startswith('{"status"'):
                # 尝试解析工具结果JSON
                tool_result = json.loads(content.strip())
                
                # 找到对应的活跃工具调用
                for call_id, call_data in list(self._active_tool_calls.items()):
                    if call_data['status'] in ['building_args', 'args_complete']:
                        # 找到匹配的工具调用，生成结果事件
                        call_data['status'] = 'completed'
                        call_data['result'] = tool_result
                        
                        # 🎯 发送工具执行结果事件
                        result_event = {
                            "type": "tool_call_result",
                            "tool_name": call_data['name'],
                            "tool_result": tool_result,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "id": call_id
                        }
                        
                        # 清理已完成的工具调用
                        del self._active_tool_calls[call_id]
                        
                        logger.debug(f"Tool call completed: {call_data['name']}", 
                                    user_id=self.user_id, tool_id=call_id, 
                                    result_size=len(str(tool_result)))
                        
                        return result_event
                        
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            # 不是工具结果，返回None继续作为普通内容处理
            logger.debug(f"Content is not tool result: {str(e)}", 
                        user_id=self.user_id, content_preview=content[:50])
            pass
        
        return None
    
    
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
            import asyncio
            # 正确调用基类的异步方法
            return asyncio.run(super().process(message))
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