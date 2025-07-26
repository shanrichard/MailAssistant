"""modify_email_unique_constraint_for_task_3_14

Revision ID: bd2d815b7786
Revises: 8769ba0ca920
Create Date: 2025-07-24 14:22:46.856062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd2d815b7786'
down_revision: Union[str, None] = '8769ba0ca920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 删除原有的全局unique约束
    op.drop_constraint('emails_gmail_id_key', 'emails', type_='unique')
    
    # 添加联合唯一约束：gmail_id + user_id（专家建议防重复）
    op.create_unique_constraint('_gmail_user_uc', 'emails', ['gmail_id', 'user_id'])


def downgrade() -> None:
    # 删除联合唯一约束 
    op.drop_constraint('_gmail_user_uc', 'emails', type_='unique')
    
    # 恢复原有的全局unique约束
    op.create_unique_constraint('emails_gmail_id_key', 'emails', ['gmail_id'])
