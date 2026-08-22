"""fleet alerts

Revision ID: e8c4d7b19f36
Revises: d3f6b21c8a04
Create Date: 2026-08-22

Alerts were computed in the browser, from a list the dashboard polled every thirty seconds
while a tab happened to be open. That makes them a report rather than an alarm: nothing
detected a screen dropping, so nothing could be sent anywhere, and an outage at midnight
was a red row waiting to be noticed in the morning.

Storing them lets the condition be detected server side, delivered to a phone, acknowledged
by whoever picked it up, and answered afterwards -- "when did that screen actually drop?"

No foreign keys on screen_id / content_id on purpose, matching play_logs: an alert outlives
the row it describes, and deleting the screen that failed must not delete the record that
it did.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e8c4d7b19f36'
down_revision = 'd3f6b21c8a04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=True),
        sa.Column('content_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('dedupe_key', sa.String(length=80), nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.Integer(), nullable=True),
        sa.Column('notified', sa.JSON(), nullable=False, server_default='[]'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alerts_organization_id', 'alerts', ['organization_id'])
    op.create_index('ix_alerts_kind', 'alerts', ['kind'])
    op.create_index('ix_alerts_screen_id', 'alerts', ['screen_id'])
    op.create_index('ix_alerts_content_id', 'alerts', ['content_id'])
    op.create_index('ix_alerts_raised_at', 'alerts', ['raised_at'])
    op.create_index('ix_alerts_resolved_at', 'alerts', ['resolved_at'])

    # Partial: the constraint holds only while an alert is open. A plain unique index would
    # mean a screen that goes offline, recovers, then goes offline again could never raise
    # a second alert -- last week's resolved row would block it forever.
    #
    # Enforced in the database rather than by the reconciler checking first, because that
    # check is a race the moment two workers sweep at the same time.
    op.create_index(
        'ix_alerts_open_unique',
        'alerts',
        ['organization_id', 'dedupe_key'],
        unique=True,
        postgresql_where=sa.text('resolved_at IS NULL'),
        sqlite_where=sa.text('resolved_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_alerts_open_unique', table_name='alerts')
    for name in (
        'ix_alerts_resolved_at', 'ix_alerts_raised_at', 'ix_alerts_content_id',
        'ix_alerts_screen_id', 'ix_alerts_kind', 'ix_alerts_organization_id',
    ):
        op.drop_index(name, table_name='alerts')
    op.drop_table('alerts')
