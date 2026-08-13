"""Add timezone to DateTime

Revision ID: 190f5bb76578
Revises: 360debe251bb
Create Date: 2026-08-07 10:28:19.525866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '190f5bb76578'
down_revision: Union[str, None] = '360debe251bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timezone to all DateTime columns
    for table, cols in [
        ('plans', ['created_at']),
        ('organizations', ['created_at']),
        ('subscriptions', ['current_period_start', 'current_period_end', 'grace_period_end', 'created_at', 'updated_at']),
        ('webhook_events', ['received_at']),
        ('users', ['created_at']),
        ('screen_groups', ['created_at', 'updated_at']),
        ('screens', ['pair_code_expires_at', 'last_seen', 'assignment_updated_at', 'last_error_at']),
        ('content', ['uploaded_at']),
        ('playlists', ['created_at', 'updated_at']),
        ('playlist_items', ['start_at', 'end_at'])
    ]:
        for col in cols:
            op.alter_column(table, col, type_=sa.DateTime(timezone=True))

def downgrade() -> None:
    pass
