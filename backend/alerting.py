"""What counts as something worth waking an operator for.

The dashboard already worked out these six conditions, but it worked them out *in the
browser*, from a list it polled every thirty seconds while a tab happened to be open. That
is a report, not an alarm: nobody watches a dashboard at 2am, and a screen that dropped at
midnight was simply a red row waiting to be noticed in the morning.

The rules move here so the server reaches the same verdict without anyone looking, which is
what lets a notification be sent at all. Kept free of SQLAlchemy and of the session so the
decisions can be tested against plain objects -- the reconciler in worker.py owns the
database, this module owns the judgement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

CRITICAL = "critical"
WARNING = "warning"

# Kinds. Stable strings: they are the dedupe key prefix and are stored on rows, so
# renaming one orphans every alert already raised under the old name.
SCREEN_OFFLINE = "screen_offline"
PLAYBACK_ERROR = "playback_error"
SCREEN_IDLE = "screen_idle"
LOW_STORAGE = "low_storage"
UPDATE_FAILED = "update_failed"
CONTENT_FAILED = "content_failed"

# A screen reporting less than this has no room to cache what it is about to be told to
# play, so it will start failing downloads shortly.
LOW_STORAGE_MB = 500

# How long a screen must be unreachable before it is worth telling someone.
#
# Deliberately far longer than SCREEN_OFFLINE_AFTER_SECONDS, which exists to grey out a
# tile in the dashboard. A TV rebooting, a router restarting, or a shop's power dipping all
# produce a gap of a minute or two many times a week; alerting on those trains people to
# ignore the alerts, which is worse than not sending them.
OFFLINE_ALERT_AFTER = timedelta(minutes=15)


@dataclass(frozen=True)
class AlertCondition:
    """One thing that is currently wrong, as the server sees it."""

    kind: str
    severity: str
    title: str
    detail: str
    screen_id: Optional[int] = None
    content_id: Optional[int] = None

    @property
    def dedupe_key(self) -> str:
        """Identity of the *situation*, not of this observation.

        The reconciler runs every minute. Without a stable key each pass would raise "Lobby
        TV is offline" again, and an operator whose TV was unplugged for a weekend would
        wake to some 2,880 identical messages. Keyed this way, the second pass recognises
        the alert it raised on the first and leaves it alone.
        """
        target = self.screen_id if self.screen_id is not None else self.content_id
        return f"{self.kind}:{target}"


def _screen_label(screen) -> str:
    name = getattr(screen, "name", None)
    if name:
        return name
    location = getattr(screen, "location", None)
    if location:
        return f"Screen at {location}"
    return f"Screen {getattr(screen, 'id', '?')}"


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Naive timestamps read back from some drivers are UTC; say so explicitly.

    Comparing a naive value against an aware `now` raises TypeError, which inside the
    reconciler would abort the sweep for the whole fleet.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def evaluate_screen(screen, now: datetime) -> list[AlertCondition]:
    """Everything currently wrong with one screen."""
    conditions: list[AlertCondition] = []
    label = _screen_label(screen)
    status = getattr(screen, "status", None)

    # A screen that has never been paired is not part of the fleet and cannot be "offline".
    if status == "waiting_pairing":
        return conditions

    last_seen = _as_utc(getattr(screen, "last_seen", None))
    offline_for = (now - last_seen) if last_seen else None
    if offline_for is not None and offline_for >= OFFLINE_ALERT_AFTER:
        minutes = int(offline_for.total_seconds() // 60)
        human = f"{minutes // 60}h {minutes % 60}m" if minutes >= 60 else f"{minutes}m"
        conditions.append(AlertCondition(
            kind=SCREEN_OFFLINE,
            severity=CRITICAL,
            title=f"{label} is offline",
            detail=f"No contact for {human}. It is not reporting plays and cannot receive new content.",
            screen_id=screen.id,
        ))
        # Everything below describes the last thing a *reachable* screen told us. Repeating
        # it while the screen is unreachable buries the one fact that matters.
        return conditions

    if getattr(screen, "last_error", None):
        conditions.append(AlertCondition(
            kind=PLAYBACK_ERROR,
            severity=CRITICAL,
            title=f"{label} reported a playback error",
            detail=str(screen.last_error)[:500],
            screen_id=screen.id,
        ))

    # Online but idle is worse than offline: the screen looks healthy in the fleet grid and
    # is selling nothing.
    if status == "online" and getattr(screen, "playback_state", None) == "idle":
        conditions.append(AlertCondition(
            kind=SCREEN_IDLE,
            severity=CRITICAL,
            title=f"{label} is on but not playing",
            detail="The screen is reporting in but nothing is on it. Check that a playlist is assigned and in schedule.",
            screen_id=screen.id,
        ))

    free_mb = getattr(screen, "free_storage_mb", None)
    if free_mb is not None and free_mb < LOW_STORAGE_MB:
        conditions.append(AlertCondition(
            kind=LOW_STORAGE,
            severity=WARNING,
            title=f"{label} is low on storage",
            detail=f"{free_mb} MB free. New content may fail to cache for offline playback.",
            screen_id=screen.id,
        ))

    if getattr(screen, "update_status", None) == "failed":
        running = getattr(screen, "app_version", None) or "an unknown version"
        wanted = getattr(screen, "target_version_code", None) or "the latest build"
        conditions.append(AlertCondition(
            kind=UPDATE_FAILED,
            severity=WARNING,
            title=f"{label} failed to update",
            detail=f"Still on {running}, wanted {wanted}. It retries, and is unpinned automatically after three failures.",
            screen_id=screen.id,
        ))

    return conditions


def evaluate_content(content) -> list[AlertCondition]:
    """Media that cannot be played by anything."""
    if getattr(content, "status", None) != "failed":
        return []
    name = getattr(content, "name", None) or f"Asset {content.id}"
    return [AlertCondition(
        kind=CONTENT_FAILED,
        severity=WARNING,
        title=f"“{name}” failed to process",
        detail=(getattr(content, "failed_reason", None)
                or "Transcoding did not complete, so no screen can play this asset."),
        content_id=content.id,
    )]


def evaluate_all(screens: Iterable, contents: Iterable, now: datetime) -> dict[str, AlertCondition]:
    """Every current condition for one organisation, keyed for reconciliation."""
    found: dict[str, AlertCondition] = {}
    for screen in screens:
        for condition in evaluate_screen(screen, now):
            found[condition.dedupe_key] = condition
    for content in contents:
        for condition in evaluate_content(content):
            found[condition.dedupe_key] = condition
    return found
