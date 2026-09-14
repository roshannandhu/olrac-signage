"""Let a package mean "no screen limit" as well as a number.

0 already meant two different things across this schema, and screens was the odd one out:
`Plan.max_ad_slots = 0` and `Plan.max_clients = 0` both mean UNLIMITED, while
`Plan.max_screens = 0` means a package that grants no screens at all. So there was no value
at all that expressed "unlimited screens" -- an operator trying to give a tenant everything
would set 0 and cut off every television they owned.

NULL now carries that meaning, which `Organization.effective_max_screens` already returns
for "no limit" and `ensure_screen_quota` already treats as unbounded. 0 keeps meaning zero,
so a genuinely screenless package is still expressible and test_tenant_isolation keeps
working.

Revision ID: c7e1f0a9b352
Revises: d1a2b3c4e5f6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7e1f0a9b352"
down_revision: Union[str, None] = "d1a2b3c4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "plans",
        "max_screens",
        existing_type=sa.Integer(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Anything unlimited has to become a number again. 0 would be the literal opposite --
    # every tenant on that package instantly capped at no screens -- so pick a ceiling high
    # enough to behave like the unlimited it is replacing.
    op.execute("UPDATE plans SET max_screens = 9999 WHERE max_screens IS NULL")
    op.alter_column(
        "plans",
        "max_screens",
        existing_type=sa.Integer(),
        nullable=False,
        existing_nullable=True,
    )
