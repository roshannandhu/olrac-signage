import logging
import os
import random
import string
from datetime import datetime, timedelta, timezone

import boto3
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..media_selection import select_rendition
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


def is_s3_enabled() -> bool:
    key = os.getenv("AWS_ACCESS_KEY_ID")
    return bool(key and key != "mock")


def resolve_media_url(value: str | None) -> str | None:
    if not value or not value.startswith("s3://") or not is_s3_enabled():
        return value
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": os.getenv("S3_BUCKET_NAME", "olrac-media"),
                "Key": value.removeprefix("s3://"),
            },
            ExpiresIn=3600,
        )
    except Exception as exc:
        print(f"Failed to generate presigned URL: {exc}")
        return value


def as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def current_app_version(db: Session, target_version_code: int = None) -> schemas.AppVersionResponse:
    if target_version_code:
        release = db.query(models.AppRelease).filter(models.AppRelease.version_code == target_version_code).first()
        if release:
            return schemas.AppVersionResponse(
                version_code=release.version_code,
                version_name=release.version_name,
                apk_url=release.apk_url,
                mandatory=release.mandatory,
            )
            
    # Fallback to latest global release
    release = db.query(models.AppRelease).order_by(models.AppRelease.version_code.desc()).first()
    if release:
        return schemas.AppVersionResponse(
            version_code=release.version_code,
            version_name=release.version_name,
            apk_url=release.apk_url,
            mandatory=release.mandatory,
        )
        
    return schemas.AppVersionResponse(
        version_code=int(os.getenv("PLAYER_VERSION_CODE", "1")),
        version_name=os.getenv("PLAYER_VERSION_NAME", "1.0"),
        apk_url=os.getenv("PLAYER_APK_URL") or None,
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


@router.post("/register", response_model=schemas.ScreenResponse)
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
    db_screen.name = f"Screen {db_screen.pair_code}"
    db_screen.assignment_updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(db_screen)
    return db_screen


@router.post("/sign-in", response_model=schemas.ScreenResponse)
def sign_in_screen(req: schemas.ScreenSignInRequest, db: Session = Depends(database.get_db)):
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
    if user.role not in ("owner", "editor"):
        raise HTTPException(status_code=403, detail="This account cannot add screens")
    if not user.organization_id:
        raise HTTPException(status_code=403, detail="This account has no workspace")

    screen = db.query(models.Screen).filter(models.Screen.device_id == req.device_id).first()

    if screen and screen.organization_id not in (None, user.organization_id):
        # A device already belonging to another organisation must never be re-homed by
        # signing in with a different organisation's account: the screen would move
        # tenants and go dark for its rightful owner. This endpoint is reachable without
        # any prior device credential, so this is the only place the boundary holds.
        # Same generic error as bad credentials, so device ids cannot be probed.
        logger.warning(
            "Rejected cross-tenant sign-in for device %s: owned by org %s, user belongs to org %s",
            req.device_id, screen.organization_id, user.organization_id,
        )
        raise CREDENTIALS_ERROR

    # A screen that is new or still waiting to be paired is not yet counted against the
    # plan. Re-signing in on a device this organisation already owns is not a new screen.
    if not screen or screen.status == "waiting_pairing":
        ensure_screen_quota(db, user.organization_id, "add another screen")

    if not screen:
        screen = models.Screen(device_id=req.device_id)
        db.add(screen)

    screen.organization_id = user.organization_id
    screen.status = "offline"
    screen.name = (req.name or "").strip() or screen.name or f"Screen {req.device_id[:6]}"
    # Drop any code minted by an earlier /register: the screen is claimed now, and a stale
    # code left in place could still be redeemed by somebody else.
    screen.pair_code = None
    screen.pair_code_expires_at = None
    screen.assignment_updated_at = models.utcnow()

    db.commit()
    db.refresh(screen)
    logger.info("Device %s signed in to org %s by %s", req.device_id, user.organization_id, user.username)
    return screen


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
def auth_device(req: schemas.DeviceAuthRequest, db: Session = Depends(database.get_db)):
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
    screens = scope.query(models.Screen).order_by(models.Screen.name).all()
    candidates = [s for s in screens if s.status != "waiting_pairing"]

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
    return screens


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
    if "group_id" in screen.model_fields_set:
        db_screen.group_id = screen.group_id
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

    for field in ("name", "orientation", "group_id", "target_version_code"):
        if field in fields:
            setattr(db_screen, field, getattr(patch, field))

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
    if hasattr(req, "update_status") and req.update_status is not None:
        db_screen.update_status = req.update_status
        if req.update_status == "success" and hasattr(req, "version_code") and req.version_code is not None:
            # If successfully updated to target, we can clear the status
            if db_screen.target_version_code == req.version_code:
                db_screen.update_status = None
        db_screen.device_version = req.app_version
    if req.storage_used:
        db_screen.storage_used = req.storage_used
        
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
def player_version():
    return current_app_version()


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
                valid_items.append(item)
        playlist_payload.items = valid_items

    return schemas.SyncResponse(
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

    # The token's subject is "device:{device_id}". We must verify the token, then ensure
    # the device matches the screen_id and organization_id in the payload to prevent cross-tenant injection.
    from jose import jwt, JWTError
    from .auth import ALGORITHM, get_secret_key
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    try:
        payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub or not sub.startswith("device:"):
            raise HTTPException(status_code=401, detail="Invalid token")
        device_id = sub.split(":", 1)[1]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    screen = db.query(models.Screen).filter(models.Screen.device_id == device_id).first()
    if not screen or not screen.device_secret_hash:
        raise HTTPException(status_code=401, detail="Screen not found or revoked")
        
    if screen.id != req.screen_id:
        logger.warning(f"Device {device_id} (screen {screen.id}) attempted to post logs for screen {req.screen_id}")
        raise HTTPException(status_code=403, detail="Screen ID mismatch")
        
    if screen.organization_id != req.organization_id:
        logger.warning(f"Device {device_id} (org {screen.organization_id}) attempted to post logs for org {req.organization_id}")
        raise HTTPException(status_code=403, detail="Organization ID mismatch")

    if not req.events:
        return {"status": "ok", "inserted": 0}

    from sqlalchemy.dialects.postgresql import insert
    
    values = []
    now = models.utcnow()
    for ev in req.events:
        values.append({
            "event_id": ev.event_id,
            "screen_id": req.screen_id,
            "organization_id": req.organization_id,
            "media_id": ev.media_id,
            "playlist_id": ev.playlist_id,
            "campaign_id": ev.campaign_id,
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

