"""ad placements: selling an advert for a period across a set of places

Revision ID: d8b3e5c1f742
Revises: c4d9f1a7e820
Create Date: 2026-08-17

A placement records the deal (who bought it, when it runs, what they paid). Its targets
record where it runs and, critically, which playlist item each target created — that link
is what makes "take this ad off that one screen" an exact delete rather than a guess.
"""
from alembic import op
import sqlalchemy as sa

revision = 'd8b3e5c1f742'
down_revision = 'c4d9f1a7e820'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ad_placements',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_id', sa.Integer(), sa.ForeignKey('content.id', ondelete='CASCADE'), nullable=False),
        sa.Column('advertiser', sa.String(), nullable=False),
        sa.Column('price_paise', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('is_paid', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_ad_placements_organization_id', 'ad_placements', ['organization_id'])
    op.create_index('ix_ad_placements_content_id', 'ad_placements', ['content_id'])

    op.create_table(
        'ad_placement_targets',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('placement_id', sa.Integer(), sa.ForeignKey('ad_placements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('screen_id', sa.Integer(), sa.ForeignKey('screens.id', ondelete='CASCADE'), nullable=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('screen_groups.id', ondelete='CASCADE'), nullable=True),
        # SET NULL: deleting the item by hand on a screen page must not erase the record of
        # what was sold, it just means the booking is no longer placed there.
        sa.Column('playlist_item_id', sa.Integer(), sa.ForeignKey('playlist_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('(screen_id IS NOT NULL) <> (group_id IS NOT NULL)', name='ck_placement_target_exactly_one'),
    )
    op.create_index('ix_ad_placement_targets_placement_id', 'ad_placement_targets', ['placement_id'])
    op.create_index('ix_ad_placement_targets_screen_id', 'ad_placement_targets', ['screen_id'])
    op.create_index('ix_ad_placement_targets_group_id', 'ad_placement_targets', ['group_id'])


def downgrade() -> None:
    op.drop_table('ad_placement_targets')
    op.drop_table('ad_placements')
