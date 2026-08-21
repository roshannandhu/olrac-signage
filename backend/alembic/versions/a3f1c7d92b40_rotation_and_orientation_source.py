"""per-item rotation and screen orientation source

Revision ID: a3f1c7d92b40
Revises: 496ec6d8c368
Create Date: 2026-08-16

Two columns for P10 display rotation:

* ``playlist_items.rotation`` — a per-item override in degrees. NULL means "use whatever
  the screen is set to", which is why it is nullable rather than defaulted to 0.
* ``screens.orientation_source`` — 'auto' when the device's heartbeat may overwrite the
  screen's orientation, 'manual' once an operator has set it by hand. Without this the
  next heartbeat silently reverts a deliberate portrait setting.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a3f1c7d92b40'
down_revision = '496ec6d8c368'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('playlist_items', sa.Column('rotation', sa.Integer(), nullable=True))
    op.add_column(
        'screens',
        sa.Column('orientation_source', sa.String(), nullable=False, server_default='auto'),
    )


def downgrade() -> None:
    op.drop_column('screens', 'orientation_source')
    op.drop_column('playlist_items', 'rotation')
