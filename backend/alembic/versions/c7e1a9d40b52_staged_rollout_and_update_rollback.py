"""staged rollout state and automatic update rollback

Revision ID: c7e1a9d40b52
Revises: b2c8f1a94e7d
Create Date: 2026-08-22

Two columns behind the fleet-operations promise that a bad build must not reach every TV.

`app_releases.rollout_state` gates the global fallback in `current_app_version`, which
hands the highest version_code to every screen that carries no explicit pin. While all
releases were eligible, creating one shipped it to the entire fleet at once and a canary
ring was impossible. Existing rows are backfilled to 'released' on purpose: they are
already live on real screens, and defaulting them to 'draft' would silently withdraw the
build the fleet is running. Only rows created from here on start as drafts.

`screens.update_failure_count` counts consecutive failed installs of the pinned target so
the pin can be dropped after three. Without it a screen re-downloaded an APK that could
never install on every heartbeat, indefinitely.
"""
from alembic import op
import sqlalchemy as sa

revision = 'c7e1a9d40b52'
down_revision = 'b2c8f1a94e7d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default rather than a bare default: existing rows need a value at ALTER time,
    # and the Python-side default only applies to objects this process creates.
    op.add_column(
        'app_releases',
        sa.Column('rollout_state', sa.String(), nullable=False, server_default='draft'),
    )
    # Anything already in the table is live by definition -- screens are running it.
    op.execute("UPDATE app_releases SET rollout_state = 'released'")
    op.create_index(
        'ix_app_releases_rollout_state', 'app_releases', ['rollout_state'], unique=False
    )
    op.create_check_constraint(
        'ck_app_releases_rollout_state',
        'app_releases',
        "rollout_state IN ('draft', 'canary', 'released')",
    )

    op.add_column(
        'screens',
        sa.Column('update_failure_count', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('screens', 'update_failure_count')
    op.drop_constraint('ck_app_releases_rollout_state', 'app_releases', type_='check')
    op.drop_index('ix_app_releases_rollout_state', table_name='app_releases')
    op.drop_column('app_releases', 'rollout_state')
