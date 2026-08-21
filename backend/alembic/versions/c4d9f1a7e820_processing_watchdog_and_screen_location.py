"""content.processing_started_at

Revision ID: c4d9f1a7e820
Revises: b7e2d84a1f30
Create Date: 2026-08-17

``content.processing_started_at`` lets the reaper find transcode jobs whose worker died,
which is the only way to clear a row that no error handler ever sees.
* ``screens.location`` — the venue a screen sits in. Several screens share one location,
  so proof-of-play can be reported per place as well as per screen.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4d9f1a7e820'
down_revision = 'b7e2d84a1f30'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('content', sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True))
    # Rows already mid-flight have no start time, so the reaper would ignore them forever.
    # Treating them as started now gives them one normal timeout window.
    op.execute(
        "UPDATE content SET processing_started_at = NOW() "
        "WHERE status = 'processing' AND processing_started_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column('content', 'processing_started_at')
