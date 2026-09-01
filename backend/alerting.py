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

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

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
CAMPAIGN_ENDING = "campaign_ending"

# How much notice an operator gets that a booking is about to finish. A week is enough to
# reach the advertiser and sell the extension; a day is a scramble, and a month is noise
# that gets acknowledged and ignored.
CAMPAIGN_ENDING_WITHIN = timedelta(days=7)

# A screen reporting less than this has no room to cache what it is about to be told to
# play, so it will start failing downloads shortly.
LOW_STORAGE_MB = 500

# How long a screen must be unreachable before it is worth telling someone.
#
# Set aggressively low (1 minute) for immediate operator awareness. The heartbeat
# interval is ~60s, so a screen that misses one cycle is flagged immediately.
OFFLINE_ALERT_AFTER = timedelta(minutes=1)


@dataclass(frozen=True)
class AlertCondition:
    """One thing that is currently wrong, as the server sees it."""

    kind: str
    severity: str
    title: str
    detail: str
    screen_id: Optional[int] = None
    content_id: Optional[int] = None
    # Overrides what the key is built from, without changing what the row points at.
    # A booking alert has to key on the BOOKING: two clients running the same creative
    # would otherwise both key on that content_id, collapse onto one alert, and only the
    # first would ever be raised -- so the second client's campaign ends unnoticed.
    ref: Optional[int] = None

    @property
    def dedupe_key(self) -> str:
        """Identity of the *situation*, not of this observation.

        The reconciler runs every minute. Without a stable key each pass would raise "Lobby
        TV is offline" again, and an operator whose TV was unplugged for a weekend would
        wake to some 2,880 identical messages. Keyed this way, the second pass recognises
        the alert it raised on the first and leaves it alone.
        """
        target = self.ref
        if target is None:
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


def is_scheduled_off(screen, now: datetime) -> bool:
    """Whether this screen is *meant* to be dark right now.

    operating_hours reached the database and the dashboard but nothing ever read it, so a
    shop TV on 09:00-21:00 hours raised a CRITICAL "is offline" every night and a
    "on but not playing" every morning while it woke up. Across a 500-screen fleet that is
    a nightly flood of alerts that are all working as intended -- and an operator who
    learns to swipe the whole category away stops seeing the real ones too.

    Evaluated in the screen's own timezone: "closed at 21:00" means 21:00 where the TV is,
    not on the server. An unknown or malformed zone falls back to UTC rather than raising,
    because the reconciler sweeps the whole fleet in one pass and one bad row must not
    abort the others.
    """
    mode = getattr(screen, "operating_mode", "always") or "always"
    if mode == "always":
        return False
    if mode == "never":
        return True

    windows = getattr(screen, "operating_hours", None)
    # "hours" with nothing configured is not a licence to silence the screen forever.
    if not windows:
        return False

    local = now
    zone = getattr(screen, "timezone", None)
    if zone:
        try:
            from zoneinfo import ZoneInfo

            local = now.astimezone(ZoneInfo(zone))
        except Exception:  # noqa: BLE001 - unknown zone must not abort the sweep
            local = now

    window = windows.get(WEEKDAYS[local.weekday()])
    if not window or len(window) != 2:
        return True

    try:
        start, end = (_minutes(stamp) for stamp in window)
    except (ValueError, AttributeError):
        return False
    minute = local.hour * 60 + local.minute

    # An end before the start is an overnight window (22:00-02:00), which is the normal
    # shape for a bar or a hotel lobby, not a typo.
    if start <= end:
        return not (start <= minute <= end)
    return not (minute >= start or minute <= end)


def _minutes(stamp: str) -> int:
    hours, _, mins = stamp.partition(":")
    return int(hours) * 60 + int(mins)


def evaluate_screen(screen, now: datetime) -> list[AlertCondition]:
    """Everything currently wrong with one screen."""
    conditions: list[AlertCondition] = []
    label = _screen_label(screen)
    status = getattr(screen, "status", None)

    # A screen that has never been paired is not part of the fleet and cannot be "offline".
    if status == "waiting_pairing":
        return conditions

    # Outside its operating hours a screen is supposed to be dark, so neither its silence
    # nor its blank playback is a fault. Checked before every condition below rather than
    # only around the offline one: a screen powering down reports "idle" first and would
    # otherwise trade one false critical for another.
    if is_scheduled_off(screen, now):
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


def evaluate_placement(placement, now: datetime) -> list[AlertCondition]:
    """Warn while there is still time to sell the extension.

    Nothing told an operator a campaign was about to finish, so the first sign was an
    advertiser noticing their advert had stopped -- which is the worst possible moment to
    open a renewal conversation.

    Resolution is automatic: the reconciler closes any alert whose condition stops being
    true, so extending the booking clears this on the next pass without anyone dismissing
    anything.
    """
    ends = getattr(placement, "effective_ends_at", None) or placement.ends_at
    if ends is None:
        return []
    # Already finished is not "ending soon" -- that alert would never resolve, and an
    # operator cannot act on it either.
    if ends <= now or ends - now > CAMPAIGN_ENDING_WITHIN:
        return []

    days = max(0, round((ends - now).total_seconds() / 86400))
    advertiser = getattr(placement, "advertiser", None) or "A client"
    return [AlertCondition(
        kind=CAMPAIGN_ENDING,
        severity=WARNING,
        title=f"{advertiser}'s campaign ends in {days} day{'' if days == 1 else 's'}",
        detail=(
            f"The booking finishes on {ends:%d %b %Y}. Extend it to keep the advert running, "
            "or it will stop playing on every screen it was placed on."
        ),
        content_id=getattr(placement, "content_id", None),
        ref=placement.id,
    )]


def evaluate_all(screens: Iterable, contents: Iterable, now: datetime,
                 placements: Iterable = ()) -> dict[str, AlertCondition]:
    """Every current condition for one organisation, keyed for reconciliation.

    `placements` defaults to empty so the existing callers and tests keep working; the
    worker passes the real list.
    """
    found: dict[str, AlertCondition] = {}
    for screen in screens:
        for condition in evaluate_screen(screen, now):
            found[condition.dedupe_key] = condition
    for content in contents:
        for condition in evaluate_content(content):
            found[condition.dedupe_key] = condition
    for placement in placements:
        for condition in evaluate_placement(placement, now):
            found[condition.dedupe_key] = condition
    return found
