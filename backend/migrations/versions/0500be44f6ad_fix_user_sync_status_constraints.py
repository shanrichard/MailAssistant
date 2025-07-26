"""fix_user_sync_status_constraints

Revision ID: 0500be44f6ad
Revises: 20e5b75175c9
Create Date: 2025-07-23 18:19:18.722298

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0500be44f6ad'
down_revision: Union[str, None] = '20e5b75175c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL to safely drop constraint if exists
    conn = op.get_bind()
    conn.execute(sa.text("""
        ALTER TABLE user_sync_status 
        DROP CONSTRAINT IF EXISTS user_sync_status_progress_check
    """))
    
    # Add new constraint that allows progress_percentage to be any value between 0 and 100
    # regardless of is_syncing status
    op.create_check_constraint(
        'user_sync_status_progress_check',
        'user_sync_status',
        'progress_percentage >= 0 AND progress_percentage <= 100'
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint('user_sync_status_progress_check', 'user_sync_status', type_='check')
    
    # Restore the old constraint
    op.create_check_constraint(
        'user_sync_status_progress_check',
        'user_sync_status',
        '(is_syncing = false AND progress_percentage = 100) OR (is_syncing = true AND progress_percentage >= 0 AND progress_percentage <= 100)'
    )
