"""Add groups, scheduling, playlist versions, and user roles.

Revision ID: b71f3d902ac4
Revises: da011c770044
Create Date: 2026-08-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b71f3d902ac4"
down_revision: Union[str, None] = "da011c770044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screen_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("playlist_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_screen_groups_id"), "screen_groups", ["id"], unique=False)
    op.create_index(op.f("ix_screen_groups_name"), "screen_groups", ["name"], unique=True)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("role", sa.String(), server_default="viewer", nullable=False))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
        )

    with op.batch_alter_table("playlists") as batch_op:
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
        )

    with op.batch_alter_table("playlist_items") as batch_op:
        batch_op.add_column(sa.Column("start_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("end_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("screens") as batch_op:
        batch_op.add_column(sa.Column("group_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "assignment_updated_at",
                sa.DateTime(),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )
        batch_op.create_foreign_key(
            "fk_screens_group_id_screen_groups",
            "screen_groups",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("playlist_item_id", sa.Integer(), nullable=False),
        sa.Column("days_of_week", sa.String(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(["playlist_item_id"], ["playlist_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("playlist_item_id"),
    )
    op.create_index(op.f("ix_schedules_id"), "schedules", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_schedules_id"), table_name="schedules")
    op.drop_table("schedules")

    with op.batch_alter_table("screens") as batch_op:
        batch_op.drop_constraint("fk_screens_group_id_screen_groups", type_="foreignkey")
        batch_op.drop_column("assignment_updated_at")
        batch_op.drop_column("group_id")

    with op.batch_alter_table("playlist_items") as batch_op:
        batch_op.drop_column("end_at")
        batch_op.drop_column("start_at")

    with op.batch_alter_table("playlists") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("created_at")
        batch_op.drop_column("is_active")
        batch_op.drop_column("role")

    op.drop_index(op.f("ix_screen_groups_name"), table_name="screen_groups")
    op.drop_index(op.f("ix_screen_groups_id"), table_name="screen_groups")
    op.drop_table("screen_groups")
