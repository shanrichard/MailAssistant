"""
EmailProcessor Agent - 基于LLM-Driven架构的邮件处理代理
"""
from typing import List, Dict
import threading
from dataclasses import dataclass
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage

from .base_agent import BaseAgent
from .email_tools import create_email_tools
from ..core.config import settings
from ..core.logging import get_logger
from .llm_provider import llm_provider_manager
from ..config.agent_prompts import EMAIL_PROCESSOR_SYSTEM_PROMPT

logger = get_logger(__name__)

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
    """邮件处理Agent - 无状态，专注于邮件分析和日报生成"""
    
    # 类级别 LLM 缓存
    _llm_cache = {}
    _cache_lock = threading.Lock()
    
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
        
        return create_email_tools(self.user_id, self.db, user_context)
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        return settings.agents.email_processor_default_model
    
    def _get_temperature(self) -> float:
        """获取温度参数"""
        return settings.agents.email_processor_temperature
    
    def _build_system_prompt(self):
        """构建EmailProcessor特定的系统prompt - 使用函数式方案避免修改父类"""
        base_prompt = super()._build_system_prompt()
        
        # 获取基础系统消息内容
        base_system_content = base_prompt.messages[0].content if hasattr(base_prompt.messages[0], 'content') else base_prompt.messages[0].prompt.template
        
        # 使用外部化的 prompt
        email_processor_instructions = EMAIL_PROCESSOR_SYSTEM_PROMPT
        
        # 使用函数式方法构建新的prompt，不修改原始对象
        return ChatPromptTemplate.from_messages([
            ("system", "{base_system}\n\n{email_instructions}"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ]).partial(
            base_system=base_system_content,
            email_instructions=email_processor_instructions
        )
    
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