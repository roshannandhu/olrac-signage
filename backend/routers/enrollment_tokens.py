import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..tenancy import TenantScope, require_tenant_roles

router = APIRouter(prefix="/enrollment-tokens", tags=["enrollment-tokens"])


def _token_to_dict(t: models.EnrollmentToken, obscure: bool = False) -> dict:
    token_str = t.token
    if obscure and token_str:
        token_str = f"{token_str[:4]}...{token_str[-4:]}" if len(token_str) > 8 else "***"

    return {
        "id": t.id,
        "token": token_str,
        "description": t.description,
        "is_active": t.is_active,
        "expires_at": t.expires_at,
        "max_uses": t.max_uses,
        "use_count": t.use_count,
        "created_at": t.created_at,
        "organization_id": t.organization_id,
    }


@router.get("/")
def list_tokens(scope: TenantScope = Depends(require_tenant_roles("owner"))):
    tokens = scope.query(models.EnrollmentToken).all()
    return [_token_to_dict(t, obscure=True) for t in tokens]


@router.post("/", status_code=201)
def create_token(
    body: schemas.EnrollmentTokenCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    token_value = secrets.token_urlsafe(32)
    token = models.EnrollmentToken(
        organization_id=scope.organization_id,
        token=token_value,
        description=body.description,
        is_active=True,
        expires_at=body.expires_at,
        max_uses=body.max_uses,
    )
    scope.db.add(token)
    scope.db.commit()
    scope.db.refresh(token)
    return _token_to_dict(token)


@router.delete("/{token_id}", status_code=204)
def revoke_token(
    token_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    token = scope.query(models.EnrollmentToken).filter(
        models.EnrollmentToken.id == token_id
    ).first()
    if not token:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = False
    scope.db.commit()
