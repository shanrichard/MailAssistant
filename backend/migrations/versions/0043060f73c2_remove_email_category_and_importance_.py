"""Remove email category and importance_score fields and EmailAnalysis table

Revision ID: 0043060f73c2
Revises: bd2d815b7786
Create Date: 2025-07-25 18:00:03.941069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0043060f73c2'
down_revision: Union[str, None] = 'bd2d815b7786'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除 emails 表的 category 和 importance_score 字段
    op.drop_index('idx_emails_category', table_name='emails')
    op.drop_index('idx_emails_importance', table_name='emails')
    op.drop_column('emails', 'category')
    op.drop_column('emails', 'importance_score')
    
    # 删除 email_analyses 表
    op.drop_table('email_analyses')


def downgrade() -> None:
    # 恢复 email_analyses 表
    op.create_table('email_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('llm_provider', sa.String(length=50), nullable=False),
        sa.Column('llm_model', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False),
        sa.Column('importance_reason', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('key_points', sa.JSON(), nullable=True),
        sa.Column('sentiment', sa.String(length=20), nullable=True),
        sa.Column('urgency_level', sa.String(length=20), nullable=True),
        sa.Column('has_business_opportunity', sa.Boolean(), nullable=True),
        sa.Column('business_opportunity_type', sa.String(length=100), nullable=True),
        sa.Column('business_opportunity_description', sa.Text(), nullable=True),
        sa.Column('matches_user_preferences', sa.Boolean(), nullable=True),
        sa.Column('preference_match_reasons', sa.JSON(), nullable=True),
        sa.Column('recommended_actions', sa.JSON(), nullable=True),
        sa.Column('content_embedding', sa.String(), nullable=True),
        sa.Column('analysis_version', sa.String(length=20), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['email_id'], ['emails.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email_id')
    )
    
    # 恢复 emails 表的字段
    op.add_column('emails', sa.Column('category', sa.String(length=50), nullable=True))
    op.add_column('emails', sa.Column('importance_score', sa.Float(), nullable=True))
    op.create_index('idx_emails_importance', 'emails', ['importance_score'], unique=False)
    op.create_index('idx_emails_category', 'emails', ['category'], unique=False)
