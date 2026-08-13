"""add playlist transition controls

Revision ID: f2c9a1d4e7b0
Revises: b71f3d902ac4
Create Date: 2026-08-07 01:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c9a1d4e7b0"
down_revision: Union[str, None] = "b71f3d902ac4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "playlists",
        sa.Column("default_transition", sa.String(), nullable=False, server_default="fade"),
    )
    op.add_column(
        "playlists",
        sa.Column("default_transition_ms", sa.Integer(), nullable=False, server_default="600"),
    )
    op.add_column("playlist_items", sa.Column("transition", sa.String(), nullable=True))
    op.add_column("playlist_items", sa.Column("transition_ms", sa.Integer(), nullable=True))

    # Backfill the product default so every existing item has deterministic
    # behavior immediately after deployment. New rows may inherit the playlist.
    op.execute("UPDATE playlist_items SET transition = 'fade', transition_ms = 600")


def downgrade() -> None:
    with op.batch_alter_table("playlist_items") as batch_op:
        batch_op.drop_column("transition_ms")
        batch_op.drop_column("transition")
    with op.batch_alter_table("playlists") as batch_op:
        batch_op.drop_column("default_transition_ms")
        batch_op.drop_column("default_transition")
