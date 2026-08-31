import html
import json
import logging
import os
import random
import string
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Literal

import boto3
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..limiter import limiter
from .. import google_device
from ..media_selection import select_rendition
from . import playlists as playlists_router
from .. import rollout
from ..rotation import normalise as normalise_rotation, resolve_rotation
from ..maps_link import MapsLinkError, parse as parse_maps_link
from ..media_urls import is_s3_enabled, media_base_url, resolve_media_url
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)

s3_client = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "auto"),
)


def public_base_url(request: Request | None = None) -> str:
    """The address a phone or a TV can actually reach this API on."""
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured and not ("localhost" in configured or "127.0.0.1" in configured):
        return configured

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if render_url:
        return render_url

    if request is not None:
        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
        scheme = forwarded_proto or request.url.scheme or "http"
        host = request.headers.get("host") or request.url.netloc
        if host and not ("127.0.0.1" in host or "localhost" in host):
            return f"{scheme}://{host}"

    return "https://olrac-signage-32lh.onrender.com"


def generate_pair_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _release_response(release: models.AppRelease) -> schemas.AppVersionResponse:
    # sha256 belongs in this payload. Without it the device has nothing to verify the
    # downloaded APK against, so UpdateManager's integrity check silently no-ops and a
    # device-owner TV installs whatever bytes arrived. It was omitted here while being
    # stored on the row, which made the whole checksum path dead code.
    return schemas.AppVersionResponse(
        version_code=release.version_code,
        version_name=release.version_name,
        apk_url=release.apk_url,
        sha256=release.sha256,
        mandatory=release.mandatory,
    )


def current_app_version(db: Session, target_version_code: int = None) -> schemas.AppVersionResponse:
    if target_version_code:
        release = db.query(models.AppRelease).filter(models.AppRelease.version_code == target_version_code).first()
        if release:
            return _release_response(release)

    # Fallback to the latest *promoted* release. A draft or canary build is deliberately
    # invisible here -- it reaches a screen only through an explicit target_version_code,
    # which is what keeps a 5-TV ring from being the whole fleet.
    release = (
        rollout.eligible_for_fallback(db.query(models.AppRelease))
        .order_by(models.AppRelease.version_code.desc())
        .first()
    )
    if release:
        return _release_response(release)

    return schemas.AppVersionResponse(
        version_code=int(os.getenv("PLAYER_VERSION_CODE", "1")),
        version_name=os.getenv("PLAYER_VERSION_NAME", "1.0"),
        apk_url=os.getenv("PLAYER_APK_URL") or None,
        sha256=os.getenv("PLAYER_APK_SHA256") or None,
        mandatory=os.getenv("PLAYER_UPDATE_MANDATORY", "false").lower() == "true",
    )


def player_sync_interval_seconds() -> int:
    try:
        configured = int(os.getenv("PLAYER_SYNC_INTERVAL_SECONDS", "60"))
    except ValueError:
        configured = 60
    return max(15, min(configured, 3600))


def screen_offline_after_seconds() -> int:
    try:
        configured = int(os.getenv("SCREEN_OFFLINE_AFTER_SECONDS", "150"))
    except ValueError:
        configured = 150
    return max(60, min(configured, 3600))


# One-shot commands for a screen, held in Redis until the device's next sync or heartbeat.
#
# This was a module-level dict. A dict lives in one process, and the API runs behind more
# than one: docker-compose scales it, Render restarts it, and uvicorn can be given
# workers. A command queued on worker A was invisible to worker B, so "Bring to front"
# reached the TV roughly one time in N and looked like a flaky device. The dict was also
# never pruned, so entries for deleted screens survived for the life of the process.
#
# Redis is already a hard dependency of this system (uploads, live push and every cron job
# stop without it), and both readers below already consulted this same key as a second
# source -- so this deletes a code path rather than adding one. SETEX gives the TTL for
# free, which is what makes an undelivered command expire instead of accumulating.
def _command_key(device_id: str) -> str:
    return f"screen_cmd:{device_id}"


async def queue_device_command(device_id: str, command: str, ttl_seconds: int = 300) -> bool:
    """Queue a one-shot command. Returns whether it was actually stored."""
    if not device_id:
        return False
    try:
        await database.get_redis().setex(_command_key(device_id), ttl_seconds, command)
        return True
    except Exception as exc:  # noqa: BLE001 - Redis down must not fail the operator's request
        logger.warning("Could not queue command %r for device %s: %s", command, device_id, exc)
        return False


async def pop_device_command(device_id: str) -> str | None:
    """Take the pending command for this device, if any. Reading it consumes it."""
    if not device_id:
        return None
    try:
        redis = database.get_redis()
        value = await redis.get(_command_key(device_id))
        if value is None:
            return None
        await redis.delete(_command_key(device_id))
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)
    except Exception as exc:  # noqa: BLE001
        # Logged rather than swallowed: silently returning None here is indistinguishable
        # from "no command was queued", which is what made the old TTL-expiry path so hard
        # to diagnose -- the operator saw the button do nothing and no trace anywhere.
        logger.warning("Could not read pending command for device %s: %s", device_id, exc)
        return None


# A freshly paired screen has to be told its own credential, and the pair-code flow gives
# it no other chance: /pair is called by an operator at the DASHBOARD, so its response
# never reaches the TV. The device polls /register while it waits to be claimed, so the
# secret is parked here and handed over on the first poll after pairing.
#
# Redis rather than a column, for the same reason the row only ever stores a hash: this is
# short-lived plaintext. The key is deleted as it is read, so a second caller racing for
# the same device_id gets nothing, and the TTL matches the pairing code's own five minutes.
def _pending_secret_key(device_id: str) -> str:
    return f"screen_pending_secret:{device_id}"


async def park_device_secret(device_id: str, secret: str, ttl_seconds: int = 300) -> None:
    if not device_id:
        return
    try:
        await database.get_redis().setex(_pending_secret_key(device_id), ttl_seconds, secret)
    except Exception as exc:  # noqa: BLE001 - the screen falls back to the legacy path
        logger.warning("Could not park device secret for %s: %s", device_id, exc)


async def collect_device_secret(device_id: str) -> str | None:
    """Take the credential waiting for this device, if any. Reading it consumes it."""
    if not device_id:
        return None
    try:
        redis = database.get_redis()
        value = await redis.get(_pending_secret_key(device_id))
        if value is None:
            return None
        await redis.delete(_pending_secret_key(device_id))
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read pending device secret for %s: %s", device_id, exc)
        return None


def legacy_device_auth_allowed() -> bool:
    """Whether a screen holding no device secret may still call the device endpoints.

    Device authentication was effectively optional: this function only demanded a token
    when `device_secret_hash` was set, and only /enroll ever set it. Every screen
    provisioned by pair code or TV sign-in therefore authenticated with nothing but its
    device id -- which is guessable, is echoed back by /register, and grants heartbeat,
    the full playlist, the maintenance pin and play-log injection.

    Closing it outright would brick every screen already in the field, so /pair and
    /sign-in now issue a secret like /enroll always has, and this flag keeps the old path
    open while the fleet rotates. Flip it to false once no screen is logging the warning
    below.
    """
    return os.getenv("ALLOW_LEGACY_DEVICE_AUTH", "true").strip().lower() in {"1", "true", "yes"}


def verify_device_auth(device_id: str, credentials: HTTPAuthorizationCredentials | None, db: Session) -> models.Screen:
    # deleted_at is checked here, not only in the dashboard's scope: this is the single
    # door every device endpoint comes through, so an archived screen loses sync,
    # heartbeat, play-log upload and its playlist in one place. The 404 is what the
    # player reads as "you were removed" and resets on.
    screen = (
        db.query(models.Screen)
        .filter(models.Screen.device_id == device_id, models.Screen.deleted_at.is_(None))
        .first()
    )
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if not credentials:
        # The staging gate, and it has to key off "no credential was presented" rather than
        # "this screen has no secret". /pair and /sign-in now issue a secret, but a player
        # built before this release neither stores nor sends one -- so keying off the hash
        # would lock out every TV already in the field the moment it re-paired, which is
        # the one failure mode this staging exists to avoid.
        if not legacy_device_auth_allowed():
            raise HTTPException(status_code=401, detail="Authentication required")
        # Logged on every call on purpose: this is the metric that says whether the fleet
        # has finished rotating and ALLOW_LEGACY_DEVICE_AUTH can be turned off.
        logger.warning(
            "Screen %s (device %s) authenticated with no credential (legacy path)",
            screen.id, device_id,
        )
        # Transient marker, not a column. Callers use it to decide what this request is
        # allowed to see -- see maintenance_pin in sync_tv.
        screen.authenticated = False
        return screen

    # A credential WAS presented, so it is verified strictly whether or not this screen is
    # known to have one. A bad token is always an error, never a silent downgrade.
    try:
        from .auth import ALGORITHM, get_secret_key
        from jose import jwt, JWTError
        payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub != f"device:{device_id}":
            raise HTTPException(status_code=401, detail="Token device mismatch")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Revocation was a no-op without this. DELETE /{screen_id}/device-secret clears the
    # hash, which stops /auth issuing NEW tokens -- but a token already in an attacker's
    # hands stayed valid for its full hour, because nothing here ever looked at the
    # database. An owner revoking a stolen credential got no answer for an hour.
    if screen.device_secret_hash is None:
        raise HTTPException(status_code=401, detail="Device credential has been revoked")

    screen.authenticated = True
    return screen


def issue_device_secret(screen: models.Screen) -> str:
    """Give this screen a credential of its own and return the plaintext once.

    /pair and /sign-in used to bind a screen and hand it nothing, which is what left
    device authentication optional for most of the fleet. Only the hash is stored, so the
    caller has exactly one chance to pass the secret to the device.
    """
    import secrets as _secrets
    from .auth import get_password_hash

    device_secret = _secrets.token_hex(32)
    screen.device_secret_hash = get_password_hash(device_secret)
    return device_secret


