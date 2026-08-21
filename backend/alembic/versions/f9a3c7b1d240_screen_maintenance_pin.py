"""per-screen maintenance pin

Revision ID: f9a3c7b1d240
Revises: e5c2a9d31b64
Create Date: 2026-08-18

Gates the player's on-TV maintenance screen, which is reached by a remote key sequence and
exposes the server URL. Backfilled with a distinct pin per existing screen rather than one
shared default, so recovering one pin does not open every screen in the fleet.
"""
import secrets

from alembic import op
import sqlalchemy as sa

revision = 'f9a3c7b1d240'
down_revision = 'e5c2a9d31b64'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('screens', sa.Column('maintenance_pin', sa.String(), nullable=True))

    connection = op.get_bind()
    screen_ids = [row[0] for row in connection.execute(sa.text("SELECT id FROM screens"))]
    for screen_id in screen_ids:
        connection.execute(
            sa.text("UPDATE screens SET maintenance_pin = :pin WHERE id = :id"),
            {"pin": f"{secrets.randbelow(10000):04d}", "id": screen_id},
        )

    # Batch mode so SQLite (dev) rebuilds the table instead of rejecting the ALTER.
    with op.batch_alter_table('screens') as batch_op:
        batch_op.alter_column(
            'maintenance_pin', existing_type=sa.String(), nullable=False
        )


def downgrade() -> None:
    op.drop_column('screens', 'maintenance_pin')
