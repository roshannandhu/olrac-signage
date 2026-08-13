"""Enrollment token lifecycle fields

Revision ID: 7d838c74ac9a
Revises: 79d608748198
Create Date: 2026-08-07 13:51:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '7d838c74ac9a'
down_revision: Union[str, None] = '79d608748198'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
def upgrade() -> None:
    op.add_column('enrollment_tokens', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('enrollment_tokens', sa.Column('max_uses', sa.Integer(), nullable=True))
    op.add_column('enrollment_tokens', sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('enrollment_tokens', 'use_count')
    op.drop_column('enrollment_tokens', 'max_uses')
    op.drop_column('enrollment_tokens', 'expires_at')
