"""screen description, tags, fit, sync roles and operating hours

Revision ID: b7e2d84a1f30
Revises: a3f1c7d92b40
Create Date: 2026-08-16

Everything the screen Settings and Hours dialogs edit. These are operator-owned fields —
none of them are reported by the device — so they all default to something safe and the
heartbeat never touches them.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e2d84a1f30'
down_revision = 'a3f1c7d92b40'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('screens', sa.Column('description', sa.String(), nullable=True))
    op.add_column('screens', sa.Column('tags', sa.String(), nullable=True))
    op.add_column('screens', sa.Column('fit_mode', sa.String(), nullable=False, server_default='contain'))
    op.add_column('screens', sa.Column('sync_playback', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('screens', sa.Column('sync_role', sa.String(), nullable=False, server_default='leader'))
    op.add_column('screens', sa.Column('leader_screen_id', sa.Integer(), nullable=True))
    op.add_column('screens', sa.Column('operating_hours', sa.JSON(), nullable=True))
    op.add_column('screens', sa.Column('operating_mode', sa.String(), nullable=False, server_default='always'))
    # Self-reference: dropping a leader must not delete its followers, only unlink them.
    op.create_foreign_key(
        'fk_screens_leader_screen_id',
        'screens', 'screens',
        ['leader_screen_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_screens_leader_screen_id', 'screens', type_='foreignkey')
    for column in (
        'operating_mode',
        'operating_hours',
        'leader_screen_id',
        'sync_role',
        'sync_playback',
        'fit_mode',
        'tags',
        'description',
    ):
        op.drop_column('screens', column)
