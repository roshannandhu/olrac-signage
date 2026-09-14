"""Record how strong a screen's hardware identity is.

The player has always worked out which identifier it could actually produce -- serial,
ANDROID_ID, or a random fallback -- and `DeviceState.identitySource` says in its own comment
that it is "reported to the server so an operator can tell WHY a screen did or did not come
back as itself". It was never sent and never stored, so the fleet had no way to show which
panels would return as duplicates after a wipe. You found out by finding the duplicate.

Nullable with no backfill: screens registered before this genuinely have no recorded answer,
and inventing one would claim a survivability nobody verified. They report it on their next
registration, which every running panel does on boot.

Revision ID: b8d2c4e6a017
Revises: c7e1f0a9b352
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8d2c4e6a017"
down_revision: Union[str, None] = "c7e1f0a9b352"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("screens", sa.Column("identity_source", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("screens", "identity_source")
