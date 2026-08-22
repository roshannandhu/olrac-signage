import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from .. import models, rollout, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

logger = logging.getLogger(__name__)

router = APIRouter()

# An AppRelease is platform-wide: `current_app_version` falls back to the highest
# version_code in this table for *every* screen in *every* tenant. Publishing one is
# therefore not a tenant-level action -- a release created by one organisation's owner
# would install itself across the whole fleet, and on a device-owner TV it installs
# silently. Creation is restricted to `super_admin` for that reason.
#
# Reading stays open to any authenticated member: the dashboard's staged-rollout table
# needs the version list to label which build each of *its own* screens is pinned to.


@router.get("/", response_model=List[schemas.AppReleaseResponse])
def list_releases(scope: TenantScope = Depends(get_tenant_scope)):
    return (
        scope.db.query(models.AppRelease)
        .order_by(models.AppRelease.version_code.desc())
        .all()
    )


@router.post("/", response_model=schemas.AppReleaseResponse, status_code=201)
def create_release(
    data: schemas.AppReleaseCreate,
    scope: TenantScope = Depends(require_tenant_roles("super_admin")),
):
    release = models.AppRelease(
        version_code=data.version_code,
        version_name=data.version_name,
        apk_url=data.apk_url,
        sha256=data.sha256.lower(),
        mandatory=data.mandatory,
        rollout_state=data.rollout_state,
    )
    scope.db.add(release)
    try:
        scope.db.commit()
    except IntegrityError:
        # version_code is unique; re-publishing one would silently repoint every screen
        # already pinned to it at a different APK.
        scope.db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Version code {data.version_code} already exists",
        )
    scope.db.refresh(release)
    logger.info(
        "Release %s (%s) published by %s",
        release.version_code,
        release.version_name,
        scope.user.username,
    )
    return release


@router.patch("/{version_code}", response_model=schemas.AppReleaseResponse)
def promote_release(
    version_code: int,
    data: schemas.AppReleasePatch,
    scope: TenantScope = Depends(require_tenant_roles("super_admin")),
):
    """Move a build along the rollout ring: draft -> canary -> released.

    Promoting to "released" is the moment a build becomes live for every screen that has
    no explicit pin, so it carries the same authority as publishing one.
    """
    release = (
        scope.db.query(models.AppRelease)
        .filter(models.AppRelease.version_code == version_code)
        .first()
    )
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    if data.rollout_state == rollout.RELEASED and not release.sha256:
        # Legacy rows predate the mandatory digest. The player refuses to install an
        # unpinned APK, so promoting one fleet-wide would only produce 500 failed
        # installs; refusing here says why instead.
        raise HTTPException(
            status_code=422,
            detail="Release has no sha256 digest and cannot be promoted; re-publish it with one",
        )
    previous = release.rollout_state
    release.rollout_state = data.rollout_state
    scope.db.commit()
    scope.db.refresh(release)
    logger.info(
        "Release %s moved %s -> %s by %s",
        release.version_code,
        previous,
        release.rollout_state,
        scope.user.username,
    )
    return release
