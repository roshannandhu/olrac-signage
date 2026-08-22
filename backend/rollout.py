"""Staged player rollout: which build a screen is offered, and when to give up on one.

Two rules live here, both of them about not breaking 500 TVs at once.

1. **A new release is not live until it is promoted.** `current_app_version` offers the
   highest `version_code` to every screen that has no explicit pin, so while all releases
   were eligible, creating one shipped it to the whole fleet immediately. Only
   `released` rows are eligible for that fallback now; `draft` and `canary` builds reach
   a screen solely through an operator pinning `target_version_code`. That is what makes
   a 5-TV ring possible.

2. **A build that cannot install is abandoned.** A screen that fails to install its
   pinned target three times in a row has its pin dropped and is left on the version it
   is already running. Previously `update_status` was merely overwritten, so a bad APK
   was re-downloaded on every heartbeat for as long as the pin stood.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from . import models

# States a release can be in, in promotion order.
DRAFT = "draft"
CANARY = "canary"
RELEASED = "released"
ROLLOUT_STATES = (DRAFT, CANARY, RELEASED)

# Consecutive failed installs before a screen gives up on its pinned build.
#
# Three rather than one: a single failure is routinely a flat battery of ordinary causes
# -- the CDN blipped, the panel was mid-reboot, storage was briefly full -- and rolling
# back on the first would make the canary ring useless for finding real problems.
ROLLBACK_THRESHOLD = 3

# Terminal and in-flight values the device may report for its update attempt.
FAILED = "failed"
SUCCESS = "success"
ROLLED_BACK = "rolled_back"


def eligible_for_fallback(query):
    """Restrict an AppRelease query to builds that unpinned screens may be offered."""
    # Imported here, not at module scope, so the decision functions below stay free of
    # SQLAlchemy. They are the part worth testing and they now test with no database
    # driver installed at all.
    from . import models

    return query.filter(models.AppRelease.rollout_state == RELEASED)


def apply_update_status(
    screen: "models.Screen",
    status: Optional[str],
    reported_version_code: Optional[int],
) -> Optional[str]:
    """Fold one device-reported update result into `screen`.

    Returns a short human-readable reason when the screen was rolled back, else None.
    The caller commits; this function only mutates the instance so it can be tested
    against a plain object with no session.
    """
    if status is None:
        return None

    if status == SUCCESS:
        screen.update_failure_count = 0
        # Clear the pin's status only when the device confirms the version we asked for.
        # A success report for some other version_code says nothing about this target.
        if (
            reported_version_code is not None
            and screen.target_version_code == reported_version_code
        ):
            screen.update_status = None
        else:
            screen.update_status = status
        return None

    if status == FAILED:
        screen.update_failure_count = (screen.update_failure_count or 0) + 1
        if screen.update_failure_count >= ROLLBACK_THRESHOLD:
            abandoned = screen.target_version_code
            # Drop the pin. The screen keeps running whatever it successfully installed
            # last; it simply stops trying to reach a build it cannot install. A pinned
            # canary therefore cannot wedge itself, and nothing propagates to the fleet
            # because a canary build was never eligible for the global fallback.
            screen.target_version_code = None
            screen.update_failure_count = 0
            screen.update_status = ROLLED_BACK
            return (
                f"rolled back after {ROLLBACK_THRESHOLD} failed attempts "
                f"to install version {abandoned}"
            )
        screen.update_status = status
        return None

    # pending / downloading / installing -- in flight, nothing to decide yet.
    screen.update_status = status
    return None


def repin(screen: "models.Screen", version_code: Optional[int]) -> None:
    """Point a screen at a build, clearing any state from the previous attempt.

    Without the reset, a screen that had already failed twice would roll back after a
    single failure of the *next* build it was given.
    """
    screen.target_version_code = version_code
    screen.update_failure_count = 0
    screen.update_status = None
