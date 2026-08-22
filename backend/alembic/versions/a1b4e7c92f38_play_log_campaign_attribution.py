"""play log campaign attribution + drop mutable-row FKs

Revision ID: a1b4e7c92f38
Revises: f9a3c7b1d240
Create Date: 2026-08-19

Two fixes to the proof-of-play table.

1. Backfill campaign_id. The player sends campaign_id = null on every event (its cached
   playlist item carries no campaign), so every row -- and therefore every hourly rollup
   row -- had a NULL campaign. All campaign analytics filter on campaign_id, so every
   campaign reported zero plays. Ingest now derives it from the playlist; this backfills
   the rows already stored.

2. Drop the media_id / playlist_id / campaign_id foreign keys. play_logs is an
   append-only audit log that references rows operators are expected to delete. When a
   playlist or content item was removed while a device still held queued events for it,
   the batch insert raised IntegrityError -> 500 -> WorkManager retry, and because the
   device always re-sends its oldest 500 events the queue never drained: every later play
   on that screen was lost behind the wedge. Indexes are kept; only the constraints go.
   Postgres-only, since SQLite does not enforce foreign keys here (no PRAGMA
   foreign_keys=ON in database.py) and rebuilding this table would be costly.

NOTE (deliberately not done here): existing play_log_hourly_rollups rows still carry
campaign_id = NULL, so historical campaign totals stay zero. Rollups are derived data, so
they can be rebuilt -- delete the NULL-campaign rows and reset play_logs.aggregated for
the window you want -- but that re-aggregates every retained log at once and anything
already pruned (PLAY_LOG_RETENTION_DAYS) cannot be recovered. Left as an explicit
operator decision rather than an implicit side effect of a migration.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b4e7c92f38'
down_revision = 'f9a3c7b1d240'
branch_labels = None
depends_on = None

# Postgres default naming: <table>_<column>_fkey
_DROPPED_FKS = (
    ('play_logs', 'play_logs_media_id_fkey'),
    ('play_logs', 'play_logs_playlist_id_fkey'),
    ('play_logs', 'play_logs_campaign_id_fkey'),
    # The rollup matters more: aggregate_play_logs swallows exceptions, so one violation
    # here silently stops aggregation fleet-wide and every report reads zero.
    ('play_log_hourly_rollups', 'play_log_hourly_rollups_campaign_id_fkey'),
    ('play_log_hourly_rollups', 'play_log_hourly_rollups_media_id_fkey'),
)

_ROLLUP_UNIQUE_INDEX = 'ix_play_log_hourly_rollups_unique'


def upgrade() -> None:
    connection = op.get_bind()

    # Attribute stored events to their playlist's campaign. Joins inside one statement so
    # this stays a single pass regardless of table size.
    connection.execute(sa.text("""
        UPDATE play_logs
        SET campaign_id = playlists.campaign_id
        FROM playlists
        WHERE play_logs.playlist_id = playlists.id
          AND play_logs.campaign_id IS NULL
          AND playlists.campaign_id IS NOT NULL
          AND play_logs.organization_id = playlists.organization_id
    """) if connection.dialect.name == 'postgresql' else sa.text("""
        UPDATE play_logs
        SET campaign_id = (
            SELECT p.campaign_id FROM playlists p
            WHERE p.id = play_logs.playlist_id
              AND p.organization_id = play_logs.organization_id
        )
        WHERE campaign_id IS NULL
          AND playlist_id IS NOT NULL
    """))

    if connection.dialect.name != 'postgresql':
        return

    for table, constraint in _DROPPED_FKS:
        op.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{constraint}"')

    # The rollup's unique index covers nullable campaign_id/media_id, and Postgres treats
    # NULLs as distinct -- so for real traffic (campaign_id was always NULL) the index
    # rejected nothing, and a concurrent or re-run aggregate_play_logs could insert a
    # second row for the same hour, double counting every SUM(total_plays).
    #
    # Expressed with COALESCE rather than NULLS NOT DISTINCT. The latter says exactly what
    # is meant, but it is PostgreSQL 15 and newer only, and this migration ran on anything
    # older with "syntax error at or near NULLS" -- which is every default Ubuntu 22.04
    # install (PG 14) and several managed services still on 13/14. The whole upgrade chain
    # stopped there, so the database could not be built at all; it only ever worked because
    # docker-compose happens to pin postgres:15-alpine.
    #
    # COALESCE(...,-1) is identical in effect and valid since 9.6. -1 is safe as the
    # sentinel: both columns hold positive primary keys.
    op.execute(f'DROP INDEX IF EXISTS {_ROLLUP_UNIQUE_INDEX}')
    op.execute(f"""
        CREATE UNIQUE INDEX {_ROLLUP_UNIQUE_INDEX}
        ON play_log_hourly_rollups (
            organization_id, COALESCE(campaign_id, -1), screen_id,
            COALESCE(media_id, -1), date_hour
        )
    """)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name != 'postgresql':
        return

    op.execute(f'DROP INDEX IF EXISTS {_ROLLUP_UNIQUE_INDEX}')
    op.execute(f"""
        CREATE UNIQUE INDEX {_ROLLUP_UNIQUE_INDEX}
        ON play_log_hourly_rollups (
            organization_id, campaign_id, screen_id, media_id, date_hour
        )
    """)
    op.create_foreign_key('play_logs_media_id_fkey', 'play_logs', 'content', ['media_id'], ['id'])
    op.create_foreign_key('play_logs_playlist_id_fkey', 'play_logs', 'playlists', ['playlist_id'], ['id'])
    op.create_foreign_key('play_logs_campaign_id_fkey', 'play_logs', 'campaigns', ['campaign_id'], ['id'])
    op.create_foreign_key('play_log_hourly_rollups_campaign_id_fkey', 'play_log_hourly_rollups', 'campaigns', ['campaign_id'], ['id'])
    op.create_foreign_key('play_log_hourly_rollups_media_id_fkey', 'play_log_hourly_rollups', 'content', ['media_id'], ['id'])
    # campaign_id backfill is intentionally not reverted: the values are correct, and
    # nulling them would put every campaign report back to zero.
