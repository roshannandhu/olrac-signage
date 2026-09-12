"""Screen Telemetry, Versioning & Remote Command Management Service."""

import logging
import os
import time
from typing import Optional, Tuple, Dict
from sqlalchemy.orm import Session

from .base import BaseService
from ..repositories.screen_repo import ScreenRepository
from .. import models, schemas, database, rollout

logger = logging.getLogger(__name__)

_IN_MEMORY_COMMANDS: Dict[str, Tuple[str, float]] = {}


def _command_key(device_id: str) -> str:
    return f"screen_cmd:{device_id}"


def player_sync_interval_seconds() -> int:
    try:
        configured = int(os.getenv("PLAYER_SYNC_INTERVAL_SECONDS", "60"))
    except ValueError:
        configured = 60
    return max(15, min(configured, 3600))


def screen_offline_after_seconds() -> int:
    """Delegated to alerting, which owns the definition.

    Two copies of this drifted apart once already -- the listing called a screen offline at
    ninety seconds while the alert fired at sixty, so the dashboard showed "screen is
    offline" beside a green Online badge. It lives in alerting because that module imports
    nothing but the standard library, so the dependency can only point this way.
    """
    from ..alerting import offline_after_seconds

    return offline_after_seconds()


def _release_response(release: models.AppRelease) -> schemas.AppVersionResponse:
    return schemas.AppVersionResponse(
        version_code=release.version_code,
        version_name=release.version_name,
        apk_url=release.apk_url,
        sha256=release.sha256,
        mandatory=release.mandatory,
    )


def current_app_version(
    db: Session, target_version_code: Optional[int] = None
) -> schemas.AppVersionResponse:
    """Resolve the appropriate app release version for a TV screen."""
    if target_version_code:
        release = (
            db.query(models.AppRelease)
            .filter(models.AppRelease.version_code == target_version_code)
            .first()
        )
        if release:
            return _release_response(release)

    # Fallback to the latest promoted release
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


async def queue_device_command(device_id: str, command: str, ttl_seconds: int = 300) -> bool:
    """Queue a one-shot remote command for a screen with in-memory and Redis persistence."""
    if not device_id:
        return False
    _IN_MEMORY_COMMANDS[device_id] = (command, time.time() + ttl_seconds)
    try:
        await database.get_redis().setex(_command_key(device_id), ttl_seconds, command)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not queue command %r in Redis for device %s: %s (using in-memory fallback)",
            command,
            device_id,
            exc,
        )
        return True


async def pop_device_command(device_id: str) -> Optional[str]:
    """Take the pending command for this device, consuming it."""
    if not device_id:
        return None
    now = time.time()
    in_memory_val = None
    in_memory = _IN_MEMORY_COMMANDS.pop(device_id, None)
    if in_memory and in_memory[1] > now:
        in_memory_val = in_memory[0]

    redis_val = None
    try:
        redis = database.get_redis()
        value = await redis.get(_command_key(device_id))
        if value is not None:
            await redis.delete(_command_key(device_id))
            redis_val = value.decode("utf-8") if isinstance(value, bytes) else str(value)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read pending command from Redis for device %s: %s", device_id, exc)

    return in_memory_val or redis_val


class ScreenTelemetryService(BaseService):
    """Application Service for TV device telemetry, remote commands, and version checks."""

    def __init__(self, db: Session, repo: Optional[ScreenRepository] = None):
        super().__init__(db)
        self.repo = repo or ScreenRepository(db)

    def get_app_version(self, target_version_code: Optional[int] = None) -> schemas.AppVersionResponse:
        return current_app_version(self.db, target_version_code)

    async def queue_command(self, device_id: str, command: str, ttl: int = 300) -> bool:
        return await queue_device_command(device_id, command, ttl)

    async def pop_command(self, device_id: str) -> Optional[str]:
        return await pop_device_command(device_id)
