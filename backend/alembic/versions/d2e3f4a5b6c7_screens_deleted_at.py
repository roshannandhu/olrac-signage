"""Archive column for screens, so a TV can be removed without destroying its play history

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-08-31

There was no way to remove a screen at all -- no endpoint, no button -- and the obvious
fix, a DELETE, is not available here: `play_logs.screen_id` and
`play_log_hourly_rollups.screen_id` are both NOT NULL foreign keys to `screens.id` with no
ON DELETE rule, so the statement fails on the constraint the moment a screen has any
history, which is every screen that has ever played anything.

Relaxing those constraints instead would be worse than the error. The booking report
attributes plays to a screen BY NAME, so a NULLed screen_id silently drops rows from an
advertiser's report -- an invoice that under-reports rather than a query that fails.

So the row stays and is marked archived. `TenantScope.query` hides archived rows from every
tenant-scoped read, and the device endpoints treat one as absent, which is what signs the
panel out.

Indexed because every screen listing now carries `deleted_at IS NULL`.
"""

from alembic import op
import sqlalchemy as sa


revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded because backend/main.py builds a brand-new database with create_all() and
    # then stamps it at head -- so on a fresh deployment this column already exists and an
    # unconditional add_column would fail the first `alembic upgrade`.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("screens")}
    if "deleted_at" not in columns:
        op.add_column("screens", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index("ix_screens_deleted_at", "screens", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_screens_deleted_at", table_name="screens")
    op.drop_column("screens", "deleted_at")
