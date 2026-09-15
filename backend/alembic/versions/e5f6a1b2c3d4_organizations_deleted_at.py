"""Removal column for organizations, so a tenant can be taken off the platform reversibly

Revision ID: e5f6a1b2c3d4
Revises: a3f7c210e9b4
Create Date: 2026-09-14

There was no way to remove a tenant at all. The console could Block one (status="suspended",
which stops API access and destroys nothing) or end its plan, and that was the whole range:
a workspace that had left still held its screens, its adverts and its bytes for ever.

A straight DELETE is not available. Twelve of the eighteen tables carrying organization_id
have a plain foreign key with no ON DELETE rule, so the statement fails on the first
constraint it meets, and relaxing them would trade a loud error for silent orphans.

So removal is a mark, and `purge_removed_tenants` does the destroying 30 days later. The
gap is the point: an admin who removes the wrong workspace has a month to put it back, and
after that nothing survives -- rows or objects.

Indexed because the purge sweep filters on it, and because every organization read now
carries `deleted_at IS NULL`.
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a1b2c3d4"
down_revision = "a3f7c210e9b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Guarded because backend/main.py builds a brand-new database with create_all() and
    # then stamps it at head -- so on a fresh deployment this column already exists and an
    # unconditional add_column would fail the first `alembic upgrade`.
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("organizations")}
    if "deleted_at" not in columns:
        op.add_column(
            "organizations", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
        )
        op.create_index("ix_organizations_deleted_at", "organizations", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_organizations_deleted_at", table_name="organizations")
    op.drop_column("organizations", "deleted_at")
