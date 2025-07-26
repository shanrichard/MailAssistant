"""add_status_field_to_user_sync_status

Revision ID: 20e5b75175c9
Revises: 3503f49229e7
Create Date: 2025-07-23 17:22:11.708082

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20e5b75175c9'
down_revision: Union[str, None] = '3503f49229e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 status 字段
    op.add_column('user_sync_status', 
        sa.Column('status', sa.String(20), nullable=False, server_default='CREATED')
    )
    
    # 更新现有数据
    connection = op.get_bind()
    connection.execute(sa.text("""
        UPDATE user_sync_status 
        SET status = CASE 
            WHEN is_syncing = true THEN 'RUNNING'
            WHEN progress_percentage = 100 THEN 'SUCCEEDED'
            ELSE 'FAILED'
        END
    """))
    
    # 创建索引提高查询性能
    op.create_index('idx_user_sync_status_status', 'user_sync_status', ['status'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_user_sync_status_status', table_name='user_sync_status')
    
    # 删除 status 字段
    op.drop_column('user_sync_status', 'status')
