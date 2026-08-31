"""The TV hand-back link must be openable by a browser: python tests/test_tv_deep_link.py

The player registers "olrac://auth" in its manifest and MainActivity.onNewIntent acts on
it, so the link looked correct in review and worked in any hand test that opened it with an
Android intent. It never worked on a panel: the last step of Google sign-in is a NAVIGATION
in Chrome (a Custom Tab is Chrome, and so is the Android TV browser), and Chrome refuses to
resolve a scheme it does not know -- ERR_UNKNOWN_URL_SCHEME, "Web page not available", with
the account already bound server side and the TV still sitting on the sign-in screen.

What is pinned here is the property that failed: whatever the page navigates to must be a
scheme a browser will actually act on.
"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "pytest-tv-deep-link")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from backend.routers.screens import (  # noqa: E402
    TV_APP_PACKAGE,
    _android_intent_url,
    _tv_result_page,
)

SUCCESS = "olrac://auth/success?screen_id=53&screen_name=TCL%20Smart%20TV%20Pro"


def test_custom_scheme_never_reaches_the_browser():
    """The whole bug in one assertion: a raw custom scheme is what Chrome rejects."""
    assert not _android_intent_url(SUCCESS).startswith("olrac:")
    assert _android_intent_url("olrac://auth/failed").startswith("intent://")


def test_intent_carries_the_same_deep_link_the_manifest_matches():
    """No APK change: the intent's data must still be the olrac:// URL already filtered on.

    android-tv/.../AndroidManifest.xml matches scheme="olrac" host="auth", so host, path and
    query all have to survive the rewrite or the app is launched without the screen it was
    told to pair.
    """
    url = _android_intent_url(SUCCESS)
    assert url.startswith("intent://auth/success?")
    assert "screen_id=53" in url
    assert "screen_name=TCL%20Smart%20TV%20Pro" in url
    assert url.endswith(f"#Intent;scheme=olrac;package={TV_APP_PACKAGE};end")


def test_package_is_named_so_chrome_launches_instead_of_offering_the_store():
    """Without package=, Chrome sends an unresolved intent to Play -- a dead end on a TV."""
    assert TV_APP_PACKAGE == "com.olrac.signage"
    assert f"package={TV_APP_PACKAGE};" in _android_intent_url(SUCCESS)


def test_http_links_are_left_alone():
    """Only a custom scheme needs the rewrite; wrapping an https URL would break it."""
    for url in ("https://example.com/x?a=b", "http://example.com/"):
        assert _android_intent_url(url) == url


def test_the_page_navigates_and_links_to_the_intent_url():
    """Both routes back to the app -- the script and the "Return to Player" button -- must
    use the rewritten URL. Fixing only one leaves the failure on whichever path a panel
    happens to take.
    """
    html_body = _tv_result_page("t", "h", "b", SUCCESS, "#68E0A0").body.decode()
    assert "olrac://" not in html_body, "a raw custom scheme survived into the page"
    assert html_body.count("intent://auth/success") == 2, "href and window.location both"


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            function()
            print(f"  ok  {name}")
    print("tv deep link: all checks passed")
