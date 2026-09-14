"""The pairing code must outlive the moment the TV replaces it, and a person typing it.

Two constants have to agree and live in different languages, so nothing connected them:

  backend/routers/screens.py   PAIR_CODE_TTL          -- how long the server honours a code
  MainActivity.kt              PAIR_CODE_REFRESH_MS   -- when the player asks for a new one

Both were sixty seconds. The code on the television therefore expired at the same instant the
player replaced it, so the six digits an installer was reading were expired or about to be for
most of their life -- and one minute is not enough time to read a code off a TV, walk to a
laptop, find the Screens page and type it anyway. The report was "the pairing code does not
work", which was exactly right.

Pure text: reads both files and compares the numbers. No database, no Android toolchain.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend" / "routers" / "screens.py"
PLAYER = REPO / "android-tv" / "app" / "src" / "main" / "java" / "com" / "olrac" / "signage" / "MainActivity.kt"

# How long the window is, is a product decision -- the player shows a countdown and rotation
# is intentional. This only refuses a window so short that nothing could be typed into it.
MINIMUM_USABLE_SECONDS = 30

# The player polls on an interval, so "earlier than expiry" is not enough on its own: the
# refresh lands on the first tick at or after the deadline, and everything between the
# deadline and that tick is a code the server has already stopped honouring.
MINIMUM_MARGIN_SECONDS = 10


def server_ttl_seconds() -> int:
    text = BACKEND.read_text(encoding="utf-8")
    match = re.search(r"PAIR_CODE_TTL\s*=\s*timedelta\((\w+)=(\d+)\)", text)
    assert match, "PAIR_CODE_TTL is not declared as a timedelta in screens.py"
    unit, amount = match.group(1), int(match.group(2))
    multiplier = {"seconds": 1, "minutes": 60, "hours": 3600}
    assert unit in multiplier, f"unexpected timedelta unit {unit!r}"
    return amount * multiplier[unit]


def player_refresh_seconds() -> int:
    text = PLAYER.read_text(encoding="utf-8")
    match = re.search(r"PAIR_CODE_REFRESH_MS\s*=\s*([0-9_*\s]+)L", text)
    assert match, "PAIR_CODE_REFRESH_MS is not declared in MainActivity.kt"
    # e.g. "4 * 60_000" -- evaluated rather than parsed, so the Kotlin stays readable.
    expression = match.group(1).replace("_", "").strip()
    assert re.fullmatch(r"[0-9*\s]+", expression), f"unexpected expression {expression!r}"
    return int(eval(expression)) // 1000  # noqa: S307 - digits and '*' only, checked above


def player_displayed_ttl_seconds() -> int:
    text = PLAYER.read_text(encoding="utf-8")
    match = re.search(r"PAIR_CODE_TTL_SECONDS\s*=\s*(\d+)", text)
    assert match, "PAIR_CODE_TTL_SECONDS is not declared in MainActivity.kt"
    return int(match.group(1))


def test_the_code_outlives_a_person_typing_it():
    ttl = server_ttl_seconds()
    assert ttl >= MINIMUM_USABLE_SECONDS, (
        f"a pairing code lasts {ttl}s. Nobody can read six digits off a television and type "
        f"them into a dashboard on another device in that time."
    )


def test_the_player_refreshes_before_the_code_expires():
    ttl = server_ttl_seconds()
    refresh = player_refresh_seconds()
    assert refresh < ttl, (
        f"the player refreshes the code every {refresh}s while the server honours it for "
        f"{ttl}s. Equal or later means the code is expired at the moment it is replaced, "
        f"which is the state this test exists to prevent."
    )
    # Not merely earlier -- earlier by enough that a slow poll or a retry cannot close the
    # gap. The player polls every few seconds, so a margin of one second is not a margin.
    assert ttl - refresh >= MINIMUM_MARGIN_SECONDS, (
        f"only {ttl - refresh}s between the player refreshing and the server expiring. "
        f"The polling loop ticks every few seconds and a round trip is not free, so a thin "
        f"margin is the same bug in a smaller window."
    )


def test_the_countdown_on_the_tv_tells_the_truth():
    """The player shows a remaining time; it must be the window the server actually grants."""
    assert player_displayed_ttl_seconds() == server_ttl_seconds(), (
        f"the TV counts down from {player_displayed_ttl_seconds()}s while the server grants "
        f"{server_ttl_seconds()}s. One of them is lying to the installer."
    )


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            function()
            print(f"  ok  {name}")
    print(
        f"OK - code lasts {server_ttl_seconds()}s, player refreshes at "
        f"{player_refresh_seconds()}s"
    )
