from fastapi import APIRouter, Depends, HTTPException

from .. import models, schemas
from ..tenancy import TenantScope, require_tenant_roles
from .auth import get_password_hash

router = APIRouter()


@router.get("/", response_model=list[schemas.UserResponse])
def list_users(scope: TenantScope = Depends(require_tenant_roles("owner", writable=False))):
    return scope.query(models.User).order_by(models.User.created_at).all()


@router.post("/", response_model=schemas.UserResponse, status_code=201)
def create_user(payload: schemas.UserCreate, scope: TenantScope = Depends(require_tenant_roles("owner"))):
    username = payload.username.strip()
    if scope.db.query(models.User).filter(models.User.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    user = models.User(
        organization_id=scope.organization_id,
        username=username,
        hashed_password=get_password_hash(payload.password),
        role=payload.role,
        is_active=True,
    )
    scope.db.add(user)
    scope.db.commit()
    scope.db.refresh(user)
    return user


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: int, payload: schemas.UserUpdate, scope: TenantScope = Depends(require_tenant_roles("owner"))):
    user = scope.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is not None and user.role == "owner" and payload.role != "owner":
        owner_count = scope.query(models.User).filter(models.User.role == "owner", models.User.is_active.is_(True)).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="At least one active owner is required")
    if payload.is_active is False and user.role == "owner" and user.is_active:
        owner_count = scope.query(models.User).filter(models.User.role == "owner", models.User.is_active.is_(True)).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="At least one active owner is required")

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.hashed_password = get_password_hash(payload.password)

    scope.db.commit()
    scope.db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, scope: TenantScope = Depends(require_tenant_roles("owner"))):
    user = scope.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "owner":
        owner_count = scope.query(models.User).filter(models.User.role == "owner", models.User.is_active.is_(True)).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="At least one active owner is required")

    scope.db.delete(user)
    scope.db.commit()
    return {"status": "ok"}
