"""
Database models for MailAssistant
"""

from .user import User
from .email import Email
from .email_analysis import EmailAnalysis
from .user_preference import UserPreference
from .daily_report import DailyReport
from .task_log import TaskLog, TaskStatus, TaskType
from .oauth_session import OAuthSession, SessionStatus

__all__ = [
    "User",
    "Email", 
    "EmailAnalysis",
    "UserPreference",
    "DailyReport",
    "TaskLog",
    "TaskStatus",
    "TaskType",
    "OAuthSession",
    "SessionStatus",
]