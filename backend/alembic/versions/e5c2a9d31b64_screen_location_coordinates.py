"""screen location with coordinates

Revision ID: e5c2a9d31b64
Revises: d8b3e5c1f742
Create Date: 2026-08-17

Where a screen physically is. The name and the coordinates are stored together so a client
report's label and its map pin always describe the same place; place_id lets a later lookup
re-resolve the same venue without searching by name again.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5c2a9d31b64'
down_revision = 'd8b3e5c1f742'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('screens', sa.Column('location', sa.String(), nullable=True))
    op.add_column('screens', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('screens', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('screens', sa.Column('place_id', sa.String(), nullable=True))
    # Reports group by this, and it is low cardinality.
    op.create_index('ix_screens_location', 'screens', ['location'])


def downgrade() -> None:
    op.drop_index('ix_screens_location', table_name='screens')
    for column in ('place_id', 'longitude', 'latitude', 'location'):
        op.drop_column('screens', column)
