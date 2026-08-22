"""null-safe unique index on play_log_hourly_rollups

Revision ID: d3f6b21c8a04
Revises: c7e1a9d40b52
Create Date: 2026-08-22

`ix_play_log_hourly_rollups_unique` covered (organization_id, campaign_id, screen_id,
media_id, date_hour) as bare columns. campaign_id and media_id are both nullable, and
Postgres treats NULLs as distinct inside a unique index, so two rollup rows with the same
screen and hour but a NULL campaign did not conflict -- the index enforced nothing for
precisely the rows most likely to collide, namely plays from a playlist with no campaign.

Nothing has gone wrong yet: aggregate_play_logs matches with IS NOT DISTINCT FROM and arq
runs each cron tick once. But the constraint meant to catch a double-aggregation if either
of those ever changed was not actually a constraint, and inflated totals on a billing
report are not the place to discover that.

Indexing COALESCE(...,-1) makes NULLs collide as intended. -1 is unused by both columns:
they hold positive primary keys.

Any duplicate rows that already exist would block the new index, so they are merged first.
On a healthy database that step affects nothing.
"""
from alembic import op

revision = 'd3f6b21c8a04'
down_revision = 'c7e1a9d40b52'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fold any pre-existing duplicates into one row per logical key, summing the counters.
    # A no-op unless the old index really did let duplicates through.
    op.execute(
        """
        WITH merged AS (
            SELECT
                MIN(id) AS keep_id,
                organization_id,
                COALESCE(campaign_id, -1) AS campaign_key,
                screen_id,
                COALESCE(media_id, -1) AS media_key,
                date_hour,
                SUM(total_plays) AS total_plays,
                SUM(completed_plays) AS completed_plays,
                SUM(partial_plays) AS partial_plays,
                SUM(error_plays) AS error_plays,
                SUM(duration_ms) AS duration_ms,
                COUNT(*) AS row_count
            FROM play_log_hourly_rollups
            GROUP BY organization_id, COALESCE(campaign_id, -1), screen_id,
                     COALESCE(media_id, -1), date_hour
            HAVING COUNT(*) > 1
        )
        UPDATE play_log_hourly_rollups p
        SET total_plays = m.total_plays,
            completed_plays = m.completed_plays,
            partial_plays = m.partial_plays,
            error_plays = m.error_plays,
            duration_ms = m.duration_ms
        FROM merged m
        WHERE p.id = m.keep_id
        """
    )
    op.execute(
        """
        DELETE FROM play_log_hourly_rollups p
        USING (
            SELECT MIN(id) AS keep_id, organization_id,
                   COALESCE(campaign_id, -1) AS campaign_key, screen_id,
                   COALESCE(media_id, -1) AS media_key, date_hour
            FROM play_log_hourly_rollups
            GROUP BY organization_id, COALESCE(campaign_id, -1), screen_id,
                     COALESCE(media_id, -1), date_hour
            HAVING COUNT(*) > 1
        ) d
        WHERE p.organization_id = d.organization_id
          AND COALESCE(p.campaign_id, -1) = d.campaign_key
          AND p.screen_id = d.screen_id
          AND COALESCE(p.media_id, -1) = d.media_key
          AND p.date_hour = d.date_hour
          AND p.id <> d.keep_id
        """
    )

    op.drop_index('ix_play_log_hourly_rollups_unique', table_name='play_log_hourly_rollups')
    op.execute(
        """
        CREATE UNIQUE INDEX ix_play_log_hourly_rollups_unique
        ON play_log_hourly_rollups (
            organization_id,
            COALESCE(campaign_id, -1),
            screen_id,
            COALESCE(media_id, -1),
            date_hour
        )
        """
    )


def downgrade() -> None:
    op.drop_index('ix_play_log_hourly_rollups_unique', table_name='play_log_hourly_rollups')
    op.create_index(
        'ix_play_log_hourly_rollups_unique',
        'play_log_hourly_rollups',
        ['organization_id', 'campaign_id', 'screen_id', 'media_id', 'date_hour'],
        unique=True,
    )