@router.get("/auth-methods")
def auth_methods():
    """Which sign-in routes this deployment actually offers.

    google_device.is_configured() existed from the start and was read in exactly one
    place -- to answer /google/start with a 503. Nothing ever told the TV, so the player
    always drew a "Sign in with Google" button, and on a deployment with no Google
    credentials pressing it could only ever produce an error. The intent to gate it was
    written down in google_device's docstring and never implemented; this is that missing
    half.

    Unauthenticated on purpose: it is read by a TV that has no credential yet, and it
    discloses nothing but which buttons to draw.
    """
    return {
        # The real answer, not a hardcoded True. With no Google credentials this route can
        # only ever answer /google/start with a 503, so the player drew a button whose
        # single outcome was an error -- and, worse, on the dev path it bound the screen to
        # an arbitrary organisation (see google_device_poll).
        "google": google_device.is_configured() or google_device.is_web_configured(),
        # Always available. Listed rather than assumed so the player renders from one
        # answer instead of hard-coding two of the three.
        "password": True,
        "pair_code": True,
    }


def presents_valid_device_token(device_id: str, credentials: HTTPAuthorizationCredentials | None) -> bool:
    """Whether this caller already holds a working credential for this screen."""
    if not credentials:
        return False
    try:
        from jose import JWTError, jwt

        from .auth import ALGORITHM, get_secret_key

        payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
        return payload.get("sub") == f"device:{device_id}"
    except Exception:  # noqa: BLE001 - expired or malformed is simply "no"
        return False


@router.post("/register", response_model=schemas.RegisterResponse)
# Unauthenticated, and it both creates rows and can hand back a credential, so it needs a
# ceiling. Sized like /auth for the same reason: a site coming back after a power cut
# re-registers every panel at once through one public IP.
@limiter.limit("120/minute")
async def register_tv(
    request: Request,
    req: schemas.RegisterRequest,
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    # Both lookups exclude archived rows, so a panel whose screen was removed comes back
    # as a genuinely new one and shows a fresh pairing code. Without this the operator
    # deletes a TV, the TV re-registers, and the row they just removed reappears.
    # 1. Match by device_id
    db_screen = (
        db.query(models.Screen)
        .filter(models.Screen.device_id == req.device_id, models.Screen.deleted_at.is_(None))
        .first()
    )

    # 2. Match by installation_id if device_id didn't match (e.g. after reinstall/reset)
    if not db_screen and req.installation_id:
        db_screen = (
            db.query(models.Screen)
            .filter(
                models.Screen.installation_id == req.installation_id,
                models.Screen.deleted_at.is_(None),
            )
            .order_by(models.Screen.last_seen.desc().nullslast(), models.Screen.id.desc())
            .first()
        )
        if db_screen:
            logger.info(
                "Restoring screen %s (Name: %s, Org: %s) for installation %s (reclaimed device_id %s -> %s)",
                db_screen.id, db_screen.name, db_screen.organization_id, req.installation_id, db_screen.device_id, req.device_id
            )
            db_screen.device_id = req.device_id

    # 3. If screen is already paired / configured, keep it active and update telemetry
    if db_screen:
        # Captured BEFORE the overwrite below, because it is the proof the re-issue path
        # checks against and assigning first would make every caller match itself.
        known_installation_id = db_screen.installation_id
        if req.installation_id:
            db_screen.installation_id = req.installation_id
        if req.device_model:
            db_screen.model = req.device_model
        db_screen.last_seen = models.utcnow()
        if db_screen.status != "waiting_pairing":
            # The screen is claimed and is coming back. Two ways it may need a credential:
            # one was parked for it when an operator redeemed its pairing code, or it lost
            # the one it had.
            issued = await collect_device_secret(db_screen.device_id)

            if issued is None and not presents_valid_device_token(req.device_id, credentials):
                # Reinstalling the app, or clearing its data, wipes SharedPreferences --
                # including the device secret -- while device_id survives, because it is
                # derived from ANDROID_ID rather than stored. So a returning screen is
                # recognised but can no longer authenticate, and without re-issuing here it
                # would be stuck on the legacy path for good: the moment
                # ALLOW_LEGACY_DEVICE_AUTH is turned off, every reinstalled TV goes dark
                # and needs a site visit.
                #
                # This used to re-issue on possession of the device id alone, reasoning that
                # every other unauthenticated device route already accepts that much. It does
                # not hold: those routes only ever let a caller ACT as the screen while the
                # legacy path is open, whereas this one mints a durable credential and
                # overwrites the stored hash -- so it both handed the fleet to anyone who
                # read a device id off the dashboard or a log line, and locked the real panel
                # out at the same time. It also survived ALLOW_LEGACY_DEVICE_AUTH=false, which
                # left that flag with no end state: the migration it stages could never
                # actually close.
                #
                # The installation id is the hardware identity (serial, else ANDROID_ID), so
                # a genuinely reinstalled panel always presents the one already on file while
                # a remote caller holding only a device id cannot. That is the proof now
                # required.
                recognised = (
                    req.installation_id is not None
                    and known_installation_id is not None
                    and req.installation_id == known_installation_id
                )
                if recognised:
                    issued = issue_device_secret(db_screen)
                    logger.info(
                        "Re-issued device credential to screen %s (device %s) after reinstall",
                        db_screen.id, db_screen.device_id,
                    )
                elif known_installation_id is None and legacy_device_auth_allowed():
                    # A screen enrolled before installation_id was recorded has no hardware
                    # identity to match, so during the rollout it keeps the old behaviour and
                    # backfills one. Tied to the legacy flag on purpose: turning that off is
                    # what finally closes this branch, which is what makes the flag mean
                    # something.
                    issued = issue_device_secret(db_screen)
                    logger.warning(
                        "Re-issued device credential to screen %s (device %s) with no stored "
                        "installation id (legacy path)",
                        db_screen.id, db_screen.device_id,
                    )
                else:
                    # Not fatal: the screen still registers and still plays on the legacy
                    # path if it is open. It simply is not handed a new credential.
                    logger.warning(
                        "Refused to re-issue a device credential for screen %s (device %s): "
                        "installation id did not match",
                        db_screen.id, db_screen.device_id,
                    )

            db.commit()
            db.refresh(db_screen)
            response = schemas.RegisterResponse.model_validate(db_screen)
            response.device_secret = issued
            return response
    else:
        db_screen = models.Screen(
            device_id=req.device_id,
            installation_id=req.installation_id,
            status="waiting_pairing"
        )
        db.add(db_screen)

    code = generate_pair_code()
    while db.query(models.Screen).filter(models.Screen.pair_code == code).first():
        code = generate_pair_code()
    db_screen.pair_code = code
    db_screen.pair_code_expires_at = models.utcnow() + timedelta(minutes=5)
    db.commit()
    db.refresh(db_screen)
    return db_screen


def ensure_screen_quota(db: Session, organization_id: int, action: str) -> None:
    """Reject the caller when the organisation is already at its screen limit.

    Two limits are checked in order:
    1. Per-org admin quota (org.max_screens > 0 → hard limit set by Super Admin).
    2. Plan-level limit (plan.max_screens) as a secondary fallback.

    Every path that binds a new screen to an organisation has to call this, or that path
    becomes a quota bypass: unlimited screens on a limited plan. An organisation with no
    plan and no admin quota is deliberately unbounded (0 = unlimited).
    """
    organization = db.query(models.Organization).filter(
        models.Organization.id == organization_id
    ).one()

    # Archived screens do not occupy a slot -- removing a TV has to actually free the
    # quota it was using, or the operator deletes one and still cannot add another.
    screen_count = db.query(models.Screen).filter(
        models.Screen.deleted_at.is_(None),
        models.Screen.organization_id == organization_id,
        models.Screen.status != "waiting_pairing",
    ).count()

    # 1. Admin-set per-org quota takes priority (0 = unlimited)
    if organization.max_screens and organization.max_screens > 0:
        if screen_count >= organization.max_screens:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"TV screen quota reached ({screen_count}/{organization.max_screens}). "
                    f"Contact your platform administrator to increase your screen limit."
                ),
            )
        return  # quota is set and not exceeded — no need to check plan

    # 2. Fall back to plan-level limit
    plan = db.query(models.Plan).filter(models.Plan.id == organization.plan_id).first()
    if not plan:
        return  # no plan, no quota → unlimited
    if screen_count >= plan.max_screens:
        raise HTTPException(
            status_code=409,
            detail=f"Screen limit reached ({plan.max_screens} on {plan.name}). Upgrade your plan to {action}.",
        )


