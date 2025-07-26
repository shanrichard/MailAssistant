"""Remove UserPreference table for task 3-20-5

Revision ID: cf908f72ad39
Revises: 0043060f73c2
Create Date: 2025-07-25 21:54:50.428855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf908f72ad39'
down_revision: Union[str, None] = '0043060f73c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除 user_preferences 表的索引
    op.drop_index('idx_user_preferences_priority', table_name='user_preferences')
    op.drop_index('idx_user_preferences_active', table_name='user_preferences')
    op.drop_index('idx_user_preferences_key', table_name='user_preferences')
    op.drop_index('idx_user_preferences_type', table_name='user_preferences')
    op.drop_index('idx_user_preferences_user_id', table_name='user_preferences')
    
    # 删除 user_preferences 表
    op.drop_table('user_preferences')


def downgrade() -> None:
    # 重新创建 user_preferences 表
    op.create_table('user_preferences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('preference_type', sa.String(length=50), nullable=False),
        sa.Column('preference_key', sa.String(length=255), nullable=False),
        sa.Column('preference_value', sa.Text(), nullable=False),
        sa.Column('is_important', sa.Boolean(), nullable=True),
        sa.Column('priority_level', sa.Integer(), nullable=True),
        sa.Column('natural_description', sa.Text(), nullable=True),
        sa.Column('description_embedding', sa.String(), nullable=True),
        sa.Column('match_count', sa.Integer(), nullable=True),
        sa.Column('positive_feedback_count', sa.Integer(), nullable=True),
        sa.Column('negative_feedback_count', sa.Integer(), nullable=True),
        sa.Column('effectiveness_score', sa.Float(), nullable=True),
        sa.Column('daily_report_time', sa.Time(), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True),
        sa.Column('auto_sync_enabled', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_learned', sa.Boolean(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_matched_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 重新创建索引
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'], unique=False)
    op.create_index('idx_user_preferences_type', 'user_preferences', ['preference_type'], unique=False)
    op.create_index('idx_user_preferences_key', 'user_preferences', ['preference_key'], unique=False)
    op.create_index('idx_user_preferences_active', 'user_preferences', ['is_active'], unique=False)
    op.create_index('idx_user_preferences_priority', 'user_preferences', ['priority_level'], unique=False)
