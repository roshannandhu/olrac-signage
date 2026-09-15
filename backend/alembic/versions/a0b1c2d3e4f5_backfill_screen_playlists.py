"""backfill screen playlists

Revision ID: a0b1c2d3e4f5
Revises: b8d2c4e6a017
Create Date: 2026-09-14

Every screen should have its own playlist from pairing time, so the dashboard
always shows the content library and playback timeline. Screens paired before
this change may still have playlist_id IS NULL; this migration creates an empty
playlist for each one.
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'b8d2c4e6a017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if context.is_offline_mode():
        return
    conn = op.get_bind()

    # Find all active screens that have no playlist of their own.
    screens = conn.execute(
        sa.text(
            "SELECT id, name, organization_id FROM screens "
            "WHERE playlist_id IS NULL AND deleted_at IS NULL AND organization_id IS NOT NULL"
        )
    ).fetchall()

    for screen in screens:
        screen_id, screen_name, org_id = screen
        label = screen_name or f"Screen {screen_id}"
        # Insert the playlist and retrieve its id in a dialect-safe way.
        conn.execute(
            sa.text(
                "INSERT INTO playlists (organization_id, name) VALUES (:org_id, :name)"
            ),
            {"org_id": org_id, "name": f"{label} loop"},
        )
        # last_insert_rowid() works on SQLite; for Postgres the ORM sequence does the
        # same thing via currval. Using a SELECT MAX is safe here because this migration
        # runs inside a single transaction.
        row = conn.execute(
            sa.text("SELECT MAX(id) FROM playlists WHERE organization_id = :org_id AND name = :name"),
            {"org_id": org_id, "name": f"{label} loop"},
        ).fetchone()
        playlist_id = row[0]
        conn.execute(
            sa.text("UPDATE screens SET playlist_id = :pid WHERE id = :sid"),
            {"pid": playlist_id, "sid": screen_id},
        )


def downgrade() -> None:
    # Downgrade is deliberately a no-op: the playlists are empty and harmless,
    # and deleting them would orphan any items an operator may have added since.
    pass
