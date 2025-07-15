"""
Task scheduler module for MailAssistant
"""
from .scheduler_app import scheduler, start_scheduler, stop_scheduler
from .jobs import setup_user_jobs, create_daily_report_job, create_token_refresh_job

__all__ = [
    "scheduler",
    "start_scheduler", 
    "stop_scheduler",
    "setup_user_jobs",
    "create_daily_report_job",
    "create_token_refresh_job"
]