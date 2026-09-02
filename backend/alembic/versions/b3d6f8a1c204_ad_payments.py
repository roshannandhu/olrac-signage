"""Record how a client actually paid, not just that they did.

Revision ID: b3d6f8a1c204
Revises: a7b8c9d0e1f2
Create Date: 2026-09-02

`ad_placements.is_paid` stays where it is and keeps its meaning. It is now maintained by
the payment routes rather than by a blind PUT, so the boolean and the record cannot
disagree; making it a derived property instead would have meant rewriting every read site
-- the PDF, both report exits, the serialiser, the client's total spend -- for no gain.

The backfill matters: without it every campaign already marked paid would come back unpaid
the moment the UI starts reading the payment record, and a tenant would be chasing clients
who had already settled.
"""
from alembic import op
import sqlalchemy as sa


revision = "b3d6f8a1c204"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("placement_id", sa.Integer(), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["placement_id"], ["ad_placements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("placement_id", name="uq_ad_payments_placement"),
    )
    op.create_index(op.f("ix_ad_payments_id"), "ad_payments", ["id"])
    op.create_index(op.f("ix_ad_payments_organization_id"), "ad_payments", ["organization_id"])
    op.create_index(op.f("ix_ad_payments_placement_id"), "ad_payments", ["placement_id"])

    # Everything already marked paid becomes a payment of the booking's price, method
    # "other" -- which is the honest answer, because how it was paid was never recorded.
    op.execute(
        """
        INSERT INTO ad_payments (
            organization_id, placement_id, amount_paise, method, paid_at, created_at, updated_at
        )
        SELECT organization_id, id, price_paise, 'other', created_at, created_at, created_at
        FROM ad_placements
        WHERE is_paid = true
        """
    )


def downgrade() -> None:
    # is_paid was never dropped, so the booking keeps its paid state; only the detail of
    # how it was settled goes.
    op.drop_index(op.f("ix_ad_payments_placement_id"), table_name="ad_payments")
    op.drop_index(op.f("ix_ad_payments_organization_id"), table_name="ad_payments")
    op.drop_index(op.f("ix_ad_payments_id"), table_name="ad_payments")
    op.drop_table("ad_payments")
