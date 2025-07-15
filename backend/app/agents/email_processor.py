"""
EmailProcessor Agent - 基于LLM-Driven架构的邮件处理代理
"""
from typing import List
from langchain.tools import Tool

from .base_agent import BaseAgent
from .email_tools import create_email_tools
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class EmailProcessorAgent(BaseAgent):
    """邮件处理Agent - 无状态，专注于邮件分析和日报生成"""
    
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
        """构建EmailProcessor特定的系统prompt"""
        base_prompt = super()._build_system_prompt()
        
        # 修改系统消息，添加EmailProcessor特定的指导
        messages = base_prompt.messages.copy()
        
        # 更新系统消息
        system_message = messages[0]
        enhanced_system_message = f"""{system_message.prompt.template}

你是专门负责邮件分析和处理的智能代理。你的专业领域包括：

1. 邮件内容分析和重要性评估
2. 邮件分类和情感分析
3. 商业机会识别
4. 日报生成和数据统计
5. 批量邮件处理和同步

工作原则：
- 始终基于用户偏好进行邮件重要性判断
- 提供详细的分析理由和建议
- 高效处理大量邮件数据
- 生成结构化、有价值的报告内容
- 识别并突出重要信息和机会

可用工具说明：
- sync_emails: 同步Gmail邮件到本地
- analyze_email: 深度分析单封邮件
- generate_daily_report: 生成每日邮件报告
- batch_analyze_emails: 批量分析邮件

请根据用户请求，智能选择合适的工具组合来完成任务。"""
        
        # 更新系统消息模板
        messages[0].prompt.template = enhanced_system_message
        
        return base_prompt
    
    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [
            "email_synchronization",     # 邮件同步
            "email_analysis",            # 邮件分析
            "daily_report_generation",   # 日报生成
            "batch_processing",          # 批量处理
            "importance_assessment",     # 重要性评估
            "business_opportunity_detection",  # 商业机会识别
            "content_summarization",     # 内容摘要
            "sentiment_analysis"         # 情感分析
        ]