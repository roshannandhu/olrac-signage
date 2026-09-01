"""How a tenant's own brand appears on the report they give their client.

The campaign report is not an internal screen -- it is a document handed to an advertiser
who is paying for it. It was headed with `organizations.name`, which is the workspace name
somebody typed at signup and is very often "<person>'s Workspace". That is not a trading
name to put on an invoice-shaped page.

Everything here is optional. A tenant that sets nothing gets exactly the report they get
today, with the workspace name in the masthead.
"""
import logging
import os
import pathlib
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from .. import media_storage, models, schemas
from ..media_urls import resolve_media_url, storage_prefix
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

logger = logging.getLogger(__name__)

router = APIRouter()

# Raster only, and no SVG. /uploads is served as StaticFiles from the API's own origin, and
# an SVG can carry a <script>; accepting one here would serve attacker-authored markup from
# the API's origin, which is the same reasoning as ALLOWED_UPLOAD_EXTENSIONS in content.py.
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# A masthead logo is a few hundred pixels tall. The cap is here because this endpoint is
# reachable by any editor and writes to the tenant's storage: without it, "logo upload" is
# an unmetered way to fill the bucket.
MAX_LOGO_BYTES = 2 * 1024 * 1024


def _organization(scope: TenantScope) -> models.Organization:
    org = scope.db.query(models.Organization).filter(
        models.Organization.id == scope.organization_id
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return org


def serialize(org: models.Organization) -> schemas.BrandingResponse:
    return schemas.BrandingResponse(
        brand_name=org.brand_name,
        brand_color=org.brand_color,
        logo_url=resolve_media_url(org.logo_url),
        # The fallback lives here rather than in the template, so the dashboard preview and
        # the PDF cannot disagree about what the client will actually see.
        effective_name=(org.brand_name or org.name),
    )


@router.get("/", response_model=schemas.BrandingResponse)
def get_branding(scope: TenantScope = Depends(get_tenant_scope)):
    return serialize(_organization(scope))


@router.put("/", response_model=schemas.BrandingResponse)
def update_branding(
    payload: schemas.BrandingUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    org = _organization(scope)
    fields = payload.model_dump(exclude_unset=True)
    if "brand_name" in fields:
        # Blanking it is meaningful: it restores the workspace-name fallback rather than
        # printing an empty masthead.
        org.brand_name = (fields["brand_name"] or "").strip() or None
    if "brand_color" in fields:
        org.brand_color = fields["brand_color"] or None
    scope.db.commit()
    scope.db.refresh(org)
    return serialize(org)


@router.post("/logo", response_model=schemas.BrandingResponse)
def upload_logo(
    file: UploadFile = File(...),
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Put the tenant's mark in their own storage folder.

    Through media_storage.store rather than a second boto3 call, so the logo follows
    whatever storage is configured -- R2 when it is, local disk when it is not -- and lands
    beside that tenant's media under the same prefix as everything else they own.
    """
    org = _organization(scope)

    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in LOGO_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Logo must be one of: {', '.join(sorted(LOGO_EXTENSIONS))}",
        )

    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Logo is {size} bytes; the limit is {MAX_LOGO_BYTES}.",
        )
    if not size:
        raise HTTPException(status_code=400, detail="That file is empty")

    previous = org.logo_url
    key = f"{storage_prefix(org)}/branding/{uuid.uuid4()}{extension}"

    # Staged through a temp file because media_storage.store takes a path -- it is the same
    # function the transcoder uses to put renditions away, and reusing it is what keeps
    # local and R2 on one code path.
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as staging:
        staging.write(file.file.read())
        staged = pathlib.Path(staging.name)
    try:
        org.logo_url = media_storage.store(staged, key, content_type=file.content_type)
    finally:
        staged.unlink(missing_ok=True)

    scope.db.commit()
    scope.db.refresh(org)

    # After the commit, and never fatal: an orphaned old logo costs a few kilobytes, while
    # deleting first would lose the current one if the new upload failed.
    if previous and previous != org.logo_url:
        try:
            media_storage.delete(previous)
        except Exception:  # noqa: BLE001 - the replacement already succeeded
            logger.warning("Could not remove the previous logo for org %s", org.id)

    return serialize(org)


@router.delete("/logo", response_model=schemas.BrandingResponse)
def remove_logo(scope: TenantScope = Depends(require_tenant_roles("owner", "editor"))):
    org = _organization(scope)
    previous = org.logo_url
    org.logo_url = None
    scope.db.commit()
    scope.db.refresh(org)
    if previous:
        try:
            media_storage.delete(previous)
        except Exception:  # noqa: BLE001
            logger.warning("Could not remove the logo object for org %s", org.id)
    return serialize(org)
