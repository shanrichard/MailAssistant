"""add_history_id_fields_to_user_for_task_3_14

Revision ID: 8769ba0ca920
Revises: 30224a568d17
Create Date: 2025-07-24 14:21:22.665908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8769ba0ca920'
down_revision: Union[str, None] = '30224a568d17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 为Gmail History API优化添加字段
    op.add_column('users', 
        sa.Column('last_history_id', sa.String(255), nullable=True, 
                 comment='Gmail History API的最后historyId，用于增量同步')
    )
    
    op.add_column('users', 
        sa.Column('last_history_sync', sa.DateTime(timezone=True), nullable=True,
                 comment='最后一次使用History API同步的时间')
    )
    
    # 创建索引提高查询性能
    op.create_index('idx_users_last_history_id', 'users', ['last_history_id'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_users_last_history_id', table_name='users')
    
    # 删除字段
    op.drop_column('users', 'last_history_sync')
    op.drop_column('users', 'last_history_id')
