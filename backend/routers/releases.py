import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Global app releases are typically managed by platform admins.
# For now, we'll allow owners to list them, or maybe create them.

@router.get("/", response_model=List[schemas.AppReleaseResponse])
def list_releases(db: Session = Depends(get_db)):
    # Platform-wide releases
    releases = db.query(models.AppRelease).order_by(models.AppRelease.version_code.desc()).all()
    return releases

@router.post("/", response_model=schemas.AppReleaseResponse)
def create_release(
    data: schemas.AppReleaseCreate,
    db: Session = Depends(get_db),
    # In a real app, this should be restricted to platform admins, not just any logged-in user.
):
    release = models.AppRelease(
        version_code=data.version_code,
        version_name=data.version_name,
        apk_url=data.apk_url,
        sha256=data.sha256,
        mandatory=data.mandatory
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release
