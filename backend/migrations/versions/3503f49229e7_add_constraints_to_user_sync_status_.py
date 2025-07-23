"""Add constraints to user_sync_status table

Revision ID: 3503f49229e7
Revises: f00564e3c768
Create Date: 2025-07-22 18:37:23.568124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '3503f49229e7'
down_revision: Union[str, None] = 'f00564e3c768'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 首先清理不一致的数据
    # 修复数据不一致：is_syncing=true 但 progress=100 的情况
    op.execute(text("""
        UPDATE user_sync_status 
        SET is_syncing = false, progress_percentage = 100 
        WHERE is_syncing = true AND progress_percentage = 100
    """))
    
    # 清理僵死任务（超过1小时未更新的运行中任务）
    op.execute(text("""
        UPDATE user_sync_status 
        SET is_syncing = false, 
            error_message = 'Cleaned by migration at ' || NOW()::text,
            progress_percentage = 0
        WHERE is_syncing = true 
          AND updated_at < NOW() - INTERVAL '1 hour'
    """))
    
    # 检查并创建约束（如果不存在）
    # 1. 状态一致性检查约束
    op.execute(text("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_sync_state_consistency'
            ) THEN
                ALTER TABLE user_sync_status ADD CONSTRAINT chk_sync_state_consistency CHECK (
                    (is_syncing = true AND progress_percentage >= 0 AND progress_percentage <= 99)
                    OR 
                    (is_syncing = false AND progress_percentage IN (0, 100))
                );
            END IF;
        END $$;
    """))
    
    # 2. 任务ID唯一索引
    op.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_task_id 
        ON user_sync_status (task_id) 
        WHERE task_id IS NOT NULL
    """))
    
    # 3. 部分唯一索引 - 每个用户只能有一个运行中的任务
    op.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uniq_user_running_sync 
        ON user_sync_status (user_id) 
        WHERE is_syncing = true
    """))
    
    # 4. 添加性能索引
    op.create_index(
        'idx_sync_status_updated',
        'user_sync_status',
        ['updated_at'],
        if_not_exists=True
    )
    
    # 5. 添加组合索引用于查询僵死任务
    op.create_index(
        'idx_sync_status_zombie_check',
        'user_sync_status',
        ['is_syncing', 'updated_at'],
        if_not_exists=True
    )


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_sync_status_zombie_check', 'user_sync_status')
    op.drop_index('idx_sync_status_updated', 'user_sync_status')
    op.execute(text("DROP INDEX IF EXISTS uniq_user_running_sync"))
    op.drop_index('uniq_task_id', 'user_sync_status')
    
    # 删除约束
    op.drop_constraint('chk_sync_state_consistency', 'user_sync_status', type_='check')
