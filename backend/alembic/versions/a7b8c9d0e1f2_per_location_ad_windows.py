"""Per-location run windows on an ad placement target

Revision ID: a7b8c9d0e1f2
Revises: f4a5b6c7d8e9
Create Date: 2026-09-02

One client regularly buys different lengths in different places -- 30 days in a mall, 10 in
a shop, 50 at an airport -- because the sites are worth different amounts to them. The
booking carried a single starts_at/ends_at applied to every location, so this could only be
expressed as three separate bookings: three invoice lines, three extensions and three
report rows for one commercial deal.

Both columns are nullable and NULL means "inherit the booking", so every existing row keeps
exactly today's behaviour and no backfill is needed.

Nothing here touches price. The money stays on the booking, which is what an invoice shows
as sold; these two columns are the delivery schedule.
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded because backend/main.py builds a brand-new database with create_all() and
    # then stamps it at head, so on a fresh deployment these already exist.
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("ad_placement_targets")
    }
    if "starts_at" not in columns:
        op.add_column(
            "ad_placement_targets",
            sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "ends_at" not in columns:
        op.add_column(
            "ad_placement_targets",
            sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("ad_placement_targets", "ends_at")
    op.drop_column("ad_placement_targets", "starts_at")
