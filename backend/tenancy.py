from dataclasses import dataclass
from typing import TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Query, Session

from . import database, models
from .routers.auth import get_current_user


TenantModel = TypeVar("TenantModel")


def is_super_admin(user: models.User) -> bool:
    """The single source of truth for platform-operator status.

    This used to be `role == "super_admin" or email in SEED_SUPER_ADMINS`, with the seed
    set copy-pasted into four files that had already drifted apart: the frontend's copy
    omitted the operator's own address (locking them out of /admin), and auth.py's copy
    omitted it again (so signing up with it created a pending_approval workspace). Worse,
    the set was hardcoded, so revoking platform access meant a redeploy.

    Role is now the only signal. The accompanying migration promotes the four legacy
    addresses to role='super_admin' once, so nothing is lost.
    """
    return user.role == "super_admin"


# Statuses that suspend a tenant's access to their own workspace. "pending_approval" is a
# tenant that has not been let in yet; the other two are one that has been put out.
#
# Only pending_approval used to be checked here, so `suspended` and `rejected` passed
# straight through: the Super Admin's Suspend button changed a label in a table and
# nothing else. The org kept full read and write access to every endpoint.
BLOCKED_ORGANIZATION_STATUSES = {
    "pending_approval": (
        "Workspace is pending manager approval. Access is restricted until approved."
    ),
    "suspended": (
        "This workspace has been suspended. Contact your platform administrator."
    ),
    "rejected": (
        "This workspace registration was not approved. Contact your platform administrator."
    ),
}


@dataclass(frozen=True)
class TenantScope:
    """The sole entry point for authenticated organization-scoped queries."""

    db: Session
    user: models.User

    @property
    def organization_id(self) -> int:
        # A super_admin has an organisation of its own like any other account, and this
        # returns it. Cross-tenant reach is expressed in `query()` below, which drops the
        # organisation filter -- not here, where a None would flow into non-nullable
        # foreign keys on every create.
        if self.user.organization_id is None:
            raise HTTPException(status_code=403, detail="User is not assigned to an organization")
        return self.user.organization_id

    def query(self, model: type[TenantModel]) -> Query:
        organization_column = getattr(model, "organization_id", None)
        if organization_column is None:
            raise RuntimeError(f"{model.__name__} is not tenant scoped")
        if is_super_admin(self.user):
            return self.db.query(model)
        return self.db.query(model).filter(organization_column == self.organization_id)

    def get(self, model: type[TenantModel], record_id: int) -> TenantModel | None:
        return self.query(model).filter(model.id == record_id).first()

    def is_read_only(self) -> bool:
        # Read directly off the user rather than through self.organization_id, which
        # raises 403 for an account with no organisation -- from inside a permission
        # check, turning "you have no workspace" into an unexplained failure on every
        # write. No organisation means no subscription means nothing to restrict.
        organization_id = self.user.organization_id
        if organization_id is None:
            return False
        subscription = (
            self.db.query(models.Subscription)
            .filter(models.Subscription.organization_id == organization_id)
            .first()
        )
        if not subscription:
            return False
        if subscription.status in {"read_only", "cancelled", "completed"}:
            return True
        return (
            subscription.status == "grace"
            and subscription.grace_period_end is not None
            and subscription.grace_period_end <= models.utcnow()
        )


def get_tenant_scope(
    db: Session = Depends(database.get_db),
    user: models.User = Depends(get_current_user),
) -> TenantScope:
    if not is_super_admin(user):
        blocked = BLOCKED_ORGANIZATION_STATUSES.get(user.organization_status)
        if blocked:
            raise HTTPException(status_code=403, detail=blocked)
    return TenantScope(db=db, user=user)


def require_super_admin(
    scope: TenantScope = Depends(get_tenant_scope),
) -> TenantScope:
    """Platform-operator routes only.

    Every caller of this used to accept `role in ("manager", "owner")` as well. Since
    every Google signup is created with role="owner", that made every customer a platform
    administrator: able to list all tenants, read their owners' email addresses, approve
    their own workspace, rewrite anyone's quota and suspend a competitor.
    """
    if not is_super_admin(scope.user):
        raise HTTPException(
            status_code=403,
            detail="Only platform administrators can perform this action.",
        )
    return scope


def require_tenant_roles(*roles: str, writable: bool = True):
    def dependency(scope: TenantScope = Depends(get_tenant_scope)) -> TenantScope:
        if not is_super_admin(scope.user) and scope.user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if writable and scope.is_read_only():
            raise HTTPException(
                status_code=403,
                detail="Subscription requires attention; dashboard changes are read-only until billing is restored",
            )
        return scope

    return dependency
