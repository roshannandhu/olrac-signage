"""Platform-operator routes: tenants, packages, and the universal demo reel.

This replaces routers/approvals.py, which was mounted at /api/approvals and gated by a
local `_require_admin` that accepted `role in ("manager", "owner")` in addition to a
super admin. Every Google signup is created with role="owner", so that check made each
customer a platform administrator: able to enumerate every tenant and its owner's email
address, approve their own pending workspace, rewrite anyone's quota, and suspend a
competitor. Everything here now depends on `require_super_admin`.

Nothing in this module edits a tenant's own content. The drill-in routes are deliberately
read-only -- an operator needs to see what a workspace contains to support it, not to
change it.
"""
import logging
import os
import pathlib
import shutil
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from .. import database, models
from ..media_urls import resolve_media_url
from ..tenancy import TenantScope, require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_DEMO_VIDEO = "/uploads/f9863204-f997-4122-ac1b-a50157e3d905.mp4"
DEMO_VIDEO_KEY = "universal_demo_video_url"


# --------------------------------------------------------------------------- schemas


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    monthly_price_paise: int
    yearly_price_paise: int
    max_screens: int
    max_storage_bytes: int
    max_ad_slots: int
    is_active: bool


class PlanWrite(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9][a-z0-9-]*$")
    monthly_price_paise: int = Field(default=0, ge=0)
    yearly_price_paise: int = Field(default=0, ge=0)
    # 0 = unlimited throughout, matching Organization.max_screens / max_ad_slots.
    max_screens: int = Field(default=0, ge=0)
    max_storage_bytes: int = Field(default=10 * 1024 * 1024 * 1024, ge=0)
    max_ad_slots: int = Field(default=0, ge=0)
    is_active: bool = True


class PlanPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    monthly_price_paise: Optional[int] = Field(default=None, ge=0)
    yearly_price_paise: Optional[int] = Field(default=None, ge=0)
    max_screens: Optional[int] = Field(default=None, ge=0)
    max_storage_bytes: Optional[int] = Field(default=None, ge=0)
    max_ad_slots: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class TenantSummaryOut(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    created_at: str
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None
    plan_id: Optional[int] = None
    plan_name: Optional[str] = None
    screens_count: int = 0
    online_screens_count: int = 0
    max_screens: int = 0
    max_ad_slots: int = 0
    ad_slots_used: int = 0
    storage_used_bytes: int = 0
    storage_quota_bytes: int = 0
    rejection_reason: Optional[str] = None


class TenantScreenOut(BaseModel):
    id: int
    name: Optional[str] = None
    status: str
    last_seen: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    app_version: Optional[str] = None
    playback_state: str = "idle"


class TenantContentOut(BaseModel):
    id: int
    name: Optional[str] = None
    type: Optional[str] = None
    status: str
    file_size_bytes: int = 0
    uploaded_at: Optional[str] = None
    thumbnail: Optional[str] = None


class TenantUserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool


class ApprovalRequest(BaseModel):
    """Approve a workspace, optionally onto a package.

    `plan_id` is the normal path: the package carries the limits. The two overrides exist
    for the tenant that negotiated something different, and win over the package when set.
    """

    plan_id: Optional[int] = None
    max_screens: Optional[int] = Field(default=None, ge=0)
    max_ad_slots: Optional[int] = Field(default=None, ge=0)


class QuotaUpdateRequest(BaseModel):
    plan_id: Optional[int] = None
    max_screens: Optional[int] = Field(default=None, ge=0)
    max_ad_slots: Optional[int] = Field(default=None, ge=0)


class RejectionRequest(BaseModel):
    reason: Optional[str] = "Application could not be approved at this time."


class DemoVideoPayload(BaseModel):
    url: str
    description: Optional[str] = None


# --------------------------------------------------------------------------- helpers


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _owner_of(db: Session, org_id: int) -> Optional[models.User]:
    return (
        db.query(models.User)
        .filter(models.User.organization_id == org_id, models.User.role == "owner")
        .order_by(models.User.created_at)
        .first()
    )


def _summarise(db: Session, org: models.Organization) -> TenantSummaryOut:
    owner = _owner_of(db, org.id)
    # "waiting_pairing" rows are unclaimed registrations, not screens this tenant owns, so
    # they must not count against a quota the operator is about to size.
    screens_count = db.query(models.Screen).filter(
        models.Screen.organization_id == org.id,
        models.Screen.status != "waiting_pairing",
    ).count()
    online_count = db.query(models.Screen).filter(
        models.Screen.organization_id == org.id,
        models.Screen.status == "online",
    ).count()
    ads_used = db.query(models.AdPlacement).filter(
        models.AdPlacement.organization_id == org.id,
        models.AdPlacement.ends_at >= models.utcnow(),
    ).count()
    from sqlalchemy import func

    storage_used = db.query(
        func.coalesce(func.sum(models.Content.file_size_bytes), 0)
    ).filter(models.Content.organization_id == org.id).scalar() or 0

    return TenantSummaryOut(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status,
        created_at=_iso(org.created_at) or "",
        owner_email=owner.email if owner else None,
        owner_name=(owner.full_name or owner.username) if owner else None,
        plan_id=org.plan_id,
        plan_name=org.plan.name if org.plan else None,
        screens_count=screens_count,
        online_screens_count=online_count,
        max_screens=org.max_screens,
        max_ad_slots=org.max_ad_slots,
        ad_slots_used=ads_used,
        storage_used_bytes=int(storage_used),
        storage_quota_bytes=org.storage_quota_bytes,
        rejection_reason=org.rejection_reason,
    )


def _get_org(db: Session, org_id: int) -> models.Organization:
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _apply_plan(org: models.Organization, plan: models.Plan) -> None:
    """Copy a package's limits onto the tenant.

    Copied rather than read through the relationship on every check, because an operator
    can then raise one tenant's ceiling without editing the package everyone else is on --
    which is what Organization.max_screens / max_ad_slots exist for.
    """
    org.plan_id = plan.id
    org.max_screens = plan.max_screens
    org.max_ad_slots = plan.max_ad_slots
    org.storage_quota_bytes = plan.max_storage_bytes


# --------------------------------------------------------------------------- tenants


@router.get("/tenants", response_model=List[TenantSummaryOut])
def list_tenants(
    status: Optional[str] = None,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Every workspace on the platform, newest first. `?status=pending_approval` filters."""
    query = db.query(models.Organization)
    if status:
        query = query.filter(models.Organization.status == status)
    orgs = query.order_by(models.Organization.created_at.desc()).all()
    return [_summarise(db, org) for org in orgs]


@router.get("/tenants/{org_id}", response_model=TenantSummaryOut)
def get_tenant(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    return _summarise(db, _get_org(db, org_id))


@router.get("/tenants/{org_id}/screens", response_model=List[TenantScreenOut])
def get_tenant_screens(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    _get_org(db, org_id)
    screens = (
        db.query(models.Screen)
        .filter(models.Screen.organization_id == org_id)
        .order_by(models.Screen.name)
        .all()
    )
    return [
        TenantScreenOut(
            id=s.id,
            name=s.name,
            status=s.status or "offline",
            last_seen=_iso(s.last_seen),
            location=s.location,
            model=s.model,
            app_version=s.app_version,
            playback_state=s.playback_state or "idle",
        )
        for s in screens
    ]


@router.get("/tenants/{org_id}/content", response_model=List[TenantContentOut])
def get_tenant_content(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    _get_org(db, org_id)
    items = (
        db.query(models.Content)
        .filter(models.Content.organization_id == org_id)
        .order_by(models.Content.uploaded_at.desc())
        .limit(500)
        .all()
    )
    return [
        TenantContentOut(
            id=c.id,
            name=c.name,
            type=c.type,
            status=c.status,
            file_size_bytes=c.file_size_bytes or 0,
            uploaded_at=_iso(c.uploaded_at),
            thumbnail=resolve_media_url(c.thumbnail),
        )
        for c in items
    ]


@router.get("/tenants/{org_id}/users", response_model=List[TenantUserOut])
def get_tenant_users(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    _get_org(db, org_id)
    users = (
        db.query(models.User)
        .filter(models.User.organization_id == org_id)
        .order_by(models.User.created_at)
        .all()
    )
    return [
        TenantUserOut(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.post("/tenants/{org_id}/approve", response_model=TenantSummaryOut)
def approve_tenant(
    org_id: int,
    req: ApprovalRequest = ApprovalRequest(),
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Let a workspace in, on a package or on hand-set limits."""
    org = _get_org(db, org_id)

    if req.plan_id is not None:
        plan = db.query(models.Plan).filter(models.Plan.id == req.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Package not found")
        _apply_plan(org, plan)

    if req.max_screens is not None:
        org.max_screens = req.max_screens
    if req.max_ad_slots is not None:
        org.max_ad_slots = req.max_ad_slots

    org.status = "active"
    org.approved_at = models.utcnow()
    org.approved_by_user_id = scope.user.id
    org.rejection_reason = None
    db.commit()
    db.refresh(org)
    logger.info(
        "Org %s (ID %s) approved by %s: plan=%s screens=%s ads=%s",
        org.name, org.id, scope.user.username, org.plan_id, org.max_screens, org.max_ad_slots,
    )
    return _summarise(db, org)


@router.patch("/tenants/{org_id}/quota", response_model=TenantSummaryOut)
def update_tenant_quota(
    org_id: int,
    req: QuotaUpdateRequest,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Change a tenant's package or its individual limits, at any time."""
    org = _get_org(db, org_id)

    if req.plan_id is not None:
        plan = db.query(models.Plan).filter(models.Plan.id == req.plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Package not found")
        _apply_plan(org, plan)

    if req.max_screens is not None:
        org.max_screens = req.max_screens
    if req.max_ad_slots is not None:
        org.max_ad_slots = req.max_ad_slots

    db.commit()
    db.refresh(org)
    logger.info("Quota updated for org %s by %s: %s", org.name, scope.user.username, req.model_dump(exclude_none=True))
    return _summarise(db, org)


@router.post("/tenants/{org_id}/reject", response_model=TenantSummaryOut)
def reject_tenant(
    org_id: int,
    req: RejectionRequest = RejectionRequest(),
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    org = _get_org(db, org_id)
    if org.id == scope.user.organization_id:
        raise HTTPException(status_code=400, detail="Cannot reject your own organization.")
    org.status = "rejected"
    org.rejection_reason = req.reason
    db.commit()
    db.refresh(org)
    logger.info("Org %s (ID %s) rejected by %s", org.name, org.id, scope.user.username)
    return _summarise(db, org)


@router.post("/tenants/{org_id}/suspend", response_model=TenantSummaryOut)
def suspend_tenant(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Block a tenant. get_tenant_scope refuses every API call from them until reinstated."""
    org = _get_org(db, org_id)
    if org.id == scope.user.organization_id:
        raise HTTPException(status_code=400, detail="Cannot suspend your own organization.")
    org.status = "suspended"
    db.commit()
    db.refresh(org)
    logger.info("Org %s (ID %s) suspended by %s", org.name, org.id, scope.user.username)
    return _summarise(db, org)


@router.post("/tenants/{org_id}/reinstate", response_model=TenantSummaryOut)
def reinstate_tenant(
    org_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    org = _get_org(db, org_id)
    org.status = "active"
    org.rejection_reason = None
    if org.approved_at is None:
        org.approved_at = models.utcnow()
    db.commit()
    db.refresh(org)
    logger.info("Org %s (ID %s) reinstated by %s", org.name, org.id, scope.user.username)
    return _summarise(db, org)


# --------------------------------------------------------------------------- packages


@router.get("/plans", response_model=List[PlanOut])
def list_plans(
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Every package, active or not.

    /api/billing/plans is the tenant-facing view and shows only active ones; this is the
    operator's, which has to show a retired package so it can be re-activated.
    """
    return db.query(models.Plan).order_by(models.Plan.monthly_price_paise).all()


@router.post("/plans", response_model=PlanOut, status_code=201)
def create_plan(
    payload: PlanWrite,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    if db.query(models.Plan).filter(models.Plan.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail="A package with that slug already exists")
    plan = models.Plan(**payload.model_dump(), feature_flags_json="{}")
    db.add(plan)
    db.commit()
    db.refresh(plan)
    logger.info("Package %s created by %s", plan.slug, scope.user.username)
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan(
    plan_id: int,
    payload: PlanPatch,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Edit a package in place.

    The slug is deliberately not editable: /api/billing/checkout resolves the payment
    provider's plan id from an env var named after it (RAZORPAY_{SLUG}_{PERIOD}_PLAN_ID),
    so renaming a slug would silently break checkout for everyone on that package.
    """
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Package not found")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    logger.info("Package %s updated by %s", plan.slug, scope.user.username)
    return plan


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Retire a package.

    Deactivated, never deleted, when tenants are on it: organizations.plan_id and
    subscriptions.plan_id both point here, so a hard delete would either fail on the
    foreign key or orphan live workspaces.
    """
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Package not found")

    in_use = db.query(models.Organization).filter(models.Organization.plan_id == plan_id).count()
    if in_use:
        plan.is_active = False
        db.commit()
        return {
            "status": "deactivated",
            "detail": f"{in_use} workspace(s) are on this package, so it was retired rather than deleted.",
        }

    db.delete(plan)
    db.commit()
    logger.info("Package %s deleted by %s", plan.slug, scope.user.username)
    return {"status": "deleted"}


# --------------------------------------------------------------------------- demo reel


@router.get("/demo-video")
def get_universal_demo_video(db: Session = Depends(database.get_db)):
    """The reel a pending tenant's TVs play. Unauthenticated: sync_tv serves it to devices."""
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == DEMO_VIDEO_KEY).first()
    return {
        "url": setting.value if setting else DEFAULT_DEMO_VIDEO,
        "description": setting.description if setting else "Default Universal Demo Video",
    }


def _store_demo_video(db: Session, url: str, description: Optional[str]) -> models.SystemSetting:
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == DEMO_VIDEO_KEY).first()
    if not setting:
        setting = models.SystemSetting(key=DEMO_VIDEO_KEY, value=url, description=description or "Universal Demo Video")
        db.add(setting)
    else:
        setting.value = url
        if description:
            setting.description = description
    db.commit()
    return setting


@router.post("/demo-video")
def set_universal_demo_video(
    payload: DemoVideoPayload,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    setting = _store_demo_video(db, payload.url, payload.description)
    return {"status": "ok", "url": setting.value}


@router.post("/demo-video/upload")
async def upload_universal_demo_video(
    file: UploadFile = File(...),
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    base_uploads = os.path.join(pathlib.Path(__file__).parent.parent.parent.absolute(), "uploads", "demo")
    os.makedirs(base_uploads, exist_ok=True)

    # Extension taken from a fixed allow-list rather than from the upload's own filename,
    # which is attacker-controlled and lands under a directory served by StaticFiles.
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in {".mp4", ".webm", ".mov", ".m4v"}:
        raise HTTPException(status_code=400, detail="Demo reel must be an .mp4, .webm, .mov or .m4v file")

    saved_filename = f"demo_reel_{uuid.uuid4().hex[:8]}{extension}"
    with open(os.path.join(base_uploads, saved_filename), "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_url = f"/uploads/demo/{saved_filename}"
    resolved_url = resolve_media_url(relative_url) or relative_url
    _store_demo_video(db, resolved_url, f"Universal Demo Video ({file.filename})")

    logger.info("Universal demo reel updated by %s (%s)", scope.user.username, resolved_url)
    return {
        "status": "ok",
        "url": resolved_url,
        "filename": file.filename,
        "message": f"Universal demo reel '{file.filename}' uploaded and applied to all pending TV displays.",
    }


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="Role to assign: super_admin, owner, editor, viewer")


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    scope: TenantScope = Depends(require_super_admin),
    db: Session = Depends(database.get_db),
):
    """Promote or demote any user account to/from super_admin or tenant roles."""
    if payload.role not in ("super_admin", "owner", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role. Must be super_admin, owner, editor, or viewer.")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    logger.info("User %s (ID %s) role updated to %s by Super Admin %s", user.username, user.id, user.role, scope.user.username)
    return {
        "status": "ok",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "message": f"User '{user.username}' is now assigned role '{user.role}'.",
    }

