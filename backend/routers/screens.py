import logging
import os
import random
import string
from datetime import datetime, timedelta, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..limiter import limiter
from .. import google_device
from ..media_selection import select_rendition
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


def verify_device_auth(device_id: str, credentials: HTTPAuthorizationCredentials | None, db: Session) -> models.Screen:
    screen = db.query(models.Screen).filter(models.Screen.device_id == device_id).first()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if screen.device_secret_hash:
        if not credentials:
            raise HTTPException(status_code=401, detail="Authentication required")
        try:
            from .auth import ALGORITHM, get_secret_key
            from jose import jwt, JWTError
            payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
            sub = payload.get("sub")
            if sub != f"device:{device_id}":
                raise HTTPException(status_code=401, detail="Token device mismatch")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    return screen


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
        "google": google_device.is_configured(),
        # Always available. Listed rather than assumed so the player renders from one
        # answer instead of hard-coding two of the three.
        "password": True,
        "pair_code": True,
    }


@router.post("/register", response_model=schemas.RegisterResponse)
def register_tv(req: schemas.RegisterRequest, db: Session = Depends(database.get_db)):
    db_screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id).first()
    if db_screen and db_screen.status != "waiting_pairing":
        return db_screen
    if not db_screen:
        db_screen = models.Screen(device_id=req.device_id, status="waiting_pairing")
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
    """Reject the caller when the organisation is already at its plan's screen limit.

    Every path that binds a new screen to an organisation has to call this, or that path
    becomes a quota bypass: unlimited screens on a limited plan. An organisation with no
    plan is deliberately unbounded.
    """
    organization = db.query(models.Organization).filter(
        models.Organization.id == organization_id
    ).one()
    plan = db.query(models.Plan).filter(models.Plan.id == organization.plan_id).first()
    if not plan:
        return
    screen_count = db.query(models.Screen).filter(
        models.Screen.organization_id == organization_id,
        models.Screen.status != "waiting_pairing",
    ).count()
    if screen_count >= plan.max_screens:
        raise HTTPException(
            status_code=409,
            detail=f"Screen limit reached ({plan.max_screens} on {plan.name}). Upgrade your plan to {action}.",
        )


