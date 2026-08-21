"""user profile fields (full_name, email)

Revision ID: b2c8f1a94e7d
Revises: a1b4e7c92f38
Create Date: 2026-08-19

Backs the account menu, which previously had only a username and a numeric
organization_id to show. Both columns are nullable: every existing account predates them,
and username remains the login identifier, so an unset email or name changes nothing.

email carries a unique index rather than a unique constraint so the many pre-existing NULL
rows stay legal -- Postgres treats NULLs as distinct in a unique index, which is exactly
what is wanted here (unlike the play_log rollup index, where it was a bug).
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c8f1a94e7d'
down_revision = 'a1b4e7c92f38'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(), nullable=True))
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_email', table_name='users')
    op.drop_column('users', 'email')
    op.drop_column('users', 'full_name')
