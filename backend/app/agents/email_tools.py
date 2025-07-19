"""
邮件处理工具 - 使用LangChain @tool装饰器
"""
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime, date, timedelta
from functools import wraps
import time
from langchain.tools import tool

from ..core.logging import get_logger
from ..models.email import Email
from ..models.email_analysis import EmailAnalysis
from ..models.daily_report_log import DailyReportLog
from ..models.analysis_audit_log import AnalysisAuditLog
from ..services.email_sync_service import email_sync_service
from ..services.gmail_service import gmail_service
from sqlalchemy.exc import IntegrityError

logger = get_logger(__name__)

def safe_tool_wrapper(tool_func: Callable) -> Callable:
    """统一的tool异常包装器"""
    @wraps(tool_func)
    def wrapper(*args, **kwargs) -> str:
        tool_name = tool_func.__name__
        start_time = time.time()
        try:
            result = tool_func(*args, **kwargs)
            # 确保结果是字符串
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False)
            
            # 记录执行时间
            execution_time = time.time() - start_time
            logger.info(f"Tool {tool_name} executed successfully", 
                       execution_time_ms=int(execution_time * 1000))
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Tool {tool_name} JSON error", exc_info=True)
            return json.dumps({
                "status": "error",
                "tool": tool_name,
                "error_type": "json_decode_error",
                "message": f"JSON解析错误: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed", exc_info=True)
            return json.dumps({
                "status": "error",
                "tool": tool_name,
                "error_type": type(e).__name__,
                "message": f"工具执行失败: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
    
    # 保留tool的元数据
    wrapper.name = tool_name
    wrapper.description = getattr(tool_func, 'description', '')
    
    return wrapper

def create_email_tools(user_id: str, db_session, user_context: Dict[str, Any]):
    """创建邮件处理工具集"""
    import uuid
    # 确保 user_id 是 UUID 对象
    if isinstance(user_id, str):
        user_id_uuid = uuid.UUID(user_id)
    else:
        user_id_uuid = user_id
    
    @tool
    @safe_tool_wrapper
    def sync_emails(days: int = 1) -> str:
        """同步Gmail邮件到本地数据库。
        
        Args:
            days: 同步最近多少天的邮件，默认1天
            
        Returns:
            同步结果的JSON字符串，包含新邮件数量等信息
        """
        sync_stats = email_sync_service.sync_user_emails(
            db_session, 
            user_id, 
            days=days,
            max_messages=100
        )
        
        result = {
            "status": "success",
            "new_emails": sync_stats.get("new_emails", 0),
            "updated_emails": sync_stats.get("updated_emails", 0),
            "total_processed": sync_stats.get("total_processed", 0),
            "sync_time": datetime.now().isoformat()
        }
        
        logger.info("Email sync completed", 
                   user_id=user_id, 
                   new_emails=result["new_emails"])
        
        return json.dumps(result, ensure_ascii=False)
    
    @tool
    @safe_tool_wrapper
    def analyze_email(email_id: str) -> str:
        """分析单封邮件的内容和重要性。
        
        Args:
            email_id: 邮件ID
            
        Returns:
            分析结果的JSON字符串，包含重要性评分、分类、摘要等
        """
        # 获取邮件
        email = db_session.query(Email).filter(
            Email.id == email_id,
            Email.user_id == user_id
        ).first()
        
        if not email:
            return json.dumps({
                "status": "error",
                "message": "邮件不存在"
            }, ensure_ascii=False)
        
        # 检查是否已分析
        existing_analysis = db_session.query(EmailAnalysis).filter(
            EmailAnalysis.email_id == email_id,
            EmailAnalysis.user_id == user_id
        ).first()
        
        if existing_analysis:
            return json.dumps({
                "status": "success",
                "analysis": {
                    "email_id": email_id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "category": existing_analysis.category,
                    "importance_score": existing_analysis.importance_score,
                    "importance_reason": existing_analysis.importance_reason,
                    "summary": existing_analysis.summary,
                    "key_points": existing_analysis.key_points,
                    "sentiment": existing_analysis.sentiment,
                    "urgency_level": existing_analysis.urgency_level,
                    "has_business_opportunity": existing_analysis.has_business_opportunity,
                    "recommended_actions": existing_analysis.recommended_actions
                }
            }, ensure_ascii=False)
        
        # 使用LLM分析邮件
        from ..agents.llm_provider import llm_provider_manager
        
        analysis_prompt = f"""
        请分析以下邮件的内容和重要性：
        
        主题：{email.subject}
        发件人：{email.sender}
        内容：{email.body_text[:2000]}  # 截取前2000字符
        
        请以JSON格式返回分析结果，包含：
        - category: 邮件类别（工作、个人、商业、营销等）
        - importance_score: 重要性评分（0-1）
        - importance_reason: 重要性原因
        - summary: 邮件摘要
        - key_points: 关键点列表
        - sentiment: 情感（positive/neutral/negative）
        - urgency_level: 紧急程度（low/medium/high）
        - has_business_opportunity: 是否包含商业机会
        - recommended_actions: 建议的行动
        """
        
        llm_response = llm_provider_manager.generate_with_fallback(analysis_prompt)
        
        # 解析LLM响应
        try:
            analysis_data = json.loads(llm_response)
        except json.JSONDecodeError:
            # 如果无法解析，使用默认分析
            analysis_data = {
                "category": "其他",
                "importance_score": 0.5,
                "importance_reason": "无法自动分析",
                "summary": email.subject,
                "key_points": [],
                "sentiment": "neutral",
                "urgency_level": "medium",
                "has_business_opportunity": False,
                "recommended_actions": []
            }
        
        # 保存分析结果
        email_analysis = EmailAnalysis(
            email_id=email_id,
            user_id=user_id,
            llm_provider="openai",
            llm_model="gpt-4o",
            category=analysis_data.get("category", "其他"),
            importance_score=analysis_data.get("importance_score", 0.5),
            importance_reason=analysis_data.get("importance_reason", ""),
            summary=analysis_data.get("summary", ""),
            key_points=analysis_data.get("key_points", []),
            sentiment=analysis_data.get("sentiment", "neutral"),
            urgency_level=analysis_data.get("urgency_level", "medium"),
            has_business_opportunity=analysis_data.get("has_business_opportunity", False),
            business_opportunity_type=analysis_data.get("business_opportunity_type"),
            business_opportunity_description=analysis_data.get("business_opportunity_description"),
            recommended_actions=analysis_data.get("recommended_actions", []),
            processing_time_ms=1000,
            confidence_score=0.8
        )
        
        db_session.add(email_analysis)
        db_session.commit()
        
        result = {
            "status": "success",
            "analysis": {
                "email_id": email_id,
                "subject": email.subject,
                "sender": email.sender,
                **analysis_data
            }
        }
        
        logger.info("Email analysis completed", 
                   user_id=user_id, 
                   email_id=email_id,
                   importance_score=analysis_data.get("importance_score"))
        
        return json.dumps(result, ensure_ascii=False)
    
    @tool
    @safe_tool_wrapper
    def generate_daily_report(target_date: Optional[str] = None) -> str:
        """生成指定日期的邮件日报 - 支持幂等性。
        
        Args:
            target_date: 目标日期，格式YYYY-MM-DD，不指定则生成今日报告
            
        Returns:
            日报内容的JSON字符串
        """
        if target_date:
            report_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            report_date = date.today()
        
        # 检查是否已存在日报
        existing_report = db_session.query(DailyReportLog).filter(
            DailyReportLog.user_id == user_id_uuid,
            DailyReportLog.report_date == report_date,
            DailyReportLog.status == "completed"
        ).first()
        
        if existing_report:
            logger.info(f"Daily report already exists for {user_id} on {report_date}")
            return json.dumps({
                "status": "success",
                "message": "日报已存在",
                "report_id": str(existing_report.id),
                "created_at": existing_report.created_at.isoformat(),
                **existing_report.report_content
            }, ensure_ascii=False)
        
        # 创建处理中的记录（防止并发）
        report_log = DailyReportLog(
            user_id=user_id_uuid,
            report_date=report_date,
            status="processing",
            report_content={}
        )
        
        try:
            db_session.add(report_log)
            db_session.commit()
        except IntegrityError:
            # 并发情况下，另一个进程已创建
            db_session.rollback()
            return generate_daily_report(target_date)  # 递归重试
        
        # 获取当日邮件
        emails = db_session.query(Email).filter(
            Email.user_id == user_id,
            Email.received_at >= report_date,
            Email.received_at < report_date + timedelta(days=1)
        ).all()
        
        if not emails:
            return json.dumps({
                "status": "success",
                "date": report_date.isoformat(),
                "total_emails": 0,
                "message": "今日暂无邮件"
            }, ensure_ascii=False)
        
        # 获取分析结果
        analyses = db_session.query(EmailAnalysis).filter(
            EmailAnalysis.user_id == user_id,
            EmailAnalysis.email_id.in_([email.id for email in emails])
        ).all()
        
        # 统计信息
        total_emails = len(emails)
        important_emails = [a for a in analyses if a.importance_score > 0.7]
        urgent_emails = [a for a in analyses if a.urgency_level == "high"]
        business_opportunities = [a for a in analyses if a.has_business_opportunity]
        
        # 生成报告
        report = {
            "status": "success",
            "date": report_date.isoformat(),
            "total_emails": total_emails,
            "important_count": len(important_emails),
            "urgent_count": len(urgent_emails),
            "business_opportunities": len(business_opportunities),
            "important_emails": [
                {
                    "subject": next(e.subject for e in emails if e.id == a.email_id),
                    "sender": next(e.sender for e in emails if e.id == a.email_id),
                    "importance_score": a.importance_score,
                    "summary": a.summary,
                    "key_points": a.key_points
                }
                for a in important_emails[:5]  # 只显示前5个
            ],
            "urgent_emails": [
                {
                    "subject": next(e.subject for e in emails if e.id == a.email_id),
                    "sender": next(e.sender for e in emails if e.id == a.email_id),
                    "urgency_level": a.urgency_level,
                    "summary": a.summary
                }
                for a in urgent_emails[:3]  # 只显示前3个
            ],
            "business_opportunities": [
                {
                    "subject": next(e.subject for e in emails if e.id == a.email_id),
                    "sender": next(e.sender for e in emails if e.id == a.email_id),
                    "opportunity_type": a.business_opportunity_type,
                    "description": a.business_opportunity_description
                }
                for a in business_opportunities
            ]
        }
        
        # 更新记录
        report_log.report_content = report
        report_log.status = "completed"
        db_session.commit()
        
        logger.info("Daily report generated", 
                   user_id=user_id, 
                   date=report_date.isoformat(),
                   total_emails=total_emails,
                   important_count=len(important_emails))
        
        return json.dumps({
            **report,
            "report_id": str(report_log.id)
        }, ensure_ascii=False)
    
    @tool
    @safe_tool_wrapper
    def batch_analyze_emails(days: int = 1) -> str:
        """批量分析最近的邮件。
        
        Args:
            days: 分析最近多少天的邮件
            
        Returns:
            批量分析结果的JSON字符串
        """
        # 先同步邮件
        sync_result = sync_emails(days)
        sync_data = json.loads(sync_result)
        
        if sync_data["status"] != "success":
            return sync_result
        
        # 获取未分析的邮件
        unanalyzed_emails = db_session.query(Email).filter(
            Email.user_id == user_id,
            ~Email.id.in_(
                db_session.query(EmailAnalysis.email_id).filter(
                    EmailAnalysis.user_id == user_id
                )
            )
        ).limit(50).all()  # 限制批次大小
        
        if not unanalyzed_emails:
            return json.dumps({
                "status": "success",
                "message": "没有需要分析的新邮件",
                "analyzed_count": 0,
                "sync_result": sync_data
            }, ensure_ascii=False)
        
        # 批量分析
        analyzed_count = 0
        errors = []
        
        for email in unanalyzed_emails:
            try:
                analysis_result = analyze_email(str(email.id))
                analysis_data = json.loads(analysis_result)
                
                if analysis_data["status"] == "success":
                    analyzed_count += 1
                else:
                    errors.append(f"分析邮件 {email.subject} 失败")
                    
            except Exception as e:
                errors.append(f"处理邮件 {email.subject} 时出错: {str(e)}")
        
        result = {
            "status": "success",
            "analyzed_count": analyzed_count,
            "total_emails": len(unanalyzed_emails),
            "errors": errors[:5],  # 只返回前5个错误
            "sync_result": sync_data
        }
        
        logger.info("Batch email analysis completed", 
                   user_id=user_id,
                   analyzed_count=analyzed_count,
                   error_count=len(errors))
        
        return json.dumps(result, ensure_ascii=False)
    
    return [sync_emails, analyze_email, generate_daily_report, batch_analyze_emails]