@router.post("/pair", response_model=schemas.ScreenResponse)
def pair_screen(
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

    ensure_screen_quota(scope.db, scope.organization_id, "pair another screen")

    db_screen.status = "offline"
    db_screen.organization_id = scope.organization_id
    # Approved on the spot: redeeming a code requires an authenticated operator at the
    # dashboard, which is the same confirmation the approval queue exists to collect.
    db_screen.approved_at = models.utcnow()
    db_screen.name = f"Screen {db_screen.pair_code}"
    db_screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(db_screen)
    return db_screen


def bind_screen_to_org(
    db: Session,
    *,
    device_id: str,
    user: models.User,
    name: str | None,
    conflict_error: HTTPException,
    how: str,
) -> models.Screen:
    """Claim `device_id` for `user`'s organisation, applying every guard /pair gets free.

    Shared by the two routes that bind a screen from a credential presented on the TV
    itself -- the password sign-in and the Google device flow. It lives here rather than
    being repeated in each because the checks below are the entire security boundary for
    an endpoint the device reaches with no prior credential: a guard added to one caller
    and forgotten in the other is a tenant leak, not a cosmetic inconsistency.

    `conflict_error` is supplied by the caller so each route can answer a cross-tenant
    attempt with the same generic message it uses for a bad credential, rather than
    confirming that a device id exists.
    """
    if user.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="This account cannot add screens")
    if not user.organization_id:
        raise HTTPException(status_code=403, detail="This account has no workspace")

    screen = db.query(models.Screen).filter(models.Screen.device_id == device_id).first()

    if screen and screen.organization_id not in (None, user.organization_id):
        # A device already belonging to another organisation must never be re-homed by
        # signing in with a different organisation's account: the screen would move
        # tenants and go dark for its rightful owner. These routes are reachable without
        # any prior device credential, so this is the only place the boundary holds.
        logger.warning(
            "Rejected cross-tenant claim for device %s: owned by org %s, user belongs to org %s",
            device_id, screen.organization_id, user.organization_id,
        )
        raise conflict_error

    # A screen that is new or still waiting to be paired is not yet counted against the
    # plan. Re-claiming a device this organisation already owns is not a new screen.
    if not screen or screen.status == "waiting_pairing":
        ensure_screen_quota(db, user.organization_id, "add another screen")

    if not screen:
        screen = models.Screen(device_id=device_id)
        db.add(screen)

    screen.organization_id = user.organization_id
    screen.status = "offline"
    # approved_at is deliberately NOT set here. This is the self-service path: somebody
    # standing at the TV claimed the organisation on their own, so an operator confirms it
    # from the dashboard before it plays anything. Re-claiming a screen that is already
    # approved leaves the existing timestamp alone, so a factory reset or a re-sign-in does
    # not knock a working screen back into the queue.
    screen.name = (name or "").strip() or screen.name or f"Screen {device_id[:6]}"
    # Drop any code minted by an earlier /register: the screen is claimed now, and a stale
    # code left in place could still be redeemed by somebody else.
    screen.pair_code = None
    screen.pair_code_expires_at = None
    screen.assignment_updated_at = models.utcnow()

    db.commit()
    db.refresh(screen)
    logger.info("Device %s %s to org %s by %s", device_id, how, user.organization_id, user.username)
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

    user = db.query(models.User).filter(models.User.username == req.username).first()
    if not user or not user.is_active or not verify_password(req.password, user.hashed_password):
        raise CREDENTIALS_ERROR

    return bind_screen_to_org(
        db,
        device_id=req.device_id,
        user=user,
        name=req.name,
        conflict_error=CREDENTIALS_ERROR,
        how="signed in",
    )


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
    """Begin a Google sign-in for this TV and hand back the code to put on screen.

    The TV never sees the client secret or the device_code: it gets a user_code to display
    and an opaque poll token. Signage APKs are sideloaded and unpacked as a matter of
    routine, so anything in the APK is public.
    """
    from .auth import create_access_token

    if not google_device.is_configured():
        # Not an error state for the product -- the password and pairing-code routes still
        # work -- so the player shows this as a plain message pointing at them, rather
        # than as a failure worth retrying.
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
        },
        # Dies exactly when Google's own code does, so an abandoned attempt cannot be
        # resumed later against a code that has since been reissued to another screen.
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
    """Has the installer approved on their phone yet? If so, bind the screen.

    Deliberately not rate limited. A TV is *supposed* to call this every few seconds for
    up to fifteen minutes -- that is what the grant specifies -- so a per-minute cap here
    would break the only flow it guards.
    """
    from jose import JWTError, jwt

    from .auth import ALGORITHM, get_secret_key

    INVALID = HTTPException(status_code=401, detail="This sign-in has expired. Start again on the TV.")

    try:
        claims = jwt.decode(req.poll_token, get_secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        raise INVALID
    # A session token is also signed with this key and would otherwise decode cleanly
    # here; the type marker is what stops one being replayed as the other.
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
        # pending / slow_down / denied / expired all pass straight through to the player,
        # which is the only party that can act on them.
        return schemas.GoogleDevicePollResponse(status=result["status"])

    email = result.get("email") or ""
    if not email or not result.get("email_verified"):
        # An unverified address proves nothing about who owns it, so it must never be
        # allowed to match an account.
        raise HTTPException(
            status_code=403,
            detail="That Google account has no verified email address.",
        )

    # Google authenticates a person; it does not authorise them. The account must already
    # exist in this workspace -- otherwise any Google address on earth could bind a screen
    # into somebody's tenant. Matched case-insensitively because Google lowercases what it
    # returns and the profile field does not.
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
        conflict_error=HTTPException(
            status_code=403,
            detail="This screen belongs to another workspace.",
        ),
        how="signed in with Google",
    )
    return schemas.GoogleDevicePollResponse(
        status="bound",
        screen=schemas.ScreenResponse.model_validate(screen),
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

    screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id).first()

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
    screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id).first()
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
        if presence is not None:
            is_online = presence.get(screen.id, False)
        else:
            # Fallback keeps the dashboard truthful when Redis is unavailable.
            is_online = _is_recent(screen.last_seen)
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
    return db_screen


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
    try:
        redis = database.get_redis()
        ttl = screen_offline_after_seconds()
        await redis.setex(f"screen_presence:{db_screen.id}", ttl, "online")
    except Exception as exc:  # noqa: BLE001 - any Redis failure must stay non-fatal
        logger.warning("Redis presence write failed for screen %s: %s", db_screen.id, exc)

    return {
        "status": "ok", 
        "screen_status": db_screen.status,
        "server_time_ms": int(models.utcnow().timestamp() * 1000),
        "screen_id": db_screen.id,
        "organization_id": db_screen.organization_id
    }


