from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Query, Session

from . import database, models
from .routers.auth import get_current_user


TenantModel = TypeVar("TenantModel")


@dataclass(frozen=True)
class TenantScope:
    """The sole entry point for authenticated organization-scoped queries."""

    db: Session
    user: models.User

    @property
    def organization_id(self) -> int:
        if self.user.role == "super_admin":
            # For super_admin, we might need a way to specify target org, but if they are
            # acting on their own scope without one, they bypass org checks or use None.
            # However, typically a super_admin can't just inject None if a column is non-nullable.
            # In this context, if they need to act on a specific org, it should be passed explicitly.
            # For queries, if they use `scope.organization_id`, it will return their own org.
            pass
        if self.user.organization_id is None:
            raise HTTPException(status_code=403, detail="User is not assigned to an organization")
        return self.user.organization_id

    def query(self, model: type[TenantModel]) -> Query:
        organization_column = getattr(model, "organization_id", None)
        if organization_column is None:
            raise RuntimeError(f"{model.__name__} is not tenant scoped")
        if self.user.role == "super_admin":
            return self.db.query(model)
        return self.db.query(model).filter(organization_column == self.organization_id)

    def get(self, model: type[TenantModel], record_id: int) -> TenantModel | None:
        return self.query(model).filter(model.id == record_id).first()

    def is_read_only(self) -> bool:
        subscription = (
            self.db.query(models.Subscription)
            .filter(models.Subscription.organization_id == self.organization_id)
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
    return TenantScope(db=db, user=user)


def require_tenant_roles(*roles: str, writable: bool = True):
    def dependency(scope: TenantScope = Depends(get_tenant_scope)) -> TenantScope:
        if scope.user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        if writable and scope.is_read_only():
            raise HTTPException(
                status_code=403,
                detail="Subscription requires attention; dashboard changes are read-only until billing is restored",
            )
        return scope

    return dependency
