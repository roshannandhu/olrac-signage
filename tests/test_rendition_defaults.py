"""Rendition selection, against the set the transcoder actually produces.

`tests/test_media_selection.py` builds its own renditions to exercise the selection rules.
That is the right shape for testing the rules, but it means the rules were never checked
against the real output of the worker -- and they had drifted apart badly.

Rule 2 hands a screen that has not yet reported its capabilities a "safe default", and it
found that default by looking up a rendition literally named "720p". When the transcoder
changed to 1080p + 480p, that lookup returned None, and the caller
(`routers/screens.py`, at the `select_rendition` call) falls back to `content.file_url` --
which is the full-size master. Every newly provisioned screen, the ones nothing is known
about, would have been handed the heaviest file in the library. Every test still passed.

So these bind to `worker.RENDITION_RESOLUTIONS` directly. Change the transcoder's output
and this file is what notices.

Run directly:  python tests/test_rendition_defaults.py
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Imported for its constants only; keep it off any real database.
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{Path(tempfile.mkdtemp()).as_posix()}/rendition.db"
)

import pytest  # noqa: E402

from backend.media_selection import select_rendition  # noqa: E402
from backend.worker import RENDITION_RESOLUTIONS  # noqa: E402


def rendition(name: str, width: int, height: int):
    return SimpleNamespace(
        resolution=name, width=width, height=height, codec="h264",
        file_url=f"s3://org/asset_{name}.mp4", sha256="a" * 64,
        file_size_bytes=width * height, rotation=0, duration_ms=1000,
    )


def real_content():
    """Content carrying exactly what the transcoder produces today."""
    return SimpleNamespace(renditions=[
        rendition(name, w, h) for name, (w, h) in RENDITION_RESOLUTIONS.items()
    ])


def screen(**kw):
    base = dict(
        screen_width=None, screen_height=None, supported_video_codecs=None,
        max_decode_width=None, max_decode_height=None, total_ram_mb=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_the_transcoder_produces_at_least_two_sizes():
    # The whole point of Rule 2 is having something smaller than the master to fall back
    # to. One rendition would make "conservative default" meaningless.
    assert len(RENDITION_RESOLUTIONS) >= 2, RENDITION_RESOLUTIONS


def test_an_uncharacterised_screen_never_gets_nothing():
    # Returning None sends the caller to content.file_url, which is the full-size master.
    chosen = select_rendition(real_content(), screen())
    assert chosen is not None, (
        "a screen with no reported capabilities got no rendition; the caller will fall "
        "back to the full-size master"
    )


def test_an_uncharacterised_screen_is_not_handed_the_largest():
    chosen = select_rendition(real_content(), screen())
    largest = max(RENDITION_RESOLUTIONS.values(), key=lambda wh: wh[0] * wh[1])
    assert (chosen.width, chosen.height) != largest, (
        f"the safe default is the biggest rendition available ({chosen.resolution})"
    )


def test_the_default_stays_within_the_low_memory_ceiling():
    # 1280 is the same ceiling Rule 6 imposes on sub-1.5GB devices; an unknown screen
    # should not be assumed better than that.
    chosen = select_rendition(real_content(), screen())
    assert max(chosen.width, chosen.height) <= 1280, chosen.resolution


def test_a_capable_panel_still_gets_the_master():
    # The conservative default must not become a cap on screens that reported real specs.
    chosen = select_rendition(
        real_content(),
        screen(screen_width=1920, screen_height=1080, total_ram_mb=4096),
    )
    assert (chosen.width, chosen.height) == (1920, 1080), chosen.resolution


def test_a_small_panel_gets_the_small_rendition():
    chosen = select_rendition(
        real_content(),
        screen(screen_width=1280, screen_height=720, total_ram_mb=2048),
    )
    assert max(chosen.width, chosen.height) <= 1280, chosen.resolution


def test_a_low_memory_device_is_capped():
    chosen = select_rendition(
        real_content(),
        screen(screen_width=1920, screen_height=1080, total_ram_mb=1024),
    )
    assert max(chosen.width, chosen.height) <= 1280, chosen.resolution


def test_the_default_survives_a_single_oversized_rendition():
    # If the set ever holds nothing under the ceiling, the smallest is still better than
    # None -- which would silently promote the master.
    only_large = SimpleNamespace(renditions=[rendition("4k", 3840, 2160),
                                             rendition("1080p", 1920, 1080)])
    chosen = select_rendition(only_large, screen())
    assert chosen is not None
    assert (chosen.width, chosen.height) == (1920, 1080), chosen.resolution


def test_content_with_no_renditions_still_returns_nothing():
    # The one case where None is correct: there is genuinely nothing to choose.
    assert select_rendition(SimpleNamespace(renditions=[]), screen()) is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
