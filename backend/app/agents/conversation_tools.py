"""
对话处理工具 - 使用LangChain @tool装饰器
"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from langchain.tools import tool

from ..core.logging import get_logger
from ..models.email import Email
from ..models.daily_report import DailyReport
from ..models.user_preference import UserPreference
from ..services.gmail_service import gmail_service

logger = get_logger(__name__)

def create_conversation_tools(user_id: str, db_session, user_context: Dict[str, Any]):
    """创建对话处理工具集"""
    
    @tool
    def search_email_history(query: str, limit: int = 10) -> str:
        """搜索历史邮件。
        
        Args:
            query: 搜索关键词，可以是主题、发件人或内容关键词
            limit: 返回结果数量限制，默认10
            
        Returns:
            搜索结果的JSON字符串
        """
        try:
            # 简单的关键词搜索
            emails = db_session.query(Email).filter(
                Email.user_id == user_id,
                (Email.subject.contains(query) | 
                 Email.sender.contains(query) | 
                 Email.body_text.contains(query))
            ).order_by(Email.received_at.desc()).limit(limit).all()
            
            results = []
            for email in emails:
                results.append({
                    "id": str(email.id),
                    "subject": email.subject,
                    "sender": email.sender,
                    "received_at": email.received_at.isoformat(),
                    "snippet": email.body_text[:200] + "..." if len(email.body_text) > 200 else email.body_text
                })
            
            result = {
                "status": "success",
                "query": query,
                "results_count": len(results),
                "results": results
            }
            
            logger.info("Email search completed", 
                       user_id=user_id, 
                       query=query,
                       results_count=len(results))
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Email search failed", 
                        user_id=user_id, 
                        query=query, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"搜索失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def read_daily_report(date: Optional[str] = None) -> str:
        """读取指定日期的日报。
        
        Args:
            date: 日期，格式YYYY-MM-DD，不指定则读取今日日报
            
        Returns:
            日报内容的JSON字符串
        """
        try:
            if date:
                report_date = datetime.strptime(date, "%Y-%m-%d").date()
            else:
                report_date = date.today()
            
            # 查找已存储的日报
            daily_report = db_session.query(DailyReport).filter(
                DailyReport.user_id == user_id,
                DailyReport.report_date == report_date
            ).first()
            
            if daily_report:
                result = {
                    "status": "success",
                    "date": report_date.isoformat(),
                    "content": daily_report.content,
                    "summary": daily_report.summary,
                    "important_count": daily_report.important_emails_count,
                    "total_count": daily_report.total_emails_count,
                    "created_at": daily_report.created_at.isoformat()
                }
            else:
                # 如果没有存储的日报，尝试实时生成
                from .email_tools import create_email_tools
                email_tools = create_email_tools(user_id, db_session, user_context)
                
                # 找到generate_daily_report工具
                generate_report_tool = next(
                    (tool for tool in email_tools if tool.name == "generate_daily_report"), 
                    None
                )
                
                if generate_report_tool:
                    report_result = generate_report_tool.func(report_date.isoformat())
                    report_data = json.loads(report_result)
                    
                    if report_data["status"] == "success":
                        result = report_data
                    else:
                        result = {
                            "status": "error",
                            "message": f"无法生成{report_date.isoformat()}的日报"
                        }
                else:
                    result = {
                        "status": "error",
                        "message": "日报生成工具不可用"
                    }
            
            logger.info("Daily report read", 
                       user_id=user_id, 
                       date=report_date.isoformat(),
                       status=result["status"])
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Daily report read failed", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"读取日报失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def bulk_mark_read(criteria: str) -> str:
        """批量标记邮件为已读。
        
        Args:
            criteria: 标记条件，可以是"广告邮件"、"营销邮件"、"不重要邮件"等自然语言描述
            
        Returns:
            操作结果的JSON字符串
        """
        try:
            # 根据条件查找邮件
            emails_to_mark = []
            
            if "广告" in criteria or "营销" in criteria:
                # 查找广告/营销邮件
                emails = db_session.query(Email).filter(
                    Email.user_id == user_id,
                    (Email.subject.contains("广告") | 
                     Email.subject.contains("营销") | 
                     Email.subject.contains("推广") |
                     Email.subject.contains("优惠") |
                     Email.sender.contains("noreply") |
                     Email.sender.contains("newsletter"))
                ).limit(100).all()
                emails_to_mark = emails
                
            elif "不重要" in criteria:
                # 查找不重要邮件（重要性评分低于0.3）
                from ..models.email_analysis import EmailAnalysis
                low_importance_analyses = db_session.query(EmailAnalysis).filter(
                    EmailAnalysis.user_id == user_id,
                    EmailAnalysis.importance_score < 0.3
                ).limit(100).all()
                
                email_ids = [a.email_id for a in low_importance_analyses]
                emails = db_session.query(Email).filter(
                    Email.user_id == user_id,
                    Email.id.in_(email_ids)
                ).all()
                emails_to_mark = emails
                
            else:
                # 其他条件，使用关键词搜索
                emails = db_session.query(Email).filter(
                    Email.user_id == user_id,
                    (Email.subject.contains(criteria) | 
                     Email.sender.contains(criteria) | 
                     Email.body_text.contains(criteria))
                ).limit(100).all()
                emails_to_mark = emails
            
            if not emails_to_mark:
                return json.dumps({
                    "status": "success",
                    "message": f"没有找到符合条件 '{criteria}' 的邮件",
                    "affected_count": 0
                }, ensure_ascii=False)
            
            # 批量标记为已读
            affected_count = 0
            errors = []
            
            for email in emails_to_mark:
                try:
                    # 调用Gmail API标记为已读
                    gmail_service.mark_email_as_read(
                        user_context["user"], 
                        email.gmail_id
                    )
                    affected_count += 1
                    
                except Exception as e:
                    errors.append(f"标记邮件 {email.subject} 失败: {str(e)}")
            
            result = {
                "status": "success",
                "criteria": criteria,
                "affected_count": affected_count,
                "total_found": len(emails_to_mark),
                "errors": errors[:5],  # 只返回前5个错误
                "operation": "mark_read"
            }
            
            logger.info("Bulk mark read completed", 
                       user_id=user_id, 
                       criteria=criteria,
                       affected_count=affected_count)
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Bulk mark read failed", 
                        user_id=user_id, 
                        criteria=criteria, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"批量标记失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def update_user_preferences(preference_description: str, preference_type: str = "important") -> str:
        """更新用户偏好设置。
        
        Args:
            preference_description: 偏好描述，如"来自GitHub的通知很重要"
            preference_type: 偏好类型，可以是"important"、"unimportant"或"schedule"
            
        Returns:
            更新结果的JSON字符串
        """
        try:
            # 创建新的偏好记录
            new_preference = UserPreference(
                user_id=user_id,
                preference_type=preference_type,
                preference_key="auto_generated",
                preference_value="auto_generated",
                natural_description=preference_description,
                priority_level=3 if preference_type == "important" else 1,
                is_active=True
            )
            
            db_session.add(new_preference)
            db_session.commit()
            
            result = {
                "status": "success",
                "message": "偏好设置已更新",
                "preference_type": preference_type,
                "description": preference_description,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info("User preference updated", 
                       user_id=user_id, 
                       preference_type=preference_type,
                       description=preference_description)
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("User preference update failed", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"偏好更新失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def trigger_email_processor(action: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """触发EmailProcessor执行特定任务。
        
        Args:
            action: 要执行的动作，如"generate_daily_report"、"batch_analyze_emails"
            parameters: 动作参数
            
        Returns:
            执行结果的JSON字符串
        """
        try:
            # 导入EmailProcessor
            from .email_processor import EmailProcessorAgent
            
            # 创建EmailProcessor实例
            processor = EmailProcessorAgent(user_id, db_session)
            
            # 构建请求消息
            if action == "generate_daily_report":
                message = "请生成今天的邮件日报"
                if parameters and parameters.get("date"):
                    message = f"请生成{parameters['date']}的邮件日报"
            elif action == "batch_analyze_emails":
                days = parameters.get("days", 1) if parameters else 1
                message = f"请分析最近{days}天的邮件"
            else:
                message = f"请执行{action}操作"
                if parameters:
                    message += f"，参数：{json.dumps(parameters, ensure_ascii=False)}"
            
            # 执行处理
            response = processor.process(message)
            
            result = {
                "status": "success",
                "action": action,
                "response": response,
                "executed_at": datetime.now().isoformat()
            }
            
            logger.info("Email processor triggered", 
                       user_id=user_id, 
                       action=action,
                       has_parameters=bool(parameters))
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Email processor trigger failed", 
                        user_id=user_id, 
                        action=action, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"触发EmailProcessor失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def get_task_status(task_type: str = "all") -> str:
        """查询任务状态。
        
        Args:
            task_type: 任务类型，可以是"all"、"email_sync"、"analysis"、"report"
            
        Returns:
            任务状态的JSON字符串
        """
        try:
            # 这里可以查询任务日志或状态
            # 暂时返回模拟数据
            result = {
                "status": "success",
                "task_type": task_type,
                "tasks": [
                    {
                        "id": "sync_001",
                        "type": "email_sync",
                        "status": "completed",
                        "started_at": "2025-07-14T10:00:00",
                        "completed_at": "2025-07-14T10:02:00",
                        "result": "同步了15封新邮件"
                    },
                    {
                        "id": "analysis_001",
                        "type": "email_analysis",
                        "status": "running",
                        "started_at": "2025-07-14T10:02:00",
                        "progress": "50%",
                        "result": "已分析8/15封邮件"
                    }
                ],
                "summary": {
                    "total_tasks": 2,
                    "completed": 1,
                    "running": 1,
                    "failed": 0
                }
            }
            
            logger.info("Task status queried", 
                       user_id=user_id, 
                       task_type=task_type)
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Task status query failed", 
                        user_id=user_id, 
                        task_type=task_type, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"查询任务状态失败：{str(e)}"
            }, ensure_ascii=False)
    
    return [
        search_email_history, 
        read_daily_report, 
        bulk_mark_read, 
        update_user_preferences, 
        trigger_email_processor,
        get_task_status
    ]