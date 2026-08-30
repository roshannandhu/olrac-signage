"""Organization approvals and system settings

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("status", sa.String(), nullable=False, server_default="active"))
    op.add_column("organizations", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("organizations", sa.Column("approved_by_user_id", sa.Integer(), nullable=True))
    op.add_column("organizations", sa.Column("rejection_reason", sa.String(), nullable=True))

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("key", sa.String(), unique=True, index=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_column("organizations", "rejection_reason")
    op.drop_column("organizations", "approved_by_user_id")
    op.drop_column("organizations", "approved_at")
    op.drop_column("organizations", "status")
