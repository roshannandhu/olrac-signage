"""Airtime formatting on the client report. Pure, no DB.

_duration() turns seconds of on-screen exposure into the compact string the headline tile
shows. Run directly:  python tests/test_report_airtime.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SECRET_KEY", "airtime-test")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite:///./airtime_test.db")

from backend.reports.booking_report import _duration  # noqa: E402


def test_duration_formats():
    assert _duration(0) == "0s"
    assert _duration(None) == "0s"
    assert _duration(45) == "45s"
    assert _duration(90) == "1m 30s"
    assert _duration(3600) == "1h 00m"
    assert _duration(42 * 3600 + 18 * 60) == "42h 18m"
    # rolls the seconds into the minute, never shows 60
    assert _duration(119) == "1m 59s"
    # thousands separator on long-running campaigns
    assert _duration(1234 * 3600) == "1,234h 00m"


if __name__ == "__main__":
    test_duration_formats()
    print("ok")
