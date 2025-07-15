"""
邮件处理工具 - 使用LangChain @tool装饰器
"""
import json
from typing import Dict, Any, Optional
from datetime import datetime, date, timedelta
from langchain.tools import tool

from ..core.logging import get_logger
from ..models.email import Email
from ..models.email_analysis import EmailAnalysis
from ..services.email_sync_service import email_sync_service
from ..services.gmail_service import gmail_service

logger = get_logger(__name__)

def create_email_tools(user_id: str, db_session, user_context: Dict[str, Any]):
    """创建邮件处理工具集"""
    
    @tool
    def sync_emails(days: int = 1) -> str:
        """同步Gmail邮件到本地数据库。
        
        Args:
            days: 同步最近多少天的邮件，默认1天
            
        Returns:
            同步结果的JSON字符串，包含新邮件数量等信息
        """
        try:
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
            
        except Exception as e:
            logger.error("Email sync failed", user_id=user_id, error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"邮件同步失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def analyze_email(email_id: str) -> str:
        """分析单封邮件的内容和重要性。
        
        Args:
            email_id: 邮件ID
            
        Returns:
            分析结果的JSON字符串，包含重要性评分、分类、摘要等
        """
        try:
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
            
        except Exception as e:
            logger.error("Email analysis failed", 
                        user_id=user_id, 
                        email_id=email_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"邮件分析失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def generate_daily_report(target_date: Optional[str] = None) -> str:
        """生成指定日期的邮件日报。
        
        Args:
            target_date: 目标日期，格式YYYY-MM-DD，不指定则生成今日报告
            
        Returns:
            日报内容的JSON字符串
        """
        try:
            if target_date:
                report_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            else:
                report_date = date.today()
            
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
            
            logger.info("Daily report generated", 
                       user_id=user_id, 
                       date=report_date.isoformat(),
                       total_emails=total_emails,
                       important_count=len(important_emails))
            
            return json.dumps(report, ensure_ascii=False)
            
        except Exception as e:
            logger.error("Daily report generation failed", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"日报生成失败：{str(e)}"
            }, ensure_ascii=False)
    
    @tool
    def batch_analyze_emails(days: int = 1) -> str:
        """批量分析最近的邮件。
        
        Args:
            days: 分析最近多少天的邮件
            
        Returns:
            批量分析结果的JSON字符串
        """
        try:
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
            
        except Exception as e:
            logger.error("Batch email analysis failed", 
                        user_id=user_id, 
                        error=str(e))
            return json.dumps({
                "status": "error",
                "message": f"批量分析失败：{str(e)}"
            }, ensure_ascii=False)
    
    return [sync_emails, analyze_email, generate_daily_report, batch_analyze_emails]