@router.post("/{screen_id}/approve", response_model=schemas.ScreenResponse)
def approve_screen(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    """Let a self-enrolled screen into the fleet.

    Owner-only rather than owner-or-editor: this is the step that decides a device is
    genuinely ours, and it is the only thing standing between a Google account that can
    sign in and a screen that plays our content.
    """
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    if screen.approved_at is None:
        screen.approved_at = models.utcnow()
        # The player polls with `since`; without a fresh marker an approved screen would
        # keep getting 204 and stay dark until something else touched the row.
        screen.assignment_updated_at = models.utcnow()
        scope.db.commit()
        scope.db.refresh(screen)
        logger.info("Screen %s approved by %s", screen_id, scope.user.username)
    return screen


@router.post("/{screen_id}/revoke-approval", response_model=schemas.ScreenResponse)
def revoke_screen_approval(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner")),
):
    """Put a screen back in the queue, e.g. a device that left the estate.

    Kept rather than only offering delete: deleting loses the play history that billing
    and the client reports are built from.
    """
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    screen.approved_at = None
    screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(screen)
    logger.info("Screen %s approval revoked by %s", screen_id, scope.user.username)
    return screen


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
    
    import json
    try:
        redis = database.get_redis()
        await redis.publish(f"screen:{screen.device_id}", json.dumps({"type": "playlist_changed"}))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish to redis: {e}")
    
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
    
    import json
    try:
        redis = database.get_redis()
        await redis.publish(f"screen:{screen.device_id}", json.dumps({"type": "playlist_changed"}))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish to redis: {e}")
    
    return {"status": "ok"}


@router.get("/player-version", response_model=schemas.AppVersionResponse)
def player_version(db: Session = Depends(database.get_db)):
    # `db` was missing, so every call raised TypeError and the endpoint answered 500.
    # The sync path passed it correctly, which is why updates still reached devices and
    # hid the breakage here.
    return current_app_version(db)


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
            
    # For group, we need to check screen's group and its parents
    screen_group_ids = []
    current_group = screen.group
    while current_group:
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
        
    # 3. Hierarchical Group Inheritance
    current_group = screen.group
    while current_group:
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
def sync_tv(
    device_id: str,
    since: datetime | None = None,
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    screen = verify_device_auth(device_id, credentials, db)

    # Not yet let into the fleet: answer with the state and nothing else. Deliberately
    # ahead of the 204 short-circuit below -- a screen that was playing before it was
    # un-approved must be told now, not left running a cached playlist until something
    # else happens to change its marker.
    #
    # organization_id guards the condition: a screen that has not been claimed at all also
    # has no approved_at, and answering "pending_approval" for it would hide the
    # waiting_pairing state the player uses to decide to show its pairing code -- a brand
    # new TV would sit blank instead, and could never be paired.
    if screen.organization_id is not None and screen.approved_at is None:
        return schemas.SyncResponse(
            status="pending_approval",
            playlist=None,
            fit_mode=screen.fit_mode or "contain",
            maintenance_pin=screen.maintenance_pin,
            sync_interval_seconds=player_sync_interval_seconds(),
        )

    playlist_id = resolve_screen_playlist(screen, db)
    playlist = (
        db.query(models.Playlist)
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
    if since and marker <= as_aware_utc(since):
        return Response(
            status_code=204,
            headers={"X-Sync-Interval-Seconds": str(player_sync_interval_seconds())},
        )

    playlist_payload = None
    if playlist:
        playlist_payload = schemas.PlaylistResponse.model_validate(playlist)
        valid_items = []
        for item in playlist_payload.items:
            if item.content.status == "ready":
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
        maintenance_pin=screen.maintenance_pin,
        operating_mode=screen.operating_mode or "always",
        operating_hours=screen.operating_hours,
        playlist=playlist_payload,
        playlist_updated_at=marker,
        status=screen.status,
        app_version=current_app_version(db, screen.target_version_code or (screen.group.target_version_code if screen.group else None)),
        sync_interval_seconds=player_sync_interval_seconds(),
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

    if screen.id != req.screen_id:
        logger.warning(f"Device {device_id} (screen {screen.id}) attempted to post logs for screen {req.screen_id}")
        raise HTTPException(status_code=403, detail="Screen ID mismatch")

    if screen.organization_id != req.organization_id:
        logger.warning(f"Device {device_id} (org {screen.organization_id}) attempted to post logs for org {req.organization_id}")
        raise HTTPException(status_code=403, detail="Organization ID mismatch")

    if not req.events:
        return {"status": "ok", "inserted": 0}

    from sqlalchemy.dialects.postgresql import insert

    # The player cannot attribute a play to a campaign: PlaylistItemEntity has no campaign
    # column, so every device sends campaign_id = null. Left as-is that makes campaign_id
    # NULL on every rollup row, and since all campaign analytics filter on it, every
    # campaign reports zero plays forever. Derive it here from the playlist the event
    # names -- server side, so it also repairs events already queued on devices.
    # Scoped to the caller's org so a forged playlist_id cannot attribute across tenants.
    playlist_ids = {ev.playlist_id for ev in req.events if ev.playlist_id is not None}
    campaign_by_playlist: dict[int, int | None] = {}
    if playlist_ids:
        campaign_by_playlist = {
            pid: cid
            for pid, cid in db.query(models.Playlist.id, models.Playlist.campaign_id)
            .filter(
                models.Playlist.id.in_(playlist_ids),
                models.Playlist.organization_id == req.organization_id,
            )
            .all()
        }

    values = []
    now = models.utcnow()
    for ev in req.events:
        values.append({
            "event_id": ev.event_id,
            "screen_id": req.screen_id,
            "organization_id": req.organization_id,
            "media_id": ev.media_id,
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
