
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date, timedelta
from langchain.tools import Tool, StructuredTool  # 需要Tool类来包装函数给ConversationHandler使用

from ..core.logging import get_logger
from ..models.email import Email
from ..models.daily_report import DailyReport
from ..services.gmail_service import gmail_service

logger = get_logger(__name__)

def create_conversation_tools(user_id: str, db_session, user_context: Dict[str, Any]):
    """创建对话处理工具集"""
    
    def search_email_history(
        query: Optional[str] = None,
        days_back: Optional[int] = None,
        sender: Optional[str] = None,
        is_read: Optional[bool] = None,
        has_attachments: Optional[bool] = None,
        limit: int = 20
    ) -> str:
        """搜索历史邮件，支持多种搜索条件。
        
        Args:
            query: 搜索关键词，在主题、发件人或内容中搜索
            days_back: 搜索最近多少天的邮件
            sender: 发件人邮箱或名称筛选
            is_read: 是否已读（True=已读，False=未读，None=全部）
            has_attachments: 是否有附件
            limit: 返回结果数量限制，默认20
            
        Returns:
            搜索结果的JSON字符串
        """
        try:
            # 构建基础查询
            query_builder = db_session.query(Email).filter(Email.user_id == user_id)
            
            # 时间范围筛选
            if days_back is not None:
                from_date = datetime.now() - timedelta(days=days_back)
                query_builder = query_builder.filter(Email.received_at >= from_date)
            
            # 关键词搜索 - 使用大小写不敏感的 ilike
            if query:
                query_builder = query_builder.filter(
                    (Email.subject.ilike(f'%{query}%') | 
                     Email.sender.ilike(f'%{query}%') | 
                     Email.body_plain.ilike(f'%{query}%'))
                )
            
            # 发件人筛选 - 使用大小写不敏感的 ilike
            if sender:
                query_builder = query_builder.filter(Email.sender.ilike(f'%{sender}%'))
            
            # 已读/未读筛选
            if is_read is not None:
                query_builder = query_builder.filter(Email.is_read == is_read)
            
            # 附件筛选
            if has_attachments is not None:
                query_builder = query_builder.filter(Email.has_attachments == has_attachments)
            
            # 执行查询，按时间降序排序
            emails = query_builder.order_by(Email.received_at.desc()).limit(limit).all()
            
            # 构建结果
            results = []
            sender_stats = {}  # 统计发件人
            
            for email in emails:
                results.append({
                    "id": str(email.id),
                    "subject": email.subject,
                    "sender": email.sender,
                    "received_at": email.received_at.isoformat(),
                    "is_read": email.is_read,
                    "is_important": email.is_important,
                    "has_attachments": email.has_attachments,
                    "snippet": email.body_plain[:200] + "..." if email.body_plain and len(email.body_plain) > 200 else email.body_plain
                })
                
                # 统计发件人
                if email.sender not in sender_stats:
                    sender_stats[email.sender] = 0
                sender_stats[email.sender] += 1
            
            # 构建响应
            result = {
                "status": "success",
                "search_params": {
                    "query": query,
                    "days_back": days_back,
                    "sender": sender,
                    "is_read": is_read,
                    "has_attachments": has_attachments
                },
                "results_count": len(results),
                "results": results,
                "sender_summary": sorted(
                    [{"sender": k, "count": v} for k, v in sender_stats.items()],
                    key=lambda x: x["count"],
                    reverse=True
                )[:10]  # 只返回前10个发件人
            }
            
            logger.info("Email search completed", 
                       user_id=user_id, 
                       search_params=result["search_params"],
                       results_count=len(results))
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Email search failed", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"搜索失败：{str(e)}"
            }, ensure_ascii=False)
    
    def read_daily_report(report_date_str: Optional[str] = None) -> str:
        """读取指定日期的日报。
        
        Args:
            report_date_str: 日期字符串，格式YYYY-MM-DD，不指定则读取今日日报
            
        Returns:
            日报内容的JSON字符串
        """
        try:
            if report_date_str:
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
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
                # 查找可能不重要的邮件（基于常见模式）
                emails = db_session.query(Email).filter(
                    Email.user_id == user_id,
                    (Email.subject.contains("通知") |
                     Email.subject.contains("newsletter") |
                     Email.subject.contains("marketing") |
                     Email.sender.contains("no-reply") |
                     Email.sender.contains("notification"))
                ).limit(100).all()
                emails_to_mark = emails
                
            else:
                # 其他条件，使用关键词搜索
                emails = db_session.query(Email).filter(
                    Email.user_id == user_id,
                    (Email.subject.contains(criteria) | 
                     Email.sender.contains(criteria) | 
                     Email.body_plain.contains(criteria))
                ).limit(100).all()
                emails_to_mark = emails
            
            if not emails_to_mark:
                return json.dumps({
                    "status": "success",
                    "message": f"没有找到符合条件 '{criteria}' 的邮件",
                    "affected_count": 0
                }, ensure_ascii=False)
            
            # 批量标记为已读（优化版本）
            gmail_ids = [email.gmail_id for email in emails_to_mark]
            
            # 分片处理避免 Gmail API 限流
            CHUNK_SIZE = 50
            affected_count = 0
            errors = []
            
            for i in range(0, len(gmail_ids), CHUNK_SIZE):
                chunk = gmail_ids[i:i + CHUNK_SIZE]
                try:
                    success = gmail_service.mark_as_read(user_context["user"], chunk)
                    if success:
                        affected_count += len(chunk)
                except Exception as e:
                    errors.append(f"标记批次 {i//CHUNK_SIZE + 1} 失败: {str(e)}")
                    logger.error(f"Failed to mark chunk {i//CHUNK_SIZE}: {e}")
            
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
    
    def get_user_preferences() -> str:
        """获取用户的邮件处理偏好。
        
        Returns:
            用户偏好的JSON字符串，包含自然语言描述
        """
        try:
            from ..models.user import User
            user = db_session.query(User).filter(User.id == user_id).first()
            
            if not user or not user.preferences_text:
                # 默认偏好
                default_preferences = """我希望重点关注以下类型的邮件：
1. 直接发给我的邮件（我是主要收件人，不是抄送）
2. 包含商业机会、合作意向的邮件
3. 来自重要联系人的邮件

我不太关注以下类型的邮件：
1. 群发的通知邮件
2. 营销推广邮件
3. 仅作为抄送的邮件
4. 自动生成的系统通知"""
                
                return json.dumps({
                    "preferences": default_preferences,
                    "has_preferences": False,
                    "message": "使用默认偏好设置"
                }, ensure_ascii=False)
            
            return json.dumps({
                "preferences": user.preferences_text,
                "has_preferences": True,
                "last_updated": user.updated_at.isoformat() if user.updated_at else None
            }, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Failed to get user preferences", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"获取偏好失败：{str(e)}"
            }, ensure_ascii=False)
    
    def update_user_preferences(preference_description: str) -> str:
        """更新用户偏好设置。
        
        Args:
            preference_description: 偏好的自然语言描述
            
        Returns:
            更新结果的JSON字符串
        """
        try:
            from ..models.user import User
            user = db_session.query(User).filter(User.id == user_id).first()
            
            if not user:
                return json.dumps({
                    "status": "error",
                    "message": "用户不存在"
                }, ensure_ascii=False)
            
            # 如果已有偏好，追加新的；否则直接设置
            if user.preferences_text:
                # 添加时间戳和新偏好
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                user.preferences_text += f"\n\n[{timestamp}] 更新的偏好：\n{preference_description}"
            else:
                user.preferences_text = preference_description
            
            db_session.commit()
            
            result = {
                "status": "success",
                "message": "偏好已更新",
                "preferences": user.preferences_text,
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info("User preference updated", 
                       user_id=user_id, 
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
    
    # 将函数包装成Tool对象，保持与ConversationHandler的兼容性
    tools = [
        StructuredTool.from_function(
            func=search_email_history,
            name="search_email_history",
            description="搜索历史邮件，支持多种搜索条件。可以按关键词、时间范围、发件人、已读状态、附件等条件搜索。例如：搜索最近3天的邮件用days_back=3，搜索某人的邮件用sender参数，搜索未读邮件用is_read=False。"
        ),
        StructuredTool.from_function(
            func=read_daily_report,
            name="read_daily_report",
            description=read_daily_report.__doc__ or "读取指定日期的日报"
        ),
        StructuredTool.from_function(
            func=bulk_mark_read,
            name="bulk_mark_read",
            description=bulk_mark_read.__doc__ or "批量标记邮件为已读"
        ),
        StructuredTool.from_function(
            func=get_user_preferences,
            name="get_user_preferences",
            description=get_user_preferences.__doc__ or "获取用户的邮件处理偏好"
        ),
        StructuredTool.from_function(
            func=update_user_preferences,
            name="update_user_preferences",
            description=update_user_preferences.__doc__ or "更新用户偏好设置"
        ),
        StructuredTool.from_function(
            func=trigger_email_processor,
            name="trigger_email_processor",
            description=trigger_email_processor.__doc__ or "触发EmailProcessor执行特定任务"
        ),
        StructuredTool.from_function(
            func=get_task_status,
            name="get_task_status",
            description=get_task_status.__doc__ or "查询任务状态"
        )
    ]
    
    return tools