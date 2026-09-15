"""Record whether a screen can install an update without a human.

Android permits a silent install only for the device owner. Every other panel raises a system
confirmation dialog -- on a television that usually has nobody in front of it -- so a
published release reaches it only if somebody happens to walk past and tap. Nothing reported
which screens were in that state, so a fleet could sit half-updated with no sign of why.

Nullable with no backfill: a screen that has not reported yet genuinely has no answer, and
guessing one would claim an unattended update path that may not exist. Every running player
reports it on its next heartbeat.

Revision ID: a3f7c210e9b4
Revises: b8d2c4e6a017
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a3f7c210e9b4"
down_revision: Union[str, None] = "a0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("screens")}
    if "device_owner" not in columns:
        op.add_column("screens", sa.Column("device_owner", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("screens", "device_owner")
