"""
ConversationHandler Agent - 基于LLM-Driven架构的对话处理代理
"""
from typing import List
from langchain.tools import Tool

from .base_agent import StatefulAgent
from .conversation_tools import create_conversation_tools
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class ConversationHandler(StatefulAgent):
    """对话处理Agent - 有状态，专注于用户交互和任务调度"""
    
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
    
    def _build_system_prompt(self):
        """构建ConversationHandler特定的系统prompt"""
        base_prompt = super()._build_system_prompt()
        
        # 修改系统消息，添加ConversationHandler特定的指导
        messages = base_prompt.messages.copy()
        
        # 更新系统消息
        system_message = messages[0]
        enhanced_system_message = f"""{system_message.prompt.template}

你是用户的贴心邮件管家，负责理解用户需求并协调各种邮件管理任务。你的专业领域包括：

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
        
        # 更新系统消息模板
        messages[0].prompt.template = enhanced_system_message
        
        return base_prompt
    
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
            "context_awareness"               # 上下文感知
        ]