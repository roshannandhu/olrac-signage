"""The advertisers a tenant sells to.

A booking used to record its buyer as a free-text `advertiser` string, which could label a
row and do nothing else: the same customer spelled two ways became two customers, there was
no address to email a report to, and "everything we ran for this client" was unanswerable.

Tenant-scoped throughout. Two tenants may both sell to the same chain, and neither may see
the other's record of it.
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

router = APIRouter()

CODE_PATTERN = re.compile(r"^CLT(\d+)$")


def next_client_code(scope: TenantScope) -> str:
    """The next free CLT##### for this tenant.

    Derived from the codes already issued rather than from a count: a tenant who deletes a
    client would otherwise get a code that is still in use by another row, and the unique
    constraint would reject the insert with a message about nothing the operator did.

    Scoped per organisation, matching uq_clients_org_code -- two tenants both starting at
    CLT00001 is intended, not a collision.

    A code freed by a deletion is reused. Accepted rather than solved: not reusing needs a
    persistent per-tenant counter, and the cost of that is carrying a second source of
    truth for something an operator can override by passing client_code explicitly. The
    risk it leaves is an old invoice naming a code now held by a different client.
    """
    existing = scope.query(models.Client).with_entities(models.Client.client_code).all()
    highest = 0
    for (code,) in existing:
        match = CODE_PATTERN.match((code or "").strip().upper())
        if match:
            highest = max(highest, int(match.group(1)))
    return f"CLT{highest + 1:05d}"


@router.get("/", response_model=list[schemas.ClientResponse])
def list_clients(scope: TenantScope = Depends(get_tenant_scope)):
    return scope.query(models.Client).order_by(models.Client.name).all()


@router.post("/", response_model=schemas.ClientResponse, status_code=201)
def create_client(
    payload: schemas.ClientCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    code = (payload.client_code or "").strip().upper() or next_client_code(scope)

    # Checked here as well as by the constraint so the operator gets a sentence rather than
    # a 500 from a raised IntegrityError.
    clash = scope.query(models.Client).filter(
        func.upper(models.Client.client_code) == code
    ).first()
    if clash:
        raise HTTPException(status_code=409, detail=f"Client code {code} is already in use")

    client = models.Client(
        organization_id=scope.organization_id,
        name=payload.name.strip(),
        client_code=code,
        email=str(payload.email) if payload.email else None,
        phone=(payload.phone or "").strip() or None,
        notes=payload.notes,
    )
    scope.db.add(client)
    scope.db.commit()
    scope.db.refresh(client)
    return client


@router.get("/{client_id}", response_model=schemas.ClientResponse)
def get_client(client_id: int, scope: TenantScope = Depends(get_tenant_scope)):
    client = scope.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.ClientResponse)
def update_client(
    client_id: int,
    payload: schemas.ClientUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    client = scope.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    fields = payload.model_dump(exclude_unset=True)
    if "name" in fields and fields["name"]:
        client.name = fields["name"].strip()
        # `ad_placements.advertiser` is NOT NULL and is what the report falls back to, so it
        # is kept in step here. Leaving it stale would print the old company name on every
        # report for bookings sold before a rename.
        scope.db.query(models.AdPlacement).filter(
            models.AdPlacement.client_id == client.id
        ).update({"advertiser": client.name}, synchronize_session=False)
    if "email" in fields:
        client.email = str(fields["email"]) if fields["email"] else None
    if "phone" in fields:
        client.phone = (fields["phone"] or "").strip() or None
    if "notes" in fields:
        client.notes = fields["notes"]

    scope.db.commit()
    scope.db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Remove a client. Their bookings survive, still named by `advertiser`.

    The foreign key is ON DELETE SET NULL for exactly this: a client leaving must not erase
    the record of what they were sold, which is a billing history.
    """
    client = scope.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    scope.db.delete(client)
    scope.db.commit()
    return {"status": "deleted"}
