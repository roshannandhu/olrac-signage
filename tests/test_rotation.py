"""Rotation precedence — pure logic, no database, no device.

Run directly:  python tests/test_rotation.py
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.rotation import normalise, resolve_rotation  # noqa: E402


def test_normalise():
    assert normalise(0) == 0
    assert normalise(90) == 90
    assert normalise(270) == 270
    assert normalise(360) == 0, "a full turn is no turn"
    assert normalise(450) == 90, "wraps past 360"
    # Anything a device or a bad payload might send falls back to landscape rather than
    # leaving the panel at some angle nobody chose.
    assert normalise(45) == 0
    assert normalise(-90) == 270
    assert normalise(None) == 0
    assert normalise("portrait") == 0


def test_item_override_wins():
    screen = SimpleNamespace(orientation=0)
    item = SimpleNamespace(rotation=90)
    assert resolve_rotation(item, screen) == 90


def test_falls_back_to_screen():
    screen = SimpleNamespace(orientation=270)
    item = SimpleNamespace(rotation=None)
    assert resolve_rotation(item, screen) == 270


def test_zero_override_is_not_treated_as_absent():
    """A screen mounted portrait with one item deliberately pinned to landscape."""
    screen = SimpleNamespace(orientation=90)
    item = SimpleNamespace(rotation=0)
    assert resolve_rotation(item, screen) == 0


def test_defaults_when_nothing_is_set():
    assert resolve_rotation(SimpleNamespace(), SimpleNamespace()) == 0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("rotation: all checks passed")
