"""add organization ownership to tenant data

Revision ID: d5a7b9c2e4f1
Revises: c4d8e1f2a6b9
Create Date: 2026-08-07 02:28:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5a7b9c2e4f1"
down_revision: Union[str, None] = "c4d8e1f2a6b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORGANIZATION_ID = 1
TENANT_TABLES = ("users", "screens", "screen_groups", "content", "playlists")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column(
            "storage_quota_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default=str(10 * 1024 * 1024 * 1024),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_id", "organizations", ["id"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    op.execute(
        "INSERT INTO organizations (id, name, slug, storage_quota_bytes) "
        f"VALUES ({DEFAULT_ORGANIZATION_ID}, 'Default Organization', 'default', {10 * 1024 * 1024 * 1024})"
    )

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("organization_id", sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {table} SET organization_id = {DEFAULT_ORGANIZATION_ID} "
            "WHERE organization_id IS NULL"
        )
        with op.batch_alter_table(table) as batch_op:
            batch_op.create_foreign_key(
                f"fk_{table}_organization_id",
                "organizations",
                ["organization_id"],
                ["id"],
            )
            if table != "screens":
                batch_op.alter_column("organization_id", existing_type=sa.Integer(), nullable=False)
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(f"fk_{table}_organization_id", type_="foreignkey")
            batch_op.drop_column("organization_id")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_index("ix_organizations_id", table_name="organizations")
    op.drop_table("organizations")
