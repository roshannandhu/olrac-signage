"""Plans gain a period, a client cap and a one-time price; custom-plan request queue.

Revision ID: d1a2b3c4e5f6
Revises: c9e2f4a71b83
Create Date: 2026-09-09

The storefront sells access as a one-time charge for a fixed window rather than a
monthly/yearly subscription, and lets a tenant buy a client cap and per-plan features. The
recurring columns stay untouched so the old subscription checkout keeps working; these are
added alongside.

`price_paise` backfills from `monthly_price_paise` so every existing package already has a
one-time price the day this ships -- a package that was free stays free (monthly 0 -> 0).
`duration_days` defaults to 30 and `max_clients`/`max_screens`... all default to 0 =
unlimited, which is the same sentinel the rest of the quota code already reads.
"""
from alembic import op
import sqlalchemy as sa


revision = "d1a2b3c4e5f6"
down_revision = "c9e2f4a71b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("max_clients", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("plans", sa.Column("price_paise", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("plans", sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"))
    # A package's one-time price starts as its monthly figure; the operator can retune it in
    # the admin editor. Free packages (monthly 0) stay free.
    op.execute("UPDATE plans SET price_paise = monthly_price_paise WHERE price_paise = 0")

    op.add_column(
        "organizations",
        sa.Column("max_clients", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "custom_plan_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("max_screens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_ad_slots", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_storage_bytes", sa.BigInteger(), nullable=False, server_default="10737418240"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("feature_flags_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("price_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("provider_order_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('requested', 'priced', 'paid', 'rejected')",
            name="ck_custom_plan_requests_status",
        ),
    )
    op.create_index("ix_custom_plan_requests_organization_id", "custom_plan_requests", ["organization_id"])
    op.create_index("ix_custom_plan_requests_status", "custom_plan_requests", ["status"])
    op.create_index(
        "ix_custom_plan_requests_provider_order_id",
        "custom_plan_requests",
        ["provider_order_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("custom_plan_requests")
    op.drop_column("organizations", "max_clients")
    op.drop_column("plans", "duration_days")
    op.drop_column("plans", "price_paise")
    op.drop_column("plans", "max_clients")
