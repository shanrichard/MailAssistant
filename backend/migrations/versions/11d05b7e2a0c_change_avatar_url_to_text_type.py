"""change avatar_url to text type

Revision ID: 11d05b7e2a0c
Revises: f01f87d404d5
Create Date: 2025-07-16 13:56:41.036693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '11d05b7e2a0c'
down_revision: Union[str, None] = 'f01f87d404d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_apscheduler_jobs_next_run_time', table_name='apscheduler_jobs')
    op.drop_table('apscheduler_jobs')
    
    # Change avatar_url from VARCHAR(1000) to TEXT
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.VARCHAR(length=1000),
                    type_=sa.Text(),
                    existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Revert avatar_url from TEXT to VARCHAR(1000)
    op.alter_column('users', 'avatar_url',
                    existing_type=sa.Text(),
                    type_=sa.VARCHAR(length=1000),
                    existing_nullable=True)
    
    op.create_table('apscheduler_jobs',
    sa.Column('id', sa.VARCHAR(length=191), autoincrement=False, nullable=False),
    sa.Column('next_run_time', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('job_state', postgresql.BYTEA(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='apscheduler_jobs_pkey')
    )
    op.create_index('ix_apscheduler_jobs_next_run_time', 'apscheduler_jobs', ['next_run_time'], unique=False)
    # ### end Alembic commands ###
