"""Screen approval gate

Revision ID: a1b2c3d4e5f6
Revises: e8c4d7b19f36
Create Date: 2026-08-24

A screen that claims an organisation from the TV itself now waits for an operator to let
it in. Existing screens are backfilled as approved: they are already running in the field,
and shipping this with a NULL default would blank every one of them on deploy.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "e8c4d7b19f36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("screens", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    # Backfill BEFORE anything can create an unapproved row. Every screen that exists today
    # was admitted under the old rules, so it stays admitted.
    op.execute("UPDATE screens SET approved_at = CURRENT_TIMESTAMP WHERE approved_at IS NULL")


def downgrade() -> None:
    op.drop_column("screens", "approved_at")
