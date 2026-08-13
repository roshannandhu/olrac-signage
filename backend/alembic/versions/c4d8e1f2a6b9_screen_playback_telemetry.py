"""add screen playback telemetry

Revision ID: c4d8e1f2a6b9
Revises: f2c9a1d4e7b0
Create Date: 2026-08-07 02:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d8e1f2a6b9"
down_revision: Union[str, None] = "f2c9a1d4e7b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("screens", sa.Column("app_version", sa.String(), nullable=True))
    op.add_column(
        "screens",
        sa.Column("playback_state", sa.String(), nullable=False, server_default="idle"),
    )
    op.add_column("screens", sa.Column("current_item_id", sa.Integer(), nullable=True))
    op.add_column("screens", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("screens", sa.Column("last_error_at", sa.DateTime(), nullable=True))

    # Preserve the version already reported by deployed players.
    op.execute("UPDATE screens SET app_version = device_version WHERE device_version IS NOT NULL")


def downgrade() -> None:
    with op.batch_alter_table("screens") as batch_op:
        batch_op.drop_column("last_error_at")
        batch_op.drop_column("last_error")
        batch_op.drop_column("current_item_id")
        batch_op.drop_column("playback_state")
        batch_op.drop_column("app_version")
