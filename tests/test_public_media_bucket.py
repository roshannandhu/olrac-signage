"""A published bucket serves media with no credentials at all.

The deployment lost its storage credentials, so `/api/media/<key>` answered 503 and every
thumbnail, report image and TV advert went blank. Publishing the bucket read-only fixes the
serving half without a credential existing anywhere -- but only if the route checks for it
BEFORE it checks for a key, which is the thing worth pinning down.

Pure logic: no database, no network, no boto3 client is ever constructed.
"""
import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

os.environ.setdefault("SECRET_KEY", "pytest-public-bucket")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend import media_urls  # noqa: E402

# Blanked AFTER the import, not before: media_urls loads backend/.env at import time, so a
# developer machine with real credentials in that file would otherwise put them straight
# back and this suite would assert nothing. `_setting` treats blank as unset.
for _name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
    os.environ[_name] = ""


def _serve(key: str):
    """Call the route function directly, without a database or an app fixture."""
    from backend.main import serve_media

    return serve_media(key)


def test_public_base_is_a_location_not_a_secret():
    """Blank unless configured, and trailing slashes never produce a doubled one."""
    os.environ.pop("R2_PUBLIC_BASE_URL", None)
    assert media_urls.public_media_base() == ""

    os.environ["R2_PUBLIC_BASE_URL"] = "https://pub-abc123.r2.dev/"
    assert media_urls.public_media_base() == "https://pub-abc123.r2.dev"


def test_serves_without_credentials():
    os.environ["R2_PUBLIC_BASE_URL"] = "https://pub-abc123.r2.dev"
    assert not media_urls.is_s3_enabled(), "precondition: no credentials are configured"

    response = _serve("org-67/9685365d-0d94-4dee-ae61-8f7deefbf3a3.png")

    assert response.status_code == 307
    assert response.headers["location"] == (
        "https://pub-abc123.r2.dev/org-67/9685365d-0d94-4dee-ae61-8f7deefbf3a3.png"
    )
    # A signature-free URL does not expire, so it is safe for a shared cache to keep --
    # which is the difference that keeps an R2 egress bill flat under a fleet of TVs.
    assert "public" in response.headers["cache-control"]


def test_without_a_public_base_it_still_refuses_rather_than_guessing():
    """No credentials and no published bucket must stay a loud 503, not a broken redirect."""
    from fastapi import HTTPException

    os.environ.pop("R2_PUBLIC_BASE_URL", None)
    try:
        _serve("org-67/whatever.png")
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("expected 503 when neither credentials nor a public base exist")


def test_key_escape_is_still_blocked_on_the_public_path():
    """The traversal guard must run before the redirect, or it stops applying at all."""
    from fastapi import HTTPException

    os.environ["R2_PUBLIC_BASE_URL"] = "https://pub-abc123.r2.dev"
    for bad in ("", "/etc/passwd", "org-1/../org-2/private.png"):
        try:
            _serve(bad)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:
            raise AssertionError(f"expected 404 for {bad!r}")


if __name__ == "__main__":
    test_public_base_is_a_location_not_a_secret()
    test_serves_without_credentials()
    test_without_a_public_base_it_still_refuses_rather_than_guessing()
    test_key_escape_is_still_blocked_on_the_public_path()
    print("OK - published bucket serves media with no credentials")
