"""Device Authentication Application Service for Android TV hardware devices."""

import logging
import os
import secrets as _secrets
from typing import Optional
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .base import BaseService
from ..repositories.screen_repo import ScreenRepository
from .. import models, database

logger = logging.getLogger(__name__)


def _pending_secret_key(device_id: str) -> str:
    return f"screen_pending_secret:{device_id}"


async def park_device_secret(device_id: str, secret: str, ttl_seconds: int = 300) -> None:
    """Temporarily park a secret in Redis for a newly paired device to collect."""
    if not device_id:
        return
    try:
        await database.get_redis().setex(_pending_secret_key(device_id), ttl_seconds, secret)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not park device secret for %s: %s", device_id, exc)


async def collect_device_secret(device_id: str) -> Optional[str]:
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

    ⚠️ Defaults to ON, which is the wrong posture: a deployment that never sets the
    variable -- a new environment, a restored one, a developer's laptop -- accepts
    unauthenticated device calls from anyone who knows or guesses a device id. A security
    allowance should be switched on deliberately rather than inherited by forgetting.

    It has NOT been flipped yet because the blast radius is a live fleet: any panel still
    holding no device secret stops syncing the moment it changes, and over ten test files
    drive the device endpoints with no credential. Flip it by setting
    ALLOW_LEGACY_DEVICE_AUTH=false once no screen logs the legacy-path warning -- the
    warning below is what tells you that.
    """
    return os.getenv("ALLOW_LEGACY_DEVICE_AUTH", "true").strip().lower() in {"1", "true", "yes"}


def issue_device_secret(screen: models.Screen) -> str:
    """Give this screen a credential of its own and return the plaintext once."""
    from ..routers.auth import get_password_hash

    device_secret = _secrets.token_hex(32)
    screen.device_secret_hash = get_password_hash(device_secret)
    return device_secret


def verify_device_auth(
    device_id: str, credentials: Optional[HTTPAuthorizationCredentials], db: Session
) -> models.Screen:
    """Verify hardware authentication for device endpoints."""
    screen = (
        db.query(models.Screen)
        .filter(models.Screen.device_id == device_id, models.Screen.deleted_at.is_(None))
        .first()
    )
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    if not credentials:
        if not legacy_device_auth_allowed():
            raise HTTPException(status_code=401, detail="Authentication required")
        logger.warning(
            "Screen %s (device %s) authenticated with no credential (legacy path)",
            screen.id,
            device_id,
        )
        screen.authenticated = False
        return screen

    try:
        from ..routers.auth import ALGORITHM, get_secret_key
        from jose import jwt, JWTError

        payload = jwt.decode(credentials.credentials, get_secret_key(), algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub != f"device:{device_id}":
            raise HTTPException(status_code=401, detail="Token device mismatch")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if screen.device_secret_hash is None:
        raise HTTPException(status_code=401, detail="Device credential has been revoked")

    screen.authenticated = True
    return screen


class DeviceAuthService(BaseService):
    """Application Service for TV hardware device authentication."""

    def __init__(self, db: Session, repo: Optional[ScreenRepository] = None):
        super().__init__(db)
        self.repo = repo or ScreenRepository(db)

    def verify_auth(
        self, device_id: str, credentials: Optional[HTTPAuthorizationCredentials]
    ) -> models.Screen:
        return verify_device_auth(device_id, credentials, self.db)

    def issue_secret(self, screen: models.Screen) -> str:
        return issue_device_secret(screen)
