"""A screen cap on a booking sold without a package

Revision ID: b7d1e3f5a921
Revises: e5f6a1b2c3d4
Create Date: 2026-09-15

A package caps how many screens a booking may cover (TenantPlan.max_locations) and
ensure_plan_locations refuses the screen that breaches it. A CUSTOM booking -- no package,
negotiated price -- had no such number anywhere, so "three screens for 40,000" was a deal
the tenant could strike and nothing could hold them to: the fourth screen went on from the
booking page, the screen page or the playlist builder and the client silently received more
than they had bought.

0 means uncapped, which is what every booking sold before this carries and what a custom
sale still means when the operator leaves the box empty. Only read when the booking is on
no plan; a package states its own limit and wins.
"""

from alembic import op
import sqlalchemy as sa


revision = "b7d1e3f5a921"
down_revision = "e5f6a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded for the same reason as e5f6a1b2c3d4: backend/main.py builds a fresh database
    # with create_all() and stamps it at head, so on a new deployment the column is already
    # there and an unconditional add_column would fail the first `alembic upgrade`.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("ad_placements")}
    if "max_locations" not in columns:
        op.add_column(
            "ad_placements",
            sa.Column("max_locations", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_column("ad_placements", "max_locations")
