"""Payments become a ledger: many receipts against one booking.

Revision ID: c9e2f4a71b83
Revises: b3d6f8a1c204
Create Date: 2026-09-06

`uq_ad_payments_placement` allowed exactly one payment row per booking, and the payment
route therefore UPDATED that row instead of adding to it. Clients pay deposits: recording
the second 5,000 of a 10,000 campaign overwrote the first and filed them as having paid
half. The money was not just mis-reported, it was gone -- no row, no date, no method, no
reference for the first instalment.

Dropping the constraint is the whole change. `is_paid` is already the shadow of a zero
balance (see placements.settlement) and every reader already goes through it, so summing
several rows instead of reading one needs nothing else migrated.

The zero-amount sweep is here rather than left to chance: the previous migration
backfilled a payment row for every booking flagged paid, `price_paise` and all, so a
booking sold for nothing left a receipt for nothing behind. Those rows carry no
information and would fail the new check constraint.
"""
from alembic import op
import sqlalchemy as sa


revision = "c9e2f4a71b83"
down_revision = "b3d6f8a1c204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_ad_payments_placement", "ad_payments", type_="unique")
    # A receipt for nothing is a mis-click. It adds no money and drags the booking into
    # "part paid", which is worse than the flag it replaced.
    op.execute("DELETE FROM ad_payments WHERE amount_paise <= 0")
    op.create_check_constraint(
        "ck_ad_payments_amount_positive", "ad_payments", "amount_paise > 0"
    )


def downgrade() -> None:
    # Lossy, and unavoidably so: one row cannot hold two methods or two dates. The TOTAL is
    # preserved on the most recent receipt -- the money is the part that matters -- and the
    # earlier rows go. Restoring the constraint with duplicates present would fail outright,
    # which is a worse downgrade than a documented collapse.
    op.drop_constraint("ck_ad_payments_amount_positive", "ad_payments", type_="check")
    op.execute(
        """
        UPDATE ad_payments SET amount_paise = totals.total
        FROM (
            SELECT placement_id, SUM(amount_paise) AS total, MAX(id) AS keep_id
            FROM ad_payments GROUP BY placement_id
        ) AS totals
        WHERE ad_payments.id = totals.keep_id
        """
    )
    op.execute(
        """
        DELETE FROM ad_payments WHERE id NOT IN (
            SELECT MAX(id) FROM ad_payments GROUP BY placement_id
        )
        """
    )
    op.create_unique_constraint("uq_ad_payments_placement", "ad_payments", ["placement_id"])
