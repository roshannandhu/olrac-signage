"""Staged-rollout decisions — pure logic, no database, no device.

Run directly:  python tests/test_rollout_policy.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import rollout  # noqa: E402


def screen(target=7, failures=0, status=None):
    return SimpleNamespace(
        target_version_code=target,
        update_failure_count=failures,
        update_status=status,
    )


def test_success_on_the_pinned_version_clears_the_pin_status():
    s = screen(target=7, failures=2)
    assert rollout.apply_update_status(s, "success", 7) is None
    assert s.update_status is None, "the target was reached; nothing is outstanding"
    assert s.update_failure_count == 0
    assert s.target_version_code == 7, "a reached pin stays; it is the running version"


def test_success_for_a_different_version_does_not_clear_the_pin_status():
    # A device confirming version 6 says nothing about whether it reached the pinned 7.
    s = screen(target=7)
    rollout.apply_update_status(s, "success", 6)
    assert s.update_status == "success"


def test_two_failures_do_not_roll_back():
    # One bad night -- a CDN blip, a reboot mid-download -- must not abandon a build, or
    # the canary ring can never distinguish noise from a genuinely broken APK.
    s = screen(target=7)
    assert rollout.apply_update_status(s, "failed", 7) is None
    assert s.update_failure_count == 1
    assert rollout.apply_update_status(s, "failed", 7) is None
    assert s.update_failure_count == 2
    assert s.target_version_code == 7, "still trying"
    assert s.update_status == "failed"


def test_third_failure_rolls_back():
    s = screen(target=7)
    for _ in range(rollout.ROLLBACK_THRESHOLD - 1):
        rollout.apply_update_status(s, "failed", 7)
    reason = rollout.apply_update_status(s, "failed", 7)

    assert reason is not None and "version 7" in reason
    assert s.target_version_code is None, (
        "the pin must be dropped, or the screen re-downloads an APK that cannot install "
        "on every heartbeat, forever"
    )
    assert s.update_status == rollout.ROLLED_BACK
    assert s.update_failure_count == 0, "counter resets so a later pin starts clean"


def test_failures_must_be_consecutive():
    s = screen(target=7)
    rollout.apply_update_status(s, "failed", 7)
    rollout.apply_update_status(s, "failed", 7)
    rollout.apply_update_status(s, "success", 7)
    assert s.update_failure_count == 0
    rollout.apply_update_status(s, "failed", 7)
    assert s.target_version_code == 7, "one failure after a success is not three in a row"


def test_repin_resets_the_failure_count():
    s = screen(target=7, failures=2, status="failed")
    rollout.repin(s, 8)
    assert s.target_version_code == 8
    assert s.update_failure_count == 0, (
        "without the reset a fresh build would be abandoned after a single failure"
    )
    assert s.update_status is None


def test_in_flight_states_are_recorded_without_judgement():
    for state in ("pending", "downloading", "installing"):
        s = screen(target=7)
        assert rollout.apply_update_status(s, state, 7) is None
        assert s.update_status == state
        assert s.update_failure_count == 0
        assert s.target_version_code == 7


def test_none_status_changes_nothing():
    s = screen(target=7, failures=1, status="failed")
    assert rollout.apply_update_status(s, None, 7) is None
    assert s.update_status == "failed"
    assert s.update_failure_count == 1


def test_null_failure_count_is_tolerated():
    # Rows created before the column existed read back as None under some drivers.
    s = screen(target=7, failures=None)
    rollout.apply_update_status(s, "failed", 7)
    assert s.update_failure_count == 1


def test_rollout_states_are_ordered_draft_canary_released():
    assert rollout.ROLLOUT_STATES == ("draft", "canary", "released")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("rollout policy: all checks passed")
