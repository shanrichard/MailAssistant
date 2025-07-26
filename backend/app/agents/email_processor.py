"""
EmailProcessor Agent - 基于LangGraph的邮件处理代理
"""
from typing import List, Dict, Any, TypedDict, Sequence, Annotated
import threading
from dataclasses import dataclass
from langchain.tools import Tool
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from .base_agent import BaseAgent
from .email_tools import create_email_tools
from .conversation_tools import create_conversation_tools
from ..core.config import settings
from ..core.logging import get_logger
from .llm_provider import llm_provider_manager
from ..config.agent_prompts import EMAIL_PROCESSOR_SYSTEM_PROMPT

logger = get_logger(__name__)

class EmailProcessorState(TypedDict):
    """EmailProcessor状态定义"""
    messages: Annotated[Sequence[BaseMessage], add_messages]

@dataclass
class AgentCapability:
    """Agent能力描述"""
    name: str
    display_name: str
    description: str
    icon: str
    category: str
    enabled: bool = True

class EmailProcessorAgent(BaseAgent):
    """邮件处理Agent - 基于LangGraph的无状态实现"""
    
    # 类级别 LLM 缓存
    _llm_cache = {}
    _cache_lock = threading.Lock()
    
    def __init__(self, user_id: str, db_session):
        """初始化EmailProcessorAgent"""
        # 调用父类初始化来加载user等基础数据
        super().__init__(user_id, db_session)
        
        # 创建LangGraph agent（无checkpointer，因为是无状态的）
        self.graph_agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self._build_prompt_for_langgraph
        )
    
    def _create_llm(self):
        """创建或获取缓存的LLM实例"""
        cache_key = (
            settings.llm.default_provider,
            self._get_default_model(),
            self._get_temperature()
        )
        
        with self._cache_lock:
            if cache_key not in self._llm_cache:
                self._llm_cache[cache_key] = llm_provider_manager.get_llm(
                    provider=cache_key[0],
                    model=cache_key[1],
                    temperature=cache_key[2]
                )
                logger.info(f"Created new LLM instance for cache key: {cache_key}")
            
            return self._llm_cache[cache_key]
    
    @classmethod
    def clear_llm_cache(cls):
        """清理LLM缓存"""
        with cls._cache_lock:
            cls._llm_cache.clear()
            logger.info("EmailProcessorAgent LLM cache cleared")
    
    def _create_tools(self) -> List[Tool]:
        """创建邮件处理工具集"""
        user_context = {
            "user_id": self.user_id,
            "db_session": self.db,
            "user": self.user
        }
        
        # 获取邮件工具
        email_tools = create_email_tools(self.user_id, self.db, user_context)
        
        # 获取对话工具
        conversation_tools = create_conversation_tools(self.user_id, self.db, user_context)
        
        # 只选择EmailProcessor需要的工具
        needed_tools = []
        
        # 从email_tools添加sync_emails
        needed_tools.extend(email_tools)
        
        # 从conversation_tools添加必要的工具
        for tool in conversation_tools:
            if tool.name in ["get_user_preferences", "search_email_history"]:
                needed_tools.append(tool)
        
        return needed_tools
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        return settings.agents.email_processor_default_model
    
    def _get_temperature(self) -> float:
        """获取温度参数"""
        return settings.agents.email_processor_temperature
    
    def _build_prompt_for_langgraph(self, state: Dict, config: Dict) -> List[BaseMessage]:
        """构建LangGraph使用的prompt消息列表"""
        system_prompt = self._build_system_prompt_content()
        messages = state.get("messages", [])
        return [SystemMessage(content=system_prompt)] + messages
    
    def _build_system_prompt_content(self) -> str:
        """构建系统prompt内容 - 返回字符串"""
        # 获取基础系统prompt
        user_preferences_text = self._format_user_preferences()
        
        base_system = f"""你是用户 {self.user.email} 的专业邮件智能助手。

用户偏好信息：
{user_preferences_text}

请基于用户偏好，以自然、友好的方式与用户交流。根据用户请求智能选择和使用工具完成任务。
你的回复应该简洁明了，必要时主动询问澄清信息。

工具使用原则：
1. 根据用户意图自动选择合适的工具
2. 工具执行后，用自然语言总结结果
3. 遇到错误时，优雅地向用户解释并提供建议
4. 保持对话连贯性，记住之前的上下文"""
        
        # 添加EmailProcessor特定指令
        email_processor_instructions = EMAIL_PROCESSOR_SYSTEM_PROMPT
        
        return f"{base_system}\n\n{email_processor_instructions}"
    
    def _build_system_prompt(self):
        """保留这个方法以兼容BaseAgent，但不会被LangGraph使用"""
        # 这个方法被BaseAgent的__init__调用，但我们在EmailProcessor中不使用它
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        return ChatPromptTemplate.from_messages([
            ("system", "placeholder"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
    
    async def process(self, message: str) -> str:
        """处理消息 - 使用LangGraph"""
        try:
            input_state = {
                "messages": [HumanMessage(content=message)]
            }
            
            # 无状态调用，不需要thread_id
            result = await self.graph_agent.ainvoke(input_state)
            
            # 提取最后一条AI消息
            if result.get("messages"):
                final_message = result["messages"][-1]
                return final_message.content
            else:
                return "抱歉，处理您的请求时出现了问题。"
                
        except Exception as e:
            logger.error("Agent processing failed", 
                        user_id=self.user_id, 
                        error=str(e))
            return f"抱歉，处理您的请求时出现了问题：{str(e)}。请稍后再试或换个方式表达。"
    
    def get_capabilities(self) -> List[AgentCapability]:
        """获取结构化的Agent能力列表"""
        return [
            AgentCapability(
                name="email_synchronization",
                display_name="邮件同步",
                description="从Gmail同步邮件到本地数据库",
                icon="sync",
                category="data_management"
            ),
            AgentCapability(
                name="email_analysis",
                display_name="邮件分析",
                description="使用AI分析邮件内容和重要性",
                icon="analytics",
                category="intelligence"
            ),
            AgentCapability(
                name="daily_report_generation",
                display_name="日报生成",
                description="生成每日邮件摘要报告",
                icon="description",
                category="reporting"
            ),
            AgentCapability(
                name="batch_processing",
                display_name="批量处理",
                description="批量分析和处理邮件",
                icon="folder_open",
                category="automation"
            ),
            AgentCapability(
                name="importance_assessment",
                display_name="重要性评估",
                description="基于用户偏好评估邮件重要性",
                icon="priority_high",
                category="intelligence"
            ),
            AgentCapability(
                name="business_opportunity_detection",
                display_name="商机识别",
                description="识别邮件中的商业机会",
                icon="business_center",
                category="intelligence"
            ),
            AgentCapability(
                name="content_summarization",
                display_name="内容摘要",
                description="生成邮件内容的简洁摘要",
                icon="summarize",
                category="intelligence"
            ),
            AgentCapability(
                name="sentiment_analysis",
                display_name="情感分析",
                description="分析邮件的情感倾向",
                icon="sentiment_satisfied",
                category="intelligence"
            )
        ]
    
    def get_capabilities_by_category(self) -> Dict[str, List[AgentCapability]]:
        """按类别组织能力"""
        capabilities = self.get_capabilities()
        categorized = {}
        for cap in capabilities:
            if cap.category not in categorized:
                categorized[cap.category] = []
            categorized[cap.category].append(cap)
        return categorized