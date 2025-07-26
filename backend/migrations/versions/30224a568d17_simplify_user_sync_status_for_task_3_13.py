"""simplify_user_sync_status_for_task_3_13

Revision ID: 30224a568d17
Revises: 0500be44f6ad
Create Date: 2025-07-23 19:21:50.340990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30224a568d17'
down_revision: Union[str, None] = '0500be44f6ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加新的简化字段
    op.add_column('user_sync_status', 
        sa.Column('last_sync_time', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('user_sync_status', 
        sa.Column('sync_message', sa.Text, nullable=True)
    )
    
    # 迁移现有数据
    connection = op.get_bind()
    # 将 updated_at 作为 last_sync_time，将 error_message 合并到 sync_message
    connection.execute(sa.text("""
        UPDATE user_sync_status 
        SET 
            last_sync_time = updated_at,
            sync_message = CASE 
                WHEN error_message IS NOT NULL THEN error_message
                WHEN is_syncing = true THEN '正在同步中'
                WHEN progress_percentage = 100 THEN '同步完成'
                ELSE '同步状态未知'
            END
    """))
    
    # 删除复杂的字段
    op.drop_column('user_sync_status', 'is_syncing')
    op.drop_column('user_sync_status', 'sync_type')
    op.drop_column('user_sync_status', 'started_at')
    op.drop_column('user_sync_status', 'progress_percentage')
    op.drop_column('user_sync_status', 'current_stats')
    op.drop_column('user_sync_status', 'task_id')
    op.drop_column('user_sync_status', 'error_message')
    
    # 如果存在 status 字段也删除
    try:
        op.drop_index('idx_user_sync_status_status', table_name='user_sync_status')
        op.drop_column('user_sync_status', 'status')
    except:
        pass  # 如果字段不存在，忽略错误


def downgrade() -> None:
    # 恢复复杂字段（如果需要回滚）
    op.add_column('user_sync_status', 
        sa.Column('is_syncing', sa.Boolean, default=False, nullable=False)
    )
    op.add_column('user_sync_status', 
        sa.Column('sync_type', sa.String(20), nullable=True)
    )
    op.add_column('user_sync_status', 
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('user_sync_status', 
        sa.Column('progress_percentage', sa.Integer, default=0)
    )
    op.add_column('user_sync_status', 
        sa.Column('current_stats', sa.dialects.postgresql.JSONB, nullable=True)
    )
    op.add_column('user_sync_status', 
        sa.Column('task_id', sa.String(100), nullable=True)
    )
    op.add_column('user_sync_status', 
        sa.Column('error_message', sa.Text, nullable=True)
    )
    
    # 删除简化字段
    op.drop_column('user_sync_status', 'last_sync_time')
    op.drop_column('user_sync_status', 'sync_message')
