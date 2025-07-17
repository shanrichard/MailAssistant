"""
OAuth Flow Manager
符合Google OAuth Client Library最佳实践的Flow对象管理器
使用数据库存储以解决开发模式热重载问题
"""

# 直接导入数据库版本的实现
from .oauth_flow_manager_db import OAuthFlowManager

# 创建全局实例
oauth_flow_manager = OAuthFlowManager()

__all__ = ['OAuthFlowManager', 'oauth_flow_manager']