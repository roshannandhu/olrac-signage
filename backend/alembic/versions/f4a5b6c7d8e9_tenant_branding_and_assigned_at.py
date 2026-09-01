"""Tenant branding for the client report, and the date each place was actually assigned

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-09-01

Two unrelated columns, one migration, because both are additive and neither is worth its
own deploy.

BRANDING. The campaign report is a document a tenant hands to their own advertiser, and it
was headed with `organizations.name` -- the workspace name someone typed at signup, often
"<person>'s Workspace". That is not a trading name. `brand_name` overrides it, `logo_url`
puts their mark in the masthead, `brand_color` tints the band. All nullable: a tenant that
sets none keeps exactly what they have today.

`logo_url` holds the same host-independent form as every other asset -- "s3://<key>" or
"/uploads/<path>" -- and is resolved on read. Storing an absolute URL is what previously
left every media row pointing at a stale localhost that no client could load.

ASSIGNED_AT. A booking's targets all inherited the booking's start date, so a screen added
on the 10th of a campaign that began on the 1st claimed nine days it was never on air. The
report divides a location's plays by its elapsed days, so that screen read as the worst
performer on the network rather than the newest.

Existing rows backfill to the booking's start, which is what they effectively meant, so no
report changes retrospectively.
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("brand_name", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("logo_url", sa.String(), nullable=True))
    op.add_column("organizations", sa.Column("brand_color", sa.String(length=9), nullable=True))

    # server_default so the NOT NULL holds for rows already in the table; the backfill below
    # then corrects it to something meaningful rather than "whenever this migration ran".
    op.add_column(
        "ad_placement_targets",
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute(
        """
        UPDATE ad_placement_targets t
        SET assigned_at = p.starts_at
        FROM ad_placements p
        WHERE p.id = t.placement_id
        """
    )


def downgrade() -> None:
    op.drop_column("ad_placement_targets", "assigned_at")
    op.drop_column("organizations", "brand_color")
    op.drop_column("organizations", "logo_url")
    op.drop_column("organizations", "brand_name")
