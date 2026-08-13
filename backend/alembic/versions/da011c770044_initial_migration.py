"""Initial Migration

Revision ID: da011c770044
Revises: 
Create Date: 2026-06-08 21:04:15.577228
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da011c770044'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'playlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_playlists_id'), 'playlists', ['id'], unique=False)
    op.create_index(op.f('ix_playlists_name'), 'playlists', ['name'], unique=False)

    op.create_table(
        'content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=True),
        sa.Column('file_url', sa.String(), nullable=True),
        sa.Column('thumbnail', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('tags', sa.String(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_id'), 'content', ['id'], unique=False)

    op.create_table(
        'playlist_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('playlist_id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['content_id'], ['content.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_playlist_items_id'), 'playlist_items', ['id'], unique=False)

    op.create_table(
        'screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=True),
        sa.Column('pair_code', sa.String(), nullable=True),
        sa.Column('pair_code_expires_at', sa.DateTime(), nullable=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('orientation', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('device_version', sa.String(), nullable=True),
        sa.Column('storage_used', sa.String(), nullable=True),
        sa.Column('playlist_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['playlist_id'], ['playlists.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_screens_device_id'), 'screens', ['device_id'], unique=True)
    op.create_index(op.f('ix_screens_id'), 'screens', ['id'], unique=False)
    op.create_index(op.f('ix_screens_pair_code'), 'screens', ['pair_code'], unique=True)


def downgrade() -> None:
    op.drop_table('screens')
    op.drop_table('playlist_items')
    op.drop_table('content')
    op.drop_table('playlists')
    op.drop_table('users')
