"""add subscription plans, billing state, and storage accounting

Revision ID: e6b8c0d3f5a2
Revises: d5a7b9c2e4f1
Create Date: 2026-08-07 02:34:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6b8c0d3f5a2"
down_revision: Union[str, None] = "d5a7b9c2e4f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

GIB = 1024 * 1024 * 1024


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("monthly_price_paise", sa.Integer(), nullable=False),
        sa.Column("yearly_price_paise", sa.Integer(), nullable=False),
        sa.Column("max_screens", sa.Integer(), nullable=False),
        sa.Column("max_storage_bytes", sa.BigInteger(), nullable=False),
        sa.Column("feature_flags_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_plans_slug"),
    )
    op.create_index("ix_plans_id", "plans", ["id"])
    op.create_index("ix_plans_slug", "plans", ["slug"], unique=True)
    plans = sa.table(
        "plans",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("monthly_price_paise", sa.Integer()),
        sa.column("yearly_price_paise", sa.Integer()),
        sa.column("max_screens", sa.Integer()),
        sa.column("max_storage_bytes", sa.BigInteger()),
        sa.column("feature_flags_json", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        plans,
        [
            {
                "id": 1,
                "name": "Free",
                "slug": "free",
                "monthly_price_paise": 0,
                "yearly_price_paise": 0,
                "max_screens": 5,
                "max_storage_bytes": 10 * GIB,
                "feature_flags_json": '{"scheduling": true}',
                "is_active": True,
            },
            {
                "id": 2,
                "name": "Starter",
                "slug": "starter",
                "monthly_price_paise": 99900,
                "yearly_price_paise": 999000,
                "max_screens": 10,
                "max_storage_bytes": 25 * GIB,
                "feature_flags_json": '{"scheduling": true, "transitions": true}',
                "is_active": True,
            },
            {
                "id": 3,
                "name": "Business",
                "slug": "business",
                "monthly_price_paise": 299900,
                "yearly_price_paise": 2999000,
                "max_screens": 50,
                "max_storage_bytes": 100 * GIB,
                "feature_flags_json": '{"scheduling": true, "transitions": true, "priority_support": true}',
                "is_active": True,
            },
        ],
    )

    op.execute(f"UPDATE organizations SET plan_id = 1 WHERE plan_id IS NULL")
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.create_foreign_key("fk_organizations_plan_id", "plans", ["plan_id"], ["id"])

    op.add_column(
        "content",
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("billing_period", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("grace_period_end", sa.DateTime(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("provider_subscription_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], name="fk_subscriptions_organization_id"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], name="fk_subscriptions_plan_id"),
        sa.UniqueConstraint("organization_id", name="uq_subscriptions_organization_id"),
        sa.UniqueConstraint("provider_subscription_id", name="uq_subscriptions_provider_subscription_id"),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"])
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"], unique=True)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_provider_subscription_id", "subscriptions", ["provider_subscription_id"], unique=True)
    op.execute(
        "INSERT INTO subscriptions (organization_id, plan_id, status, billing_period) "
        "SELECT id, plan_id, 'active', 'monthly' FROM organizations"
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("provider_event_id", name="uq_webhook_events_provider_event_id"),
    )
    op.create_index("ix_webhook_events_id", "webhook_events", ["id"])
    op.create_index("ix_webhook_events_provider_event_id", "webhook_events", ["provider_event_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_webhook_events_provider_event_id", table_name="webhook_events")
    op.drop_index("ix_webhook_events_id", table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_index("ix_subscriptions_provider_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_organization_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    with op.batch_alter_table("content") as batch_op:
        batch_op.drop_column("file_size_bytes")
    with op.batch_alter_table("organizations") as batch_op:
        batch_op.drop_constraint("fk_organizations_plan_id", type_="foreignkey")
    op.drop_index("ix_plans_slug", table_name="plans")
    op.drop_index("ix_plans_id", table_name="plans")
    op.drop_table("plans")
