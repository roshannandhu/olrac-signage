"""Which fleet conditions are worth an alert — pure logic, no database, no device.

Run directly:  python tests/test_alerting.py
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import alerting  # noqa: E402

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)


def screen(**kw):
    base = dict(
        id=1, name="Lobby TV", location="Phoenix Mall", status="online",
        last_seen=NOW, playback_state="playing", last_error=None,
        free_storage_mb=8000, update_status=None, app_version="1.2.0",
        target_version_code=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def kinds(conditions):
    return {c.kind for c in conditions}


def test_a_healthy_screen_raises_nothing():
    assert alerting.evaluate_screen(screen(), NOW) == []


def test_a_brief_gap_is_not_an_alert():
    # A TV rebooting or a router restarting produces a gap of a minute or two many times a
    # week. Alerting on those teaches people to ignore alerts, which is worse than silence.
    s = screen(status="offline", last_seen=NOW - timedelta(minutes=5))
    assert alerting.evaluate_screen(s, NOW) == []


def test_a_sustained_outage_is_critical():
    s = screen(status="offline", last_seen=NOW - timedelta(minutes=20))
    found = alerting.evaluate_screen(s, NOW)
    assert kinds(found) == {alerting.SCREEN_OFFLINE}
    assert found[0].severity == alerting.CRITICAL
    assert "Lobby TV" in found[0].title
    assert "20m" in found[0].detail


def test_a_long_outage_reads_in_hours():
    s = screen(status="offline", last_seen=NOW - timedelta(hours=9, minutes=5))
    assert "9h 5m" in alerting.evaluate_screen(s, NOW)[0].detail


def test_an_offline_screen_reports_only_that():
    # Storage and error values from an unreachable screen are last week's news. Repeating
    # them alongside the outage buries the one fact that matters.
    s = screen(
        status="offline", last_seen=NOW - timedelta(hours=2),
        last_error="decoder failed", free_storage_mb=10, update_status="failed",
    )
    assert kinds(alerting.evaluate_screen(s, NOW)) == {alerting.SCREEN_OFFLINE}


def test_online_but_idle_is_critical():
    # Worse than offline: the fleet grid shows it healthy and it is selling nothing.
    s = screen(playback_state="idle")
    found = alerting.evaluate_screen(s, NOW)
    assert kinds(found) == {alerting.SCREEN_IDLE}
    assert found[0].severity == alerting.CRITICAL


def test_playback_error_is_reported():
    s = screen(last_error="MediaCodec decoder init failed")
    found = alerting.evaluate_screen(s, NOW)
    assert kinds(found) == {alerting.PLAYBACK_ERROR}
    assert "MediaCodec" in found[0].detail


def test_low_storage_is_a_warning_not_a_crisis():
    s = screen(free_storage_mb=100)
    found = alerting.evaluate_screen(s, NOW)
    assert kinds(found) == {alerting.LOW_STORAGE}
    assert found[0].severity == alerting.WARNING


def test_ample_storage_is_silent():
    assert alerting.evaluate_screen(screen(free_storage_mb=alerting.LOW_STORAGE_MB), NOW) == []


def test_failed_update_is_a_warning():
    s = screen(update_status="failed", target_version_code=12)
    found = alerting.evaluate_screen(s, NOW)
    assert kinds(found) == {alerting.UPDATE_FAILED}
    assert "12" in found[0].detail


def test_an_unpaired_screen_is_not_part_of_the_fleet():
    # It has no name, no playlist and nothing to report; it cannot be "offline".
    s = screen(status="waiting_pairing", last_seen=NOW - timedelta(days=3))
    assert alerting.evaluate_screen(s, NOW) == []


def test_several_faults_on_one_screen_all_surface():
    s = screen(last_error="boom", free_storage_mb=10, update_status="failed")
    assert kinds(alerting.evaluate_screen(s, NOW)) == {
        alerting.PLAYBACK_ERROR, alerting.LOW_STORAGE, alerting.UPDATE_FAILED,
    }


def test_naive_timestamps_are_treated_as_utc():
    # Some drivers hand back naive datetimes. Comparing one against an aware `now` raises
    # TypeError, which inside the reconciler would abort the sweep for the whole fleet.
    s = screen(status="offline", last_seen=(NOW - timedelta(hours=1)).replace(tzinfo=None))
    assert kinds(alerting.evaluate_screen(s, NOW)) == {alerting.SCREEN_OFFLINE}


def test_a_screen_never_seen_raises_nothing():
    assert alerting.evaluate_screen(screen(last_seen=None), NOW) == []


def test_failed_content_is_reported_once():
    c = SimpleNamespace(id=7, name="summer-ad.mp4", status="failed", failed_reason="no video stream")
    found = alerting.evaluate_content(c)
    assert kinds(found) == {alerting.CONTENT_FAILED}
    assert "no video stream" in found[0].detail
    assert alerting.evaluate_content(SimpleNamespace(id=8, name="x", status="ready")) == []


def test_dedupe_key_is_stable_for_the_same_situation():
    # The reconciler runs every minute. Without a stable key, a TV unplugged over a weekend
    # would produce ~2,880 identical alerts.
    first = alerting.evaluate_screen(screen(status="offline", last_seen=NOW - timedelta(minutes=20)), NOW)[0]
    later = alerting.evaluate_screen(
        screen(status="offline", last_seen=NOW - timedelta(minutes=20)),
        NOW + timedelta(hours=3),
    )[0]
    assert first.dedupe_key == later.dedupe_key == "screen_offline:1"


def test_dedupe_keys_do_not_collide_across_kinds_or_targets():
    s = screen(last_error="boom", free_storage_mb=10)
    keys = {c.dedupe_key for c in alerting.evaluate_screen(s, NOW)}
    assert keys == {"playback_error:1", "low_storage:1"}
    other = screen(id=2, last_error="boom")
    assert alerting.evaluate_screen(other, NOW)[0].dedupe_key == "playback_error:2"


def test_evaluate_all_keys_every_condition():
    screens = [
        screen(id=1, last_error="boom"),
        screen(id=2, status="offline", last_seen=NOW - timedelta(hours=1)),
    ]
    contents = [SimpleNamespace(id=9, name="ad", status="failed", failed_reason=None)]
    found = alerting.evaluate_all(screens, contents, NOW)
    assert set(found) == {"playback_error:1", "screen_offline:2", "content_failed:9"}


def test_a_screen_with_no_name_falls_back_to_its_location():
    s = screen(name=None, last_error="boom")
    assert "Phoenix Mall" in alerting.evaluate_screen(s, NOW)[0].title
    s = screen(name=None, location=None, last_error="boom")
    assert "Screen 1" in alerting.evaluate_screen(s, NOW)[0].title


# --- Operating hours -------------------------------------------------------------------
# A screen scheduled off is not a broken screen. Before this, a shop TV on 09:00-21:00
# raised a CRITICAL every night of its life.

OPEN_9_TO_9 = {d: ["09:00", "21:00"] for d in
               ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}


def test_always_on_is_never_scheduled_off():
    assert alerting.is_scheduled_off(screen(), NOW) is False


def test_mode_never_is_always_scheduled_off():
    assert alerting.is_scheduled_off(screen(operating_mode="never"), NOW) is True


def test_inside_the_window_is_open():
    # NOW is 12:00 UTC, inside 09:00-21:00.
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9)
    assert alerting.is_scheduled_off(s, NOW) is False


def test_outside_the_window_is_closed():
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9)
    assert alerting.is_scheduled_off(s, NOW.replace(hour=23)) is True


def test_hours_mode_with_no_windows_stays_open():
    # "hours" selected but nothing filled in must not silence the screen forever.
    s = screen(operating_mode="hours", operating_hours=None)
    assert alerting.is_scheduled_off(s, NOW) is False


def test_an_overnight_window_wraps_midnight():
    # A bar open 22:00-02:00 is open at 01:00 and shut at 12:00.
    s = screen(operating_mode="hours",
               operating_hours={d: ["22:00", "02:00"] for d in
                                ("mon", "tue", "wed", "thu", "fri", "sat", "sun")})
    assert alerting.is_scheduled_off(s, NOW.replace(hour=1)) is False
    assert alerting.is_scheduled_off(s, NOW) is True


def test_a_day_with_no_window_is_closed_all_day():
    # NOW is a Saturday; only weekdays are configured.
    s = screen(operating_mode="hours",
               operating_hours={"mon": ["09:00", "21:00"]})
    assert alerting.is_scheduled_off(s, NOW) is True


def test_hours_are_read_in_the_screens_own_timezone():
    # 23:00 UTC is 04:30 next day in Kolkata, which is outside 09:00-21:00 either way;
    # 05:00 UTC is 10:30 there, inside the window but outside it in UTC.
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9,
               timezone="Asia/Kolkata")
    assert alerting.is_scheduled_off(s, NOW.replace(hour=5)) is False
    assert alerting.is_scheduled_off(screen(operating_mode="hours",
                                            operating_hours=OPEN_9_TO_9),
                                     NOW.replace(hour=5)) is True


def test_an_unknown_timezone_falls_back_instead_of_raising():
    # One bad row must not abort the reconciler's sweep over the whole fleet.
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9,
               timezone="Mars/Olympus_Mons")
    assert alerting.is_scheduled_off(s, NOW) is False


def test_a_closed_screen_raises_no_offline_alert():
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9,
               status="offline", last_seen=NOW - timedelta(hours=8))
    assert alerting.evaluate_screen(s, NOW.replace(hour=23)) == []


def test_a_closed_screen_raises_no_idle_alert():
    # Powering down reports "idle" first; that must not become a critical either.
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9,
               status="online", playback_state="idle")
    assert alerting.evaluate_screen(s, NOW.replace(hour=23)) == []


def test_an_open_screen_still_alerts_normally():
    # The suppression must not swallow a real outage during trading hours.
    s = screen(operating_mode="hours", operating_hours=OPEN_9_TO_9,
               status="offline", last_seen=NOW - timedelta(hours=8))
    assert kinds(alerting.evaluate_screen(s, NOW)) == {alerting.SCREEN_OFFLINE}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("alerting: all checks passed")
