"""Super-admin role promotion, and the org/plan quota columns that were never migrated

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-08-30

Three things, all of which have to land together because the admin console reads all of
them:

1. `organizations.max_screens` and `organizations.max_ad_slots` were added to models.py
   and are read by the approvals router and enforced by the placements router -- but no
   migration ever created them. A database built by `alembic upgrade head` (rather than by
   create_all) is missing both, so `GET /api/approvals/tenants` and `POST /api/placements/`
   fail with UndefinedColumn. The head revision was already out of sync with the models.

2. `plans.max_ad_slots`, so a package can carry an ad-slot limit the same way it already
   carries a screen limit.

3. Promotes the four addresses that used to be hardcoded in `tenancy.SEED_SUPER_ADMINS`
   to a real `role='super_admin'`. That set is deleted in this release; without this step
   the platform operators would lose their access on deploy.
"""
from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


# Exactly the contents of the old tenancy.SEED_SUPER_ADMINS. Matched against email OR
# username, because that is how the old check behaved -- "admin" was never an address.
#
# Note the bare "admin": under the old code ANY account that registered that username
# silently gained cross-tenant read across every scope.query() call site. Promoting it
# once here preserves the existing operator account; from this revision on, the only way
# to mint a super admin is `python -m backend.seed_admin <name> --role super_admin`.
LEGACY_SUPER_ADMINS = (
    "juug22btech48491@gmail.com",
    "roshannandhu1100@gmail.com",
    "admin@olrac.com",
    "admin",
)


def upgrade() -> None:
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_screens INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS max_ad_slots INTEGER DEFAULT 0 NOT NULL")
    op.execute("ALTER TABLE plans ADD COLUMN IF NOT EXISTS max_ad_slots INTEGER DEFAULT 0 NOT NULL")

    # Same story as the two above: models.User has carried these three since Google
    # sign-in was added, and no migration ever created them. On a migrated Postgres every
    # query that touches the users table fails outright with
    # `UndefinedColumn: column users.google_sub does not exist` -- which is every
    # authenticated request, not just the Google ones, because SQLAlchemy selects all
    # mapped columns.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS picture VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider VARCHAR DEFAULT 'local' NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub ON users (google_sub)")

    users = sa.table(
        "users",
        sa.column("role", sa.String),
        sa.column("email", sa.String),
        sa.column("username", sa.String),
    )
    op.execute(
        users.update()
        .where(
            sa.or_(
                sa.func.lower(users.c.email).in_(LEGACY_SUPER_ADMINS),
                sa.func.lower(users.c.username).in_(LEGACY_SUPER_ADMINS),
            )
        )
        .values(role="super_admin")
    )


def downgrade() -> None:
    # The role is deliberately NOT reverted: there is no record of what each account was
    # before, and guessing "owner" could hand a platform operator a tenant role in an
    # organisation they do not belong to.
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "picture")
    op.drop_column("users", "google_sub")
    op.drop_column("plans", "max_ad_slots")
    op.drop_column("organizations", "max_ad_slots")
    op.drop_column("organizations", "max_screens")
