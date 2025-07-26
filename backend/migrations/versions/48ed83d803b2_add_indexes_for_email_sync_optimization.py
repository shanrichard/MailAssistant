"""add_indexes_for_email_sync_optimization

Revision ID: 48ed83d803b2
Revises: cf908f72ad39
Create Date: 2025-07-27 00:15:52.233138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48ed83d803b2'
down_revision: Union[str, None] = 'cf908f72ad39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为邮件表添加索引以优化同步查询性能
    op.create_index('idx_email_user_date', 'emails', ['user_id', 'received_at'])
    
    # 确保gmail_id的唯一性约束（如果还没有的话）
    # 注意：这个可能已经存在，如果报错可以忽略
    try:
        op.create_unique_constraint('uq_email_user_gmail', 'emails', ['user_id', 'gmail_id'])
    except Exception:
        # 约束可能已存在
        pass


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_email_user_date', 'emails')
    
    # 删除唯一约束（如果存在）
    try:
        op.drop_constraint('uq_email_user_gmail', 'emails', type_='unique')
    except Exception:
        # 约束可能不存在
        pass