@router.post("/pair", response_model=schemas.ScreenResponse)
async def pair_screen(
    req: schemas.PairRequest,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    db_screen = scope.db.query(models.Screen).filter(models.Screen.pair_code == req.pair_code).first()
    if not db_screen:
        raise HTTPException(status_code=404, detail="Invalid pairing code")
    if db_screen.organization_id not in (None, scope.organization_id):
        raise HTTPException(status_code=404, detail="Invalid pairing code")
    if db_screen.status != "waiting_pairing":
        raise HTTPException(status_code=400, detail="Screen already paired")
    if db_screen.pair_code_expires_at and db_screen.pair_code_expires_at < models.utcnow():
        raise HTTPException(status_code=400, detail="Pairing code expired")

    # Anti-duplicate hardware check: If the same physical TV was previously paired in this organization,
    # reclaim the existing screen record instead of creating a duplicate ghost screen.
    existing_screen = None
    if db_screen.installation_id:
        existing_screen = (
            scope.db.query(models.Screen)
            .filter(
                models.Screen.installation_id == db_screen.installation_id,
                models.Screen.organization_id == scope.organization_id,
                models.Screen.id != db_screen.id,
            )
            .first()
        )

    if existing_screen:
        logger.info(
            "Reclaiming existing screen %s (%s) on pairing reinstalled hardware (installation_id: %s, new device_id: %s)",
            existing_screen.id, existing_screen.name, db_screen.installation_id, db_screen.device_id
        )
        existing_screen.device_id = db_screen.device_id
        if db_screen.model:
            existing_screen.model = db_screen.model
        if db_screen.manufacturer:
            existing_screen.manufacturer = db_screen.manufacturer
        existing_screen.status = "online"
        existing_screen.last_seen = models.utcnow()
        existing_screen.pair_code = None
        existing_screen.pair_code_expires_at = None
        existing_screen.assignment_updated_at = models.utcnow()

        device_secret = issue_device_secret(existing_screen)

        # Remove the transient waiting_pairing placeholder
        scope.db.delete(db_screen)
        scope.db.commit()
        scope.db.refresh(existing_screen)
        # Parked for the TV to collect on its next /register poll; this response goes to
        # the operator's dashboard, not to the screen.
        await park_device_secret(existing_screen.device_id, device_secret)
        response = schemas.ScreenResponse.model_validate(existing_screen)
        response.device_secret = device_secret
        return response

    ensure_screen_quota(scope.db, scope.organization_id, "pair another screen")

    db_screen.status = "online"
    db_screen.last_seen = models.utcnow()
    db_screen.organization_id = scope.organization_id
    db_screen.approved_at = models.utcnow()
    if not db_screen.name or db_screen.name.startswith("Screen "):
        if db_screen.model:
            m = (db_screen.manufacturer or "").strip()
            mod = db_screen.model.strip()
            db_screen.name = f"{m} {mod}".strip() if m and not mod.lower().startswith(m.lower()) else mod
        else:
            db_screen.name = f"Screen {db_screen.pair_code}"
    db_screen.pair_code = None
    db_screen.pair_code_expires_at = None
    db_screen.assignment_updated_at = models.utcnow()
    device_secret = issue_device_secret(db_screen)
    scope.db.commit()
    scope.db.refresh(db_screen)
    await park_device_secret(db_screen.device_id, device_secret)
    response = schemas.ScreenResponse.model_validate(db_screen)
    response.device_secret = device_secret
    return response


def bind_screen_to_org(
    db: Session,
    *,
    device_id: str,
    user: models.User,
    name: str | None,
    conflict_error: HTTPException,
    how: str,
    installation_id: str | None = None,
    model: str | None = None,
    manufacturer: str | None = None,
) -> models.Screen:
    """Claim `device_id` or `installation_id` for `user`'s organisation, auto-reclaiming existing hardware."""
    if user.role not in ("owner", "editor", "super_admin"):
        raise HTTPException(status_code=403, detail="This account cannot add screens")
    if not user.organization_id:
        raise HTTPException(status_code=403, detail="This account has no workspace")

    # Anti-duplicate hardware search:
    # 1. Match by persistent installation_id (survives app reinstalls)
    # 2. Or match by device_id
    screen = None
    if installation_id:
        screen = db.query(models.Screen).filter(
            (models.Screen.installation_id == installation_id) &
            (models.Screen.organization_id == user.organization_id)
        ).first()

    if not screen:
        screen = db.query(models.Screen).filter(models.Screen.device_id == device_id, models.Screen.deleted_at.is_(None)).first()

    # If an existing screen with installation_id was found, clean up any transient placeholder holding device_id
    if screen and screen.device_id != device_id:
        temp_screen = db.query(models.Screen).filter(
            models.Screen.device_id == device_id,
            models.Screen.id != screen.id
        ).first()
        if temp_screen:
            db.delete(temp_screen)
            db.flush()

    if screen and screen.organization_id not in (None, user.organization_id):
        logger.warning(
            "Rejected cross-tenant claim for device %s (installation %s): owned by org %s, user belongs to org %s",
            device_id, installation_id, screen.organization_id, user.organization_id,
        )
        raise conflict_error

    # A screen that is new or still waiting to be paired is not yet counted against the
    # plan. Re-claiming a device this organisation already owns is not a new screen.
    if not screen or screen.status == "waiting_pairing":
        ensure_screen_quota(db, user.organization_id, "add another screen")

    if not screen:
        screen = models.Screen(device_id=device_id)
        db.add(screen)

    screen.device_id = device_id
    if installation_id:
        screen.installation_id = installation_id
    if model:
        screen.model = model
    if manufacturer:
        screen.manufacturer = manufacturer

    screen.organization_id = user.organization_id
    screen.approved_at = models.utcnow()
    screen.status = "online"
    screen.last_seen = models.utcnow()

    # Hardware Model based auto-naming
    detected_name = None
    if model:
        m = (manufacturer or "").strip()
        mod = model.strip()
        if m and not mod.lower().startswith(m.lower()):
            detected_name = f"{m} {mod}"
        else:
            detected_name = mod

    if name and name.strip():
        screen.name = name.strip()
    elif not screen.name or screen.name.startswith("Screen "):
        screen.name = detected_name or screen.name or f"Screen {device_id[:6]}"

    # Drop any code minted by an earlier /register: the screen is claimed now
    screen.pair_code = None
    screen.pair_code_expires_at = None
    screen.assignment_updated_at = models.utcnow()

    # Rotated on every bind, exactly as /enroll does. The plaintext is stashed on the
    # instance (not a column) so the calling route can hand it to the device once; it is
    # never persisted and never reloaded.
    device_secret = issue_device_secret(screen)

    db.commit()
    db.refresh(screen)
    screen.issued_device_secret = device_secret
    logger.info("Device %s (model: %s) %s to org %s by %s", device_id, screen.model, how, user.organization_id, user.username)
    return screen

@router.post("/sign-in", response_model=schemas.ScreenResponse)
# Matches the reasoning on google/start below: an installer bringing up a room of twenty
# screens is one IP making twenty legitimate attempts in a few minutes, and a five-per-
# minute cap fails exactly the install it is meant to protect. Still tight enough to make
# password guessing through this route pointless.
@limiter.limit("30/minute")
def sign_in_screen(
    request: Request,
    req: schemas.ScreenSignInRequest, 
    db: Session = Depends(database.get_db)
):
    """Bind this device to the organisation of whoever signs in on the TV.

    The pairing-code flow needs a second person at a dashboard within five minutes. If the
    installer already has an account, signing in on the TV proves the same thing. The
    device holds no credential yet, so every guard that /pair gets for free from
    require_tenant_roles has to be applied by hand here.

    Deliberately does not issue a device secret: this binds a screen exactly as /pair does,
    so device auth stays optional (see verify_device_auth) and the player needs no token
    handling. /enroll remains the path for devices that should carry a real secret.
    """
    from .auth import verify_password

    # One error for every credential failure — never reveal whether the username exists,
    # the account is disabled, or only the password was wrong.
    CREDENTIALS_ERROR = HTTPException(status_code=401, detail="The username or password is incorrect")

    # Matched case-insensitively, exactly as /api/auth/token does. Case-sensitive matching
    # here meant a TV rejected the very credentials the dashboard had just accepted.
    login_id = (req.username or "").strip().lower()
    user = db.query(models.User).filter(
        (func.lower(models.User.username) == login_id)
        | (func.lower(models.User.email) == login_id)
    ).first()
    if not user or not user.is_active or not verify_password(req.password, user.hashed_password):
        raise CREDENTIALS_ERROR

    screen = bind_screen_to_org(
        db,
        device_id=req.device_id,
        user=user,
        name=req.name,
        installation_id=req.installation_id,
        model=req.model,
        manufacturer=req.manufacturer,
        conflict_error=CREDENTIALS_ERROR,
        how="signed in",
    )
    response = schemas.ScreenResponse.model_validate(screen)
    response.device_secret = getattr(screen, "issued_device_secret", None)
    return response


# The poll token is minted and read only here, so the marker is local rather than shared.
GOOGLE_POLL_TYPE = "google_poll"


@router.post("/google/start", response_model=schemas.GoogleDeviceStartResponse)
# Loose on purpose. Each call spends a Google device-code quota unit, so it cannot be
# unlimited -- but a whole site sits behind one NAT address, and an installer bringing up
# a room of twenty screens is one IP making twenty legitimate calls in a few minutes. A
# tight per-IP cap here would fail exactly the install it is meant to protect.
@limiter.limit("30/minute")
def google_device_start(
    request: Request,
    req: schemas.GoogleDeviceStartRequest,
):
    """Begin a Google sign-in for this TV and hand back the code to put on screen."""
    from .auth import create_access_token

    if not google_device.is_configured():
        # No credentials means no Google sign-in. This used to mint a fake "TV-1234" code
        # and a poll token flagged is_dev, which google_device_poll then honoured by
        # binding the screen to `email == <a hardcoded gmail address> OR role == "owner"`
        # -- in practice whichever owner the database returned first, in someone else's
        # organisation. /auth-methods now reports google=false so the player hides the
        # button; this is the backstop for a client that asks anyway.
        raise HTTPException(status_code=503, detail="Google sign-in is not enabled on this server")

    try:
        started = google_device.start()
    except google_device.GoogleError as error:
        logger.warning("Google device-code request failed for %s: %s", req.device_id, error)
        raise HTTPException(status_code=502, detail="Could not reach Google. Try again.")

    poll_token = create_access_token(
        {
            "sub": f"device:{req.device_id}",
            "typ": GOOGLE_POLL_TYPE,
            "dc": started["device_code"],
            "nm": req.name,
            "iid": req.installation_id,
            "mod": req.model,
            "man": req.manufacturer,
        },
        expires_delta=timedelta(seconds=started["expires_in"]),
    )

    logger.info("Started Google sign-in for device %s", req.device_id)
    return schemas.GoogleDeviceStartResponse(
        user_code=started["user_code"],
        verification_url=started["verification_url"],
        interval=started["interval"],
        expires_in=started["expires_in"],
        poll_token=poll_token,
    )


@router.post("/google/poll", response_model=schemas.GoogleDevicePollResponse)
def google_device_poll(
    req: schemas.GoogleDevicePollRequest,
    db: Session = Depends(database.get_db),
):
    """Has the installer approved on their phone yet? If so, bind the screen."""
    from jose import JWTError, jwt

    from .auth import ALGORITHM, get_secret_key

    INVALID = HTTPException(status_code=401, detail="This sign-in has expired. Start again on the TV.")

    try:
        claims = jwt.decode(req.poll_token, get_secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        raise INVALID
    if claims.get("typ") != GOOGLE_POLL_TYPE:
        raise INVALID

    device_id = str(claims.get("sub") or "").removeprefix("device:")
    device_code = claims.get("dc")
    if not device_id or not device_code:
        raise INVALID

    try:
        result = google_device.poll(device_code)
    except google_device.GoogleError as error:
        logger.warning("Google poll failed for device %s: %s", device_id, error)
        raise HTTPException(status_code=502, detail="Could not reach Google. Try again.")

    if result["status"] != "ok":
        # Google has nothing for us. Before reporting that back, check whether this panel
        # got bound by some OTHER route in the meantime.
        #
        # google_device.poll() asks GOOGLE about this device code. The browser flow on the
        # TV (google/oauth-callback) is a separate OAuth grant that never approves this
        # code, so a panel signing in through its own browser sat on "authorization_pending"
        # until the code expired -- while the screen was already bound and the TV's browser
        # was showing "Display Connected".
        #
        # Closing that gap was left entirely to the olrac:// deep link back into the app,
        # and a TV browser is free to refuse it ("App deeplink blocked" on TCL), which
        # stranded the panel on a sign-in screen it had already passed. MainActivity starts
        # this poll alongside opening the browser, so the binding is reported on the next
        # tick instead and the deep link becomes an accelerator, not the only way through.
        # An operator redeeming a pairing code mid-flow lands here for the same reason.
        #
        # Deliberately only on a NON-ok result. Every authorisation check below -- the
        # tenant boundary above all -- runs whenever Google actually returns an identity,
        # and must keep running: a rival approving on their own phone has to be refused,
        # not handed the screen this device is already bound to.
        #
        # It reports a binding, it never creates one, and it reaches no further than
        # /register already does for the same device_id. No device secret: there is no new
        # grant to hand over, which is also why the deep-link path carries none.
        already_bound = (
            db.query(models.Screen)
            .filter(
                models.Screen.device_id == device_id,
                models.Screen.deleted_at.is_(None),
                models.Screen.organization_id.isnot(None),
                models.Screen.status != "waiting_pairing",
            )
            .first()
        )
        if already_bound:
            return schemas.GoogleDevicePollResponse(
                status="bound",
                screen=schemas.ScreenResponse.model_validate(already_bound),
            )
        return schemas.GoogleDevicePollResponse(status=result["status"])

    email = result.get("email") or ""
    if not email or not result.get("email_verified"):
        raise HTTPException(
            status_code=403,
            detail="That Google account has no verified email address.",
        )

    user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
    if not user or not user.is_active:
        logger.warning("Google sign-in for device %s: no active account for that address", device_id)
        raise HTTPException(
            status_code=403,
            detail=(
                "No OLRAC account uses that Google address. Add it to your profile in the "
                "dashboard under Account, then try again."
            ),
        )

    screen = bind_screen_to_org(
        db,
        device_id=device_id,
        user=user,
        name=claims.get("nm"),
        installation_id=claims.get("iid"),
        model=claims.get("mod"),
        manufacturer=claims.get("man"),
        conflict_error=HTTPException(
            status_code=403,
            detail="This screen belongs to another workspace.",
        ),
        how="signed in with Google",
    )
    bound = schemas.ScreenResponse.model_validate(screen)
    bound.device_secret = getattr(screen, "issued_device_secret", None)
    return schemas.GoogleDevicePollResponse(status="bound", screen=bound)


@router.get("/google/oauth-url")
def get_tv_google_oauth_url(
    device_id: str,
    name: Optional[str] = None,
    installation_id: Optional[str] = None,
    model: Optional[str] = None,
    manufacturer: Optional[str] = None,
    request: Request = None,
):
    """Generate a direct Google OAuth URL for Android TV / Custom Tab login."""
    from .auth import create_access_token

    if not google_device.is_web_configured():
        raise HTTPException(status_code=503, detail="Google sign-in is not enabled on this server")

    redirect_uri = f"{public_base_url(request)}/api/screens/google/oauth-callback"
    state_token = create_access_token(
        {
            "sub": f"device:{device_id}",
            "typ": "tv_oauth",
            "nm": name,
            "iid": installation_id,
            "mod": model,
            "man": manufacturer,
        },
        expires_delta=timedelta(minutes=30),
    )
    return {
        "oauth_url": google_device.build_oauth_url(redirect_uri, state=state_token),
        "redirect_uri": redirect_uri,
    }


# The player's package, so an intent: URL can name it and Chrome launches it directly
# instead of bouncing to the Play Store. Matches applicationId in
# android-tv/app/build.gradle.kts; there is no build-type suffix, so one value covers both.
TV_APP_PACKAGE = "com.olrac.signage"


def _android_intent_url(deep_link: str) -> str:
    """Rewrite an "olrac://" deep link into the intent: form a browser will actually open.

    The player registers the custom scheme (AndroidManifest, scheme="olrac" host="auth",
    BROWSABLE) and MainActivity.onNewIntent handles it -- but none of that is ever reached,
    because Chrome refuses to resolve a scheme it does not know and fails the navigation
    with ERR_UNKNOWN_URL_SCHEME. Chrome is what a Custom Tab is, and what every Android TV
    browser is, so this failed on the panel while working anywhere it was tested by hand.

    That is the "Web page not available" a TV shows at the very end of Google sign-in: the
    account is authenticated and the screen is bound server side, the sign-in genuinely
    succeeded, and the panel simply never hears about it and sits on the sign-in screen.

    The intent: syntax is the documented way to hand a browser navigation to an app. The
    intent it builds carries the same "olrac://auth/..." data, so the manifest filter that
    is already shipped matches it and no APK rebuild is needed -- this is a backend deploy.
    """
    parts = urllib.parse.urlsplit(deep_link)
    # http(s) is already something a browser can open; only a custom scheme needs this.
    if not parts.scheme or parts.scheme in ("http", "https"):
        return deep_link
    target = f"{parts.netloc}{parts.path}"
    if parts.query:
        target += f"?{parts.query}"
    # Nothing caller-supplied can break out of the fragment: every value reaching a query
    # here goes through urllib.parse.quote, which percent-encodes both "#" and ";".
    return f"intent://{target}#Intent;scheme={parts.scheme};package={TV_APP_PACKAGE};end"


def _tv_result_page(title: str, heading: str, body_html: str, deep_link: str, accent: str) -> HTMLResponse:
    """The TV's Custom Tab landing page, which then hands back to the player app.

    Every caller-supplied value reaching this function is escaped by the caller with
    html.escape. The three pages this replaces interpolated `screen.name`, `target_email`
    and Google's raw `error` string straight into markup -- and screen names are
    operator-controlled, so that was stored XSS in a page that runs on the installer's
    phone.
    """
    launch_url = _android_intent_url(deep_link)
    safe_link = html.escape(launch_url, quote=True)
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{html.escape(title)} &mdash; OLRAC Signage</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ background: #070A0F; color: #FFFFFF; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }}
        .card {{ background: #0D131F; border: 1px solid #1E293B; border-radius: 20px; padding: 40px; max-width: 420px; width: 90%; }}
        .btn {{ display: inline-block; margin-top: 24px; padding: 14px 28px; background: {accent}; color: #070A0F; border-radius: 12px; text-decoration: none; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="card">
        <h1 style="color:{accent};margin-bottom:12px;font-size:22px;">{heading}</h1>
        <p style="color:#94A3B8;line-height:1.5;">{body_html}</p>
        <a id="link" href="{safe_link}" class="btn" autofocus>Return to Player</a>
    </div>
    <script>
        window.location.href = {json.dumps(launch_url)};
        setTimeout(function() {{ window.close(); }}, 2500);
    </script>
</body>
</html>""",
        media_type="text/html; charset=utf-8",
    )


@router.get("/google/oauth-callback", response_class=HTMLResponse)
def tv_google_oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    request: Request = None,
    db: Session = Depends(database.get_db),
):
    """Handle Google OAuth return on Android TV Custom Tab and auto-bind screen.

    `email` and `name` used to be accepted here as query parameters and trusted as the
    signed-in identity. The `state` token they travelled with is minted by
    /google/oauth-url, which is unauthenticated -- so two requests, neither of them
    carrying a credential, bound an attacker's TV into any workspace whose owner's address
    they could guess. Identity now comes only from exchanging `code` with Google.
    """
    from jose import JWTError, jwt
    from .auth import ALGORITHM, get_secret_key

    FAILED_LINK = "olrac://auth/failed"

    def failure(heading: str, message: str, link: str = FAILED_LINK) -> HTMLResponse:
        return _tv_result_page("Sign-in failed", heading, message, link, "#FF8A80")

    if error or not state:
        return failure("Google Authentication Cancelled", html.escape(error or "Missing state token"))

    try:
        claims = jwt.decode(state, get_secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        return failure("Sign-in Expired", "This sign-in link is no longer valid. Start again on the TV.")
    if claims.get("typ") != "tv_oauth":
        return failure("Sign-in Expired", "This sign-in link is no longer valid. Start again on the TV.")

    device_id = str(claims.get("sub") or "").removeprefix("device:")
    if not device_id:
        return failure("Sign-in Failed", "This sign-in link is missing its device. Start again on the TV.")

    if not code or not google_device.is_web_configured():
        return failure("Sign-in Failed", "Google did not return an authorization code. Start again on the TV.")

    # Must be byte-identical to the redirect_uri /google/oauth-url sent to Google, or the
    # exchange is rejected. Both are built from public_base_url, so a deployment behind TLS
    # produces an https:// pair -- the hardcoded http://127.0.0.1:8000 this replaces could
    # never work anywhere but a developer's laptop.
    redirect_uri = f"{public_base_url(request)}/api/screens/google/oauth-callback"
    try:
        google_claims = google_device.exchange_code(code, redirect_uri)
    except google_device.GoogleError as exc:
        logger.warning("Google code exchange failed on TV callback: %s", exc)
        return failure("Sign-in Failed", "Could not complete Google sign-in. Start again on the TV.")

    target_email = (google_claims.get("email") or "").strip().lower()
    if not target_email or not google_claims.get("email_verified"):
        return failure("Sign-in Failed", "That Google account has no verified email address.")

    google_sub = google_claims.get("sub")
    user = None
    if google_sub:
        user = db.query(models.User).filter(models.User.google_sub == google_sub).first()
    if not user:
        user = db.query(models.User).filter(
            (func.lower(models.User.email) == target_email)
            | (func.lower(models.User.username) == target_email)
        ).first()

    if not user:
        import secrets
        org_name = google_claims.get("name") or target_email.split("@")[0]
        organization = models.Organization(
            name=f"{org_name}'s Workspace",
            slug=f"org-{secrets.token_hex(4)}",
            status="active",
            approved_at=datetime.utcnow(),
        )
        db.add(organization)
        db.flush()

        user = models.User(
            organization_id=organization.id,
            email=target_email,
            username=target_email,
            google_sub=google_sub,
            role="owner",
            is_active=True,
            auth_provider="google",
            picture=google_claims.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_active:
        user.is_active = True
        if google_sub and not user.google_sub:
            user.google_sub = google_sub
        db.commit()

    screen = bind_screen_to_org(
        db,
        device_id=device_id,
        user=user,
        name=claims.get("nm"),
        installation_id=claims.get("iid"),
        model=claims.get("mod"),
        manufacturer=claims.get("man"),
        conflict_error=HTTPException(status_code=403, detail="Screen claimed elsewhere"),
        how="signed in with Google OAuth",
    )

    deep_link = (
        f"olrac://auth/success?screen_id={screen.id}"
        f"&screen_name={urllib.parse.quote(screen.name or '')}"
    )
    return _tv_result_page(
        "Display connected",
        "&#10003; Display Connected",
        f"Screen <strong>{html.escape(screen.name or 'Display')}</strong> is now linked to "
        f"<strong>{html.escape(user.email or user.username)}</strong>.",
        deep_link,
        "#68E0A0",
    )


@router.post("/enroll", response_model=schemas.EnrollResponse)
def enroll_device(req: schemas.EnrollRequest, db: Session = Depends(database.get_db)):
    token = db.query(models.EnrollmentToken).filter(
        models.EnrollmentToken.token == req.enrollment_token,
        models.EnrollmentToken.is_active == True
    ).first()
    # Use a single generic error for all token rejection cases so callers
    # cannot probe which tokens exist or distinguish between "no such token",
    # "expired", "revoked", and "quota exhausted".
    TOKEN_ERROR = HTTPException(status_code=400, detail="Invalid or inactive enrollment token")

    if not token:
        raise TOKEN_ERROR

    # Lifecycle check 1: expiry
    if token.expires_at and token.expires_at < models.utcnow():
        raise TOKEN_ERROR

    # Lifecycle check 2: max-use cap
    if token.max_uses is not None and token.use_count >= token.max_uses:
        raise TOKEN_ERROR

    screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id, models.Screen.deleted_at.is_(None)).first()

    if screen and screen.organization_id not in (None, token.organization_id):
        # A device already belonging to another organisation must never be re-homed by
        # presenting a different organisation's token. Without this guard anyone holding
        # any valid enrollment token can hijack a competitor's screen by guessing its
        # device_id: the screen moves to their tenant and the rightful owner's secret is
        # overwritten, taking the TV offline. Enrollment is unauthenticated, so this is
        # the only place the tenant boundary can be enforced.
        # Deliberately the same generic error as a bad token, so this cannot be used to
        # probe which device ids exist.
        logger.warning(
            "Rejected cross-tenant enrollment of device %s: owned by org %s, token belongs to org %s",
            req.device_id, screen.organization_id, token.organization_id,
        )
        raise TOKEN_ERROR

    if not screen and req.installation_id:
        # A factory reset mints a fresh device_id, so the same panel would enrol again as
        # a second screen and the fleet count would drift up with every wipe. The install
        # id survives the reset, so the existing row is reclaimed and its history, group
        # and playlist assignment stay with the physical screen.
        screen = (
            db.query(models.Screen)
            .filter(
                models.Screen.installation_id == req.installation_id,
                models.Screen.organization_id == token.organization_id,
            )
            .first()
        )
        if screen:
            logger.info(
                "Reclaiming screen %s for installation %s (device id changed %s -> %s)",
                screen.id, req.installation_id, screen.device_id, req.device_id,
            )
            temp_screen = db.query(models.Screen).filter(
                models.Screen.device_id == req.device_id,
                models.Screen.id != screen.id
            ).first()
            if temp_screen:
                db.delete(temp_screen)
                db.flush()
            screen.device_id = req.device_id

    if not screen:
        # New device counts against the plan, exactly as pairing does.
        ensure_screen_quota(db, token.organization_id, "enrol another device")
        screen = models.Screen(device_id=req.device_id)
        db.add(screen)

    import secrets
    from .auth import get_password_hash
    device_secret = secrets.token_hex(32)

    # Re-enrolling a device already in this organisation is legitimate (factory reset,
    # reinstall) and rotates the secret.
    screen.device_secret_hash = get_password_hash(device_secret)
    screen.organization_id = token.organization_id
    screen.status = "offline"
    # The enrollment token was minted by an owner for exactly this, so the screen is
    # already authorised; making it queue for approval would gate zero-touch on a human.
    screen.approved_at = models.utcnow()
    screen.installation_id = req.installation_id
    if not screen.name:
        screen.name = f"Screen {req.device_id[:6]}"
    screen.assignment_updated_at = models.utcnow()

    # Atomically increment use_count after all validation passes.
    token.use_count = (token.use_count or 0) + 1

    db.commit()

    return {
        "device_id": req.device_id,
        "device_secret": device_secret,
        "organization_id": token.organization_id,
        "screen_id": screen.id
    }


@router.post("/auth", response_model=schemas.DeviceTokenResponse)
# Sized for a site reconnecting, not for a single device. Fifty screens in one mall leave
# through one public IP and all re-authenticate at once after a power cut -- the moment a
# tight cap does the most damage. The credential here is a 32-byte secret, so brute force
# is infeasible at any rate this would permit; the cap exists to bound abuse, not to be the
# thing standing between an attacker and the fleet.
@limiter.limit("120/minute")
def auth_device(
    request: Request,
    req: schemas.DeviceAuthRequest, 
    db: Session = Depends(database.get_db)
):
    screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id, models.Screen.deleted_at.is_(None)).first()
    if not screen or not screen.device_secret_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    from .auth import verify_password, create_access_token
    if not verify_password(req.device_secret, screen.device_secret_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    token = create_access_token(
        data={"sub": f"device:{req.device_id}"},
        expires_delta=timedelta(hours=1)
    )
    return {"access_token": token}


@router.get("/", response_model=list[schemas.ScreenResponse])
async def get_screens(
    scope: TenantScope = Depends(get_tenant_scope),
):
    # A screen still waiting to be paired is not part of the fleet: it has no name, no
    # playlist and nothing to report, and listing it put placeholder cards in the grid.
    screens = (
        scope.query(models.Screen)
        .filter(models.Screen.status != "waiting_pairing")
        .order_by(models.Screen.name)
        .all()
    )
    candidates = screens

    # One pipelined round-trip for the whole fleet. Awaiting EXISTS per screen inside
    # the loop is 500 sequential round-trips at 500 screens, which is the latency
    # problem Redis was introduced to remove.
    presence: dict[int, bool] | None = None
    if candidates:
        try:
            redis = database.get_redis()
            pipe = redis.pipeline()
            for screen in candidates:
                pipe.exists(f"screen_presence:{screen.id}")
            results = await pipe.execute()
            presence = {s.id: bool(r) for s, r in zip(candidates, results)}
        except Exception as exc:  # noqa: BLE001 - Redis is a cache, not a dependency
            logger.warning("Redis presence read failed, falling back to last_seen: %s", exc)

    changed = False
    for screen in candidates:
        is_online = (presence.get(screen.id, False) if presence else False) or _is_recent(screen.last_seen)
        new_status = "online" if is_online else "offline"
        if screen.status != new_status:
            screen.status = new_status
            changed = True

    if changed:
        scope.db.commit()

    shots = _latest_screenshots(scope, screens)
    return [
        schemas.ScreenResponse.model_validate(screen).model_copy(
            update={"latest_screenshot": shots.get(screen.id)}
        )
        for screen in screens
    ]


def _is_recent(last_seen) -> bool:
    """True when last_seen is inside the offline threshold.

    Tolerates naive and aware timestamps: SQLite returns naive values while Postgres
    with timezone=True returns aware ones, and comparing the two raises TypeError.
    """
    if last_seen is None:
        return False
    now = models.utcnow()
    if last_seen.tzinfo is None:
        now = now.replace(tzinfo=None)
    return (now - last_seen).total_seconds() < screen_offline_after_seconds()


def _latest_screenshots(scope: TenantScope, screens) -> dict[int, str]:
    """Most recent capture per screen, in one query.

    The fleet grid shows a live thumbnail per screen. Fetching that per card is 500 round
    trips at 500 screens, so the newest row per screen is picked with a window function.
    """
    if not screens:
        return {}

    ranked = (
        select(
            models.ScreenshotLog.screen_id.label("screen_id"),
            models.ScreenshotLog.file_url.label("file_url"),
            func.row_number()
            .over(
                partition_by=models.ScreenshotLog.screen_id,
                order_by=models.ScreenshotLog.created_at.desc(),
            )
            .label("rank"),
        )
        .where(models.ScreenshotLog.screen_id.in_([s.id for s in screens]))
    )
    # Super admins read across tenants; everyone else must stay inside their own.
    if scope.user.role != "super_admin":
        ranked = ranked.where(models.ScreenshotLog.organization_id == scope.organization_id)

    newest = ranked.subquery()
    rows = scope.db.execute(
        select(newest.c.screen_id, newest.c.file_url).where(newest.c.rank == 1)
    ).all()

    return {screen_id: resolve_media_url(file_url) for screen_id, file_url in rows}


@router.put("/{screen_id}", response_model=schemas.ScreenResponse)
def update_screen(
    screen_id: int,
    screen: schemas.ScreenCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    db_screen = scope.get(models.Screen, screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    db_screen.name = screen.name
    db_screen.orientation = screen.orientation
    # An operator setting orientation here means the heartbeat must stop overwriting it.
    db_screen.orientation_source = "manual"
    if "group_id" in screen.model_fields_set:
        db_screen.group_id = screen.group_id
    db_screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(db_screen)
    return db_screen


@router.patch("/{screen_id}", response_model=schemas.ScreenResponse)
def patch_screen(
    screen_id: int,
    patch: schemas.ScreenPatch,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    db_screen = scope.get(models.Screen, screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    fields = patch.model_fields_set
    if "target_version_code" in fields and patch.target_version_code is not None:
        release = scope.db.query(models.AppRelease).filter(
            models.AppRelease.version_code == patch.target_version_code
        ).first()
        if not release:
            raise HTTPException(status_code=422, detail="Unknown release version code")

    if "leader_screen_id" in fields and patch.leader_screen_id is not None:
        if patch.leader_screen_id == screen_id:
            raise HTTPException(status_code=422, detail="A screen cannot follow itself")
        # scope.get keeps this inside the tenant: without it, a follower could be pointed
        # at another organisation's screen and take its playback clock.
        if not scope.get(models.Screen, patch.leader_screen_id):
            raise HTTPException(status_code=422, detail="Unknown leader screen")

    for field in (
        "name",
        "orientation",
        "group_id",
        "target_version_code",
        "description",
        "tags",
        "location",
        "latitude",
        "longitude",
        "place_id",
        "timezone",
        "fit_mode",
        "maintenance_pin",
        "sync_playback",
        "sync_role",
        "leader_screen_id",
        "operating_mode",
        "operating_hours",
    ):
        if field in fields:
            setattr(db_screen, field, getattr(patch, field))
    if "target_version_code" in fields:
        # Re-pinning is a fresh attempt: carry no failure count over from the build this
        # screen was previously chasing, or it would roll back after one failure instead
        # of three.
        rollout.repin(db_screen, patch.target_version_code)
    if "orientation" in fields:
        # Explicit operator choice; auto-detection must not undo it on the next heartbeat.
        db_screen.orientation_source = "manual"
    # A leader has nothing to follow; keeping a stale pointer would make the player chase
    # a clock it is supposed to be publishing.
    if db_screen.sync_role == "leader":
        db_screen.leader_screen_id = None

    # The player asks "anything new since X?" and the answer is built from this marker.
    # Orientation and fit_mode are answered in that same response, so without a bump the
    # sync stays quiet and an operator's rotation change never reaches the panel.
    db_screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(db_screen)
    from .websockets import trigger_screen_sync
    trigger_screen_sync(organization_id=scope.organization_id, screen_device_id=db_screen.device_id, group_id=db_screen.group_id)
    return db_screen


@router.delete("/{screen_id}", status_code=204)
async def remove_screen(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    """Remove a TV from the fleet and sign the panel out of this workspace.

    Archives rather than deletes. play_logs and play_log_hourly_rollups both hold a NOT
    NULL foreign key to this row, and the booking report attributes plays to a screen by
    name -- so a DELETE would either fail on the constraint or, with it relaxed, quietly
    erase the proof of play an advertiser was billed on. The screen leaves the fleet, the
    history keeps it.

    Owner-only, unlike the editor-level screen edits: this ends a device's access to the
    workspace, which is closer to revoking a credential than to renaming a screen.
    """
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    device_id = screen.device_id

    screen.deleted_at = models.utcnow()
    # The credential goes with the row. Without this, a token minted moments before the
    # removal stays valid for its full hour -- and verify_device_auth would refuse it
    # anyway, but leaving a live hash on an archived screen is a loaded gun for whatever
    # reads that column next.
    screen.device_secret_hash = None
    # Frees the identifiers so the same panel can be paired again as a new screen. Held
    # onto, the unique constraint on device_id would reject the fresh row and the TV could
    # never rejoin -- a removal that quietly bricks the hardware. The old values stay
    # readable on the archived row for anyone tracing what happened.
    screen.device_id = f"removed:{screen.id}:{device_id}" if device_id else None
    screen.installation_id = None
    # Nothing should still be scheduled to it.
    screen.playlist_id = None
    screen.group_id = None
    screen.pair_code = None
    scope.db.commit()

    # Tell it now rather than at its next sync. A screen removed mid-playback would
    # otherwise keep showing the old playlist for up to PLAYER_SYNC_INTERVAL_SECONDS,
    # which for an operator who just cut a customer off is exactly the wrong behaviour.
    # Best-effort: the 404 on the next sync is the guarantee, this is the speed.
    if device_id:
        await queue_device_command(device_id, "deregister", ttl_seconds=3600)
        try:
            redis = database.get_redis()
            payload = json.dumps({"type": "deregister", "command": "deregister"})
            await redis.publish(f"screen:{device_id}", payload)
            await redis.publish(f"device:{device_id}", payload)
        except Exception as exc:  # noqa: BLE001 - the 404 still resets it
            logger.warning("Could not push deregister to %s: %s", device_id, exc)

    logger.info("Screen %s removed from organisation %s", screen_id, screen.organization_id)
    return Response(status_code=204)


@router.delete("/{screen_id}/device-secret")
def revoke_device_secret(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    db_screen = scope.get(models.Screen, screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    db_screen.device_secret_hash = None
    scope.db.commit()
    return {"status": "ok", "message": "Device secret revoked"}


@router.delete("/{screen_id}")
async def delete_screen(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Permanently delete a screen and instruct the physical TV to sign out immediately."""
    db_screen = scope.get(models.Screen, screen_id)
    if not db_screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    device_id = db_screen.device_id
    org_id = db_screen.organization_id

    # 1. Queue and publish instant remote reset / unpair command
    if device_id:
        try:
            await queue_device_command(device_id, "reset", 300)
        except Exception as exc:
            logger.warning("Could not queue reset command for %s: %s", device_id, exc)

        payload = json.dumps({"type": "command", "command": "reset", "reason": "unpaired_by_admin"})
        try:
            redis = database.get_redis()
            await redis.publish(f"screen:{device_id}", payload)
            await redis.publish(f"device:{device_id}", payload)
            await redis.publish(f"screen:{screen_id}", payload)
            if org_id:
                await redis.publish(f"org:{org_id}", payload)
        except Exception as exc:
            logger.warning("Failed to publish reset command to redis: %s", exc)

        try:
            from .websockets import broadcast_in_memory
            await broadcast_in_memory(f"screen:{device_id}", payload)
            await broadcast_in_memory(f"device:{device_id}", payload)
            await broadcast_in_memory(f"screen:{screen_id}", payload)
            if org_id:
                await broadcast_in_memory(f"org:{org_id}", payload)
        except Exception as exc:
            logger.warning("Failed to broadcast reset command in-memory: %s", exc)

    # 2. Clean up child references
    scope.db.query(models.AdPlacementTarget).filter(models.AdPlacementTarget.screen_id == screen_id).delete(synchronize_session=False)
    scope.db.query(models.ScreenshotLog).filter(models.ScreenshotLog.screen_id == screen_id).delete(synchronize_session=False)
    scope.db.query(models.Alert).filter(models.Alert.screen_id == screen_id).delete(synchronize_session=False)
    scope.db.query(models.PlayLog).filter(models.PlayLog.screen_id == screen_id).delete(synchronize_session=False)
    scope.db.query(models.PlayLogHourlyRollup).filter(models.PlayLogHourlyRollup.screen_id == screen_id).delete(synchronize_session=False)

    # 3. Delete the screen from database
    scope.db.delete(db_screen)
    scope.db.commit()

    return {"status": "ok", "message": f"Screen {screen_id} deleted and unpairing signal broadcast."}


@router.post("/heartbeat")
async def heartbeat(
    req: schemas.HeartbeatRequest, 
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    db_screen = verify_device_auth(req.device_id, credentials, db)
    
    # Update DB fields
    db_screen.last_seen = models.utcnow()
    if db_screen.status != "waiting_pairing":
        db_screen.status = "online"
    if req.device_version:
        db_screen.device_version = req.device_version
        if not req.app_version:
            db_screen.app_version = req.device_version
    if req.app_version is not None:
        db_screen.app_version = req.app_version
    if getattr(req, "update_status", None) is not None:
        rolled_back = rollout.apply_update_status(
            db_screen,
            req.update_status,
            getattr(req, "version_code", None),
        )
        if rolled_back:
            logging.getLogger(__name__).warning(
                "Screen %s %s", db_screen.id, rolled_back
            )
        # Only when the device actually told us its version. This used to assign
        # unconditionally, so a heartbeat reporting an update result without app_version
        # wiped the device_version that had been recorded earlier.
        if req.app_version is not None:
            db_screen.device_version = req.app_version
    if req.storage_used:
        db_screen.storage_used = req.storage_used

    # Auto-detected orientation, but never over an operator's explicit choice. This is the
    # only place auto-detection is applied; without the source check a manual override
    # silently reverts on the next heartbeat.
    if req.orientation is not None and db_screen.orientation_source != "manual":
        db_screen.orientation = normalise_rotation(req.orientation)

    if req.screen_width is not None:
        db_screen.screen_width = req.screen_width
    if req.screen_height is not None:
        db_screen.screen_height = req.screen_height
    if req.refresh_rate is not None:
        db_screen.refresh_rate = req.refresh_rate
    if req.total_ram_mb is not None:
        db_screen.total_ram_mb = req.total_ram_mb
    if req.available_ram_mb is not None:
        db_screen.available_ram_mb = req.available_ram_mb
    if req.total_storage_mb is not None:
        db_screen.total_storage_mb = req.total_storage_mb
    if req.free_storage_mb is not None:
        db_screen.free_storage_mb = req.free_storage_mb
    if req.supported_video_codecs is not None:
        db_screen.supported_video_codecs = req.supported_video_codecs
    if req.max_decode_width is not None:
        db_screen.max_decode_width = req.max_decode_width
    if req.max_decode_height is not None:
        db_screen.max_decode_height = req.max_decode_height
    if req.manufacturer is not None:
        db_screen.manufacturer = req.manufacturer
    if req.model is not None:
        db_screen.model = req.model
    if req.android_version is not None:
        db_screen.android_version = req.android_version
    if req.sdk_int is not None:
        db_screen.sdk_int = req.sdk_int
    if req.network_type is not None:
        db_screen.network_type = req.network_type
    if req.timezone is not None:
        db_screen.timezone = req.timezone
        
    fields = req.model_fields_set
    if "playback_state" in fields and req.playback_state is not None:
        db_screen.playback_state = req.playback_state
    if "current_item_id" in fields:
        db_screen.current_item_id = req.current_item_id
    if "last_error" in fields:
        db_screen.last_error = req.last_error
        if req.last_error:
            db_screen.last_error_at = models.utcnow()
    db.commit()

    # Presence cache. Best-effort on purpose: a Redis outage must never fail a TV's
    # heartbeat. last_seen is already committed above, so get_screens can fall back to
    # it. Reliability of the fleet outranks accuracy of the presence cache.
    pending_command = await pop_device_command(db_screen.device_id)
    try:
        ttl = screen_offline_after_seconds()
        await database.get_redis().setex(f"screen_presence:{db_screen.id}", ttl, "online")
    except Exception as exc:  # noqa: BLE001 - any Redis failure must stay non-fatal
        logger.warning("Redis presence write failed for screen %s: %s", db_screen.id, exc)

    return {
        "status": "ok", 
        "screen_status": db_screen.status,
        "server_time_ms": int(models.utcnow().timestamp() * 1000),
        "screen_id": db_screen.id,
        "organization_id": db_screen.organization_id,
        "pending_command": pending_command,
    }


# Screen approval was removed here, deliberately.
#
# `Screen.approved_at` was written by /pair, /sign-in and /enroll and read by absolutely
# nothing -- sync_tv never consulted it. So POST /{id}/approve and /{id}/revoke-approval
# had no effect on playback: a "revoked" screen kept syncing and playing, and no dashboard
# ever called either route. Pairing a screen is now what it always actually was, instant.
#
# The gate that DOES matter is company approval (Organization.status), which a platform
# administrator controls from the admin console and which get_tenant_scope and sync_tv both
# enforce. approved_at survives as the informational "when did this screen join" timestamp
# the fleet list shows.


@router.post("/{screen_id}/assign/{playlist_id}")
async def assign_playlist(
    screen_id: int,
    playlist_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    now = models.utcnow()
    screen.playlist_id = playlist_id
    screen.assignment_updated_at = now
    playlist.updated_at = now
    scope.db.commit()
    
    from .websockets import trigger_screen_sync
    trigger_screen_sync(organization_id=scope.organization_id, screen_device_id=screen.device_id)
    
    return {"status": "ok", "message": "Playlist assigned"}


@router.delete("/{screen_id}/assign")
async def clear_direct_assignment(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    screen.playlist_id = None
    screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    
    from .websockets import trigger_screen_sync
    trigger_screen_sync(organization_id=scope.organization_id, screen_device_id=screen.device_id)
    
    return {"status": "ok"}


@router.get("/player-version", response_model=schemas.AppVersionResponse)
def player_version(db: Session = Depends(database.get_db)):
    # `db` was missing, so every call raised TypeError and the endpoint answered 500.
    # The sync path passed it correctly, which is why updates still reached devices and
    # hid the breakage here.
    return current_app_version(db)


# A group tree deeper than this is a mistake or a cycle, either way not worth walking.
MAX_GROUP_DEPTH = 32


def resolve_screen_playlist(screen: models.Screen, db: Session) -> int | None:
    # 1. Emergency Broadcast Overrides
    active_broadcasts = db.query(models.EmergencyBroadcast).filter(
        models.EmergencyBroadcast.organization_id == screen.organization_id,
        models.EmergencyBroadcast.is_active == True
    ).all()
    
    # Priority: screen > group > org (all)
    for broadcast in active_broadcasts:
        if broadcast.target_type == "screen" and broadcast.target_id == screen.id:
            return broadcast.playlist_id
            
    # For group, we need to check screen's group and its parents.
    #
    # Bounded. ScreenGroup.parent_id is operator-settable and was never validated, so a
    # cycle (A -> B -> A) was reachable, and every one of these `while current_group` walks
    # would then spin forever holding a database connection and a request thread. The
    # create/update routes now reject cycles outright; this cap is the backstop for rows
    # that predate that check.
    screen_group_ids = []
    current_group = screen.group
    for _ in range(MAX_GROUP_DEPTH):
        if current_group is None:
            break
        screen_group_ids.append(current_group.id)
        current_group = current_group.parent
        
    for broadcast in active_broadcasts:
        if broadcast.target_type == "group" and broadcast.target_id in screen_group_ids:
            return broadcast.playlist_id
            
    for broadcast in active_broadcasts:
        if broadcast.target_type == "all":
            return broadcast.playlist_id
            
    # 2. Direct Playlist Assignment
    if screen.playlist_id:
        return screen.playlist_id
        
    # 3. Hierarchical Group Inheritance (bounded, see MAX_GROUP_DEPTH above)
    current_group = screen.group
    for _ in range(MAX_GROUP_DEPTH):
        if current_group is None:
            break
        if current_group.playlist_id:
            return current_group.playlist_id
        current_group = current_group.parent
        
    # 4. Dynamic Groups (Evaluating criteria)
    dynamic_groups = db.query(models.ScreenGroup).filter(
        models.ScreenGroup.organization_id == screen.organization_id,
        models.ScreenGroup.is_dynamic == True
    ).all()
    for dg in dynamic_groups:
        if not dg.dynamic_criteria or not dg.playlist_id:
            continue
        # Evaluate simple JSON criteria like {"orientation": 1}
        match = True
        for k, v in dg.dynamic_criteria.items():
            if getattr(screen, k, None) != v:
                match = False
                break
        if match:
            return dg.playlist_id

    return None

@router.get(
    "/{device_id}/sync",
    response_model=schemas.SyncResponse,
    responses={204: {"description": "Playlist has not changed"}},
)
async def sync_tv(
    device_id: str,
    since: datetime | None = None,
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    screen = verify_device_auth(device_id, credentials, db)

    pending_command = await pop_device_command(device_id)

    # Not yet let into the fleet: answer with the state and nothing else. Deliberately
    # ahead of the 204 short-circuit below -- a screen that was playing before it was
    # un-approved must be told now, not left running a cached playlist until something
    # else happens to change its marker.
    #
    # organization_id guards the condition: a screen that has not been claimed at all also
    # has no approved_at, and answering "pending_approval" for it would hide the
    # waiting_pairing state the player uses to decide to show its pairing code -- a brand
    # new TV would sit blank instead, and could never be paired.
    if screen.organization and screen.organization.status == "pending_approval":
        setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == "universal_demo_video_url").first()
        demo_url = setting.value if setting else "/uploads/f9863204-f997-4122-ac1b-a50157e3d905.mp4"
        demo_url = resolve_media_url(demo_url) or demo_url

        demo_content = schemas.ContentResponse(
            id=999999,
            name="OLRAC Universal Demo Reel",
            type="video/mp4",
            file_url=demo_url,
            thumbnail=None,
            file_size_bytes=1575315,
            duration_ms=44000,
            status="ready",
            uploaded_at=models.utcnow(),
            renditions=[],
        )
        demo_item = schemas.PlaylistItemResponse(
            id=999999,
            content_id=999999,
            order=0,
            duration=44,
            rotation=screen.orientation or 0,
            content=demo_content,
        )
        demo_playlist = schemas.PlaylistResponse(
            id=999999,
            name="OLRAC Universal Demo Loop",
            default_transition="fade",
            default_transition_ms=600,
            created_at=models.utcnow(),
            updated_at=models.utcnow(),
            items=[demo_item],
        )
        return schemas.SyncResponse(
            status="online",
            playlist=demo_playlist,
            playlist_updated_at=models.utcnow(),
            fit_mode=screen.fit_mode or "contain",
            maintenance_pin=screen.maintenance_pin if getattr(screen, "authenticated", False) else None,
            sync_interval_seconds=15,
            operating_mode="always",
            pending_command=pending_command,
            screen_id=screen.id,
            organization_id=screen.organization_id,
        )

    playlist_id = resolve_screen_playlist(screen, db)
    playlist = (
        db.query(models.Playlist)
        # The same load chain the dashboard's playlist routes use, and it matters more
        # here than anywhere else in the API. This response embeds a ContentResponse per
        # item, whose expires_at walks Content.playlist_items -- so lazily this cost one
        # extra query per item: 109 queries for a 100-item playlist. Every screen repeats
        # that every PLAYER_SYNC_INTERVAL_SECONDS, so an 80-screen estate on a one-minute
        # interval was issuing roughly 8,700 queries a minute to render a playlist that
        # had not changed. Named eagerly it is a fixed handful regardless of length.
        .options(*playlists_router.PLAYLIST_LOAD)
        .filter(
            models.Playlist.id == playlist_id,
            models.Playlist.organization_id == screen.organization_id,
        )
        .first()
        if playlist_id and screen.organization_id is not None
        else None
    )
    marker = screen.assignment_updated_at or screen.last_seen
    if playlist and playlist.updated_at > marker:
        marker = playlist.updated_at
    if screen.group and screen.group.updated_at > marker:
        marker = screen.group.updated_at

    marker = as_aware_utc(marker)
    if since and marker <= as_aware_utc(since) and not pending_command:
        return Response(
            status_code=204,
            headers={"X-Sync-Interval-Seconds": str(player_sync_interval_seconds())},
        )

    playlist_payload = None
    if playlist:
        playlist_payload = schemas.PlaylistResponse.model_validate(playlist)
        valid_items = []
        for item in playlist_payload.items:
            if item.content.status in {"ready", "processing"}:
                rendition = select_rendition(item.content, screen)
                if rendition:
                    item.content.file_url = rendition.file_url
                    item.content.sha256 = rendition.sha256
                    item.content.file_size_bytes = rendition.file_size_bytes

                item.content.file_url = resolve_media_url(item.content.file_url) or item.content.file_url
                item.content.thumbnail = resolve_media_url(item.content.thumbnail)
                # Resolve renditions urls as well if needed
                for rend in item.content.renditions:
                    rend.file_url = resolve_media_url(rend.file_url) or rend.file_url
                # Hand the player one number so it never has to work out precedence.
                item.rotation = resolve_rotation(item, screen)
                valid_items.append(item)
        playlist_payload.items = valid_items

    return schemas.SyncResponse(
        fit_mode=screen.fit_mode or "contain",
        # Withheld from a screen that authenticated with nothing but its device id: this
        # pin unlocks the on-TV maintenance screen, and device ids are guessable.
        maintenance_pin=screen.maintenance_pin if getattr(screen, "authenticated", False) else None,
        operating_mode=screen.operating_mode or "always",
        operating_hours=screen.operating_hours,
        playlist=playlist_payload,
        playlist_updated_at=marker,
        status=screen.status,
        app_version=current_app_version(db, screen.target_version_code or (screen.group.target_version_code if screen.group else None)),
        sync_interval_seconds=player_sync_interval_seconds(),
        pending_command=pending_command,
        screen_id=screen.id,
        organization_id=screen.organization_id,
    )


@router.post("/play-logs/batch")
def batch_upload_play_logs(
    req: schemas.PlayLogBatchRequest,
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    if len(req.events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds limit of 500")

    # Same identity check as sync and heartbeat: a screen holding a device secret must
    # present its token, one provisioned by pair code is known by its device id. This
    # endpoint used to demand a JWT of its own, which no pair-code screen can produce, so
    # every one of them had its proof of play rejected with 401 and reported zero plays.
    device_id = req.device_id
    screen = verify_device_auth(device_id, credentials, db)

    # The identity that counts is the authenticated screen, never the body. screen_id and
    # organization_id are still ACCEPTED for compatibility with players that send them, but
    # a value naming a different screen or tenant is rejected rather than quietly
    # rewritten: silently re-attributing it would let one TV file plays that look like they
    # came from a competitor's screen, and the sender would be told it worked.
    if req.screen_id is not None and req.screen_id != screen.id:
        raise HTTPException(status_code=403, detail="screen_id does not match the authenticated screen")
    if req.organization_id is not None and req.organization_id != screen.organization_id:
        raise HTTPException(status_code=403, detail="organization_id does not match the authenticated screen")

    target_screen_id = screen.id
    target_org_id = screen.organization_id

    if not req.events:
        return {"status": "ok", "inserted": 0}

    from sqlalchemy.dialects.postgresql import insert

    # The player cannot attribute a play to a campaign: PlaylistItemEntity has no campaign
    # column, so every device sends campaign_id = null. Left as-is that makes campaign_id
    # NULL on every rollup row, and since all campaign analytics filter on it, every
    # campaign reports zero plays forever. Derive it here from the playlist the event
    # names -- server side, so it also repairs events already queued on devices.
    # Scoped to the screen's verified org so a forged playlist_id cannot attribute across tenants.
    playlist_ids = {ev.playlist_id for ev in req.events if ev.playlist_id is not None}
    campaign_by_playlist: dict[int, int | None] = {}
    media_by_playlist: dict[int, int | None] = {}
    if playlist_ids:
        campaign_by_playlist = {
            pid: cid
            for pid, cid in db.query(models.Playlist.id, models.Playlist.campaign_id)
            .filter(
                models.Playlist.id.in_(playlist_ids),
                models.Playlist.organization_id == target_org_id,
            )
            .all()
        }
        # Fallback media_id resolution for single-item playlists
        playlist_items = (
            db.query(models.PlaylistItem.playlist_id, models.PlaylistItem.content_id)
            .filter(models.PlaylistItem.playlist_id.in_(playlist_ids))
            .all()
        )
        from collections import defaultdict
        p_items_map = defaultdict(list)
        for pid, cid in playlist_items:
            p_items_map[pid].append(cid)
        for pid, cids in p_items_map.items():
            if len(cids) == 1:
                media_by_playlist[pid] = cids[0]

    values = []
    now = models.utcnow()
    for ev in req.events:
        values.append({
            "event_id": ev.event_id,
            "screen_id": target_screen_id,
            "organization_id": target_org_id,
            "media_id": ev.media_id or media_by_playlist.get(ev.playlist_id),
            "playlist_id": ev.playlist_id,
            "campaign_id": ev.campaign_id or campaign_by_playlist.get(ev.playlist_id),
            "device_started_at": ev.device_started_at,
            "device_finished_at": ev.device_finished_at,
            "corrected_started_at": ev.corrected_started_at,
            "corrected_finished_at": ev.corrected_finished_at,
            "duration_ms": ev.duration_ms,
            "status": ev.status,
            "error_message": ev.error_message,
            "received_at": now
        })
        
    stmt = insert(models.PlayLog).values(values)
    stmt = stmt.on_conflict_do_nothing(index_elements=['event_id'])
    
    result = db.execute(stmt)
    db.commit()

    # Immediately aggregate so stats and proof-of-play cards update live in real-time
    from ..worker import aggregate_play_logs_sync
    aggregate_play_logs_sync(db)
    
    return {"status": "ok", "inserted": result.rowcount}



@router.post("/resolve-location-link", response_model=schemas.ResolveLinkResponse)
def resolve_location_link(
    payload: schemas.ResolveLinkRequest,
    tenant: TenantScope = Depends(get_tenant_scope),
):
    """Coordinates for a pasted Google Maps link.

    Deliberately not a Google API call: every form of Maps URL already carries the
    coordinate, so this needs no key and no billing account. Short links are resolved by
    following the redirect, which is a plain HTTP request.
    """
    try:
        latitude, longitude, name = parse_maps_link(payload.link)
    except MapsLinkError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return schemas.ResolveLinkResponse(latitude=latitude, longitude=longitude, name=name)


@router.post("/{screen_id}/bring-to-front")
async def bring_to_front(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Two delivery paths, on purpose: the publish reaches a screen holding a websocket
    # right now, and the queued command is picked up at the next sync or heartbeat by one
    # that is not. queue_device_command owns the SETEX -- this used to write the same key
    # itself a few lines below, so the two could disagree about the TTL.
    queued = await queue_device_command(screen.device_id, "bring_to_front", 300) if screen.device_id else False

    published = False
    try:
        redis = database.get_redis()
        payload = json.dumps({"type": "bring_to_front", "command": "launch_app"})
        if screen.device_id:
            await redis.publish(f"screen:{screen.device_id}", payload)
            await redis.publish(f"device:{screen.device_id}", payload)
        await redis.publish(f"screen:{screen.id}", payload)
        if screen.organization_id:
            await redis.publish(
                f"org:{screen.organization_id}",
                json.dumps({"type": "bring_to_front", "device_id": screen.device_id, "screen_id": screen.id}),
            )
        published = True
    except Exception as e:
        logger.warning(f"Failed to publish bring_to_front to redis: {e}")

    try:
        from .websockets import broadcast_in_memory
        payload = json.dumps({"type": "bring_to_front", "command": "launch_app"})
        if screen.device_id:
            await broadcast_in_memory(f"screen:{screen.device_id}", payload)
            await broadcast_in_memory(f"device:{screen.device_id}", payload)
        await broadcast_in_memory(f"screen:{screen.id}", payload)
        if screen.organization_id:
            await broadcast_in_memory(
                f"org:{screen.organization_id}",
                json.dumps({"type": "bring_to_front", "device_id": screen.device_id, "screen_id": screen.id}),
            )
        published = True
    except Exception as e:
        logger.warning(f"Failed to broadcast bring_to_front in-memory: {e}")

    if not queued and not published:
        # Neither path is available, so the command is going nowhere. Saying "ok" here is
        # what made this button look like flaky hardware.
        raise HTTPException(
            status_code=503,
            detail="Could not reach the message broker; the screen was not notified.",
        )

    return {"status": "ok", "message": "Bring to front command sent"}

