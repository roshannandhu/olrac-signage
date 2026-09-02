"""Turning a stored media location into something a browser or a TV can fetch.

This lives in its own module because both the schemas and the routers need it, and the
schemas cannot import from a router without a cycle.

Locations are stored host-independently — "/uploads/<org>/<file>" for local storage, or
"s3://<key>" for object storage — and only become absolute when they are served. Baking an
origin in at upload time is what previously left every row pointing at a stale
http://localhost:8000 that no phone or TV could ever reach.
"""
import os
import pathlib
from functools import lru_cache
from urllib.parse import quote


# Characters that must never reach a storage key. "/" would invent a nested folder and
# ".." a parent one; whitespace and control characters break the URLs built from the key.
_UNSAFE_PUNCTUATION = '/\\?%*:|"<>'
_UNSAFE_IN_KEY = str.maketrans(
    {character: "-" for character in _UNSAFE_PUNCTUATION}
    # Space and the control range: both are legal in an S3 key and both make the URLs
    # built from it awkward or invalid, so neither should survive into one.
    | {chr(code): "-" for code in range(33)}
)


def storage_prefix(organization) -> str:
    """Safe, alphanumeric bucket key prefix for an organization."""
    if not organization or getattr(organization, "id", None) is None:
        return "shared"
    return f"org-{organization.id}"


def _setting(name: str) -> str:
    """One environment value, with a variable that is present but BLANK treated as unset.

    `os.getenv(name, default)` returns "" for `S3_ENDPOINT_URL=` in a deployment's
    environment -- a stray blank, not a deliberate choice -- and boto3 rejects an empty
    endpoint with ValueError. Callers swallowed that, so one blank turned every thumbnail
    on the site grey and left nothing in the logs to say why.

    There is no baked-in account. Credentials in source (or in a client JS bundle) are
    world-readable and cannot be rotated without a rebuild.
    """
    return (os.getenv(name) or "").strip()


def get_s3_config() -> dict[str, str]:
    """Where object storage is and how to authenticate to it.

    The single source of truth: every boto3 client in this codebase is built from this and
    nothing else. A second answer to "which bucket?" living elsewhere is what produced a
    run of signature 403s.
    """
    return {
        "endpoint_url": _setting("S3_ENDPOINT_URL"),
        "aws_access_key_id": _setting("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": _setting("AWS_SECRET_ACCESS_KEY"),
        "bucket": _setting("S3_BUCKET_NAME") or "olrac-media",
        "region_name": _setting("AWS_REGION") or "auto",
    }


def is_s3_enabled() -> bool:
    cfg = get_s3_config()
    return bool(cfg["aws_access_key_id"] and cfg["aws_access_key_id"] != "mock")


@lru_cache(maxsize=4)
def _s3_client_for(endpoint_url: str, key_id: str, secret: str, region: str):
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=region,
    )


def s3_client():
    """A boto3 client built from `get_s3_config` and nothing else.

    Cached, because /api/media signs a URL for every image in every grid and constructing a
    client re-parses botocore's service model each time -- but keyed on the configuration
    rather than cached outright, so changing an environment variable actually takes effect
    instead of being silently served by a client built from the old one.
    """
    cfg = get_s3_config()
    return _s3_client_for(
        cfg["endpoint_url"], cfg["aws_access_key_id"], cfg["aws_secret_access_key"], cfg["region_name"]
    )


@lru_cache(maxsize=1)
def _detect_lan_host() -> str:
    """Best-effort LAN address of this machine, so devices on the network can reach it.

    Cached: this runs for every asset and every rendition in a response, and a socket call
    per URL would turn one list request into hundreds of them.
    """
    import socket

    try:
        # No packet is actually sent; this only asks the OS which interface would be used.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except Exception:
        return "127.0.0.1"


def media_base_url() -> str:
    """Origin that players and browsers should fetch media from."""
    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if render_url:
        return render_url
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured and not ("localhost" in configured or "127.0.0.1" in configured):
        return configured
    public_host = os.getenv("PUBLIC_HOST", "").strip()
    if public_host and not ("127.0.0.1" in public_host or "localhost" in public_host):
        return f"http://{public_host}:{os.getenv('PORT', '8010')}"
    return "https://olrac-signage-32lh.onrender.com"


def resolve_media_url(value: str | None) -> str | None:
    """Absolute, fetchable URL for a stored media location.

    An object-storage key resolves to this API's own `/api/media/<key>`, which redirects to
    a freshly signed URL each time it is followed. It used to resolve to a presigned R2 URL
    minted right here, and that is what made blank thumbnails a recurring bug rather than a
    one-off: every consumer ended up holding a credential-signed URL with an expiry baked
    into it, so the dashboard, the TV app and the JS and Kotlin signers each had to agree
    on bucket, endpoint, region, key prefix and clock. Any drift between them, any URL
    cached past its expiry, and any object that had since moved all came back as the same
    opaque 403 and rendered as the same grey placeholder.

    What this returns is pure string work -- no credentials, no clock, no network, nothing
    that can throw -- and it stays valid for as long as the object exists, so it is safe to
    cache in a browser, persist in a TV's local database or paste into a report.
    """
    if not value:
        return value
    if value.startswith("/uploads/"):
        return f"{media_base_url()}{value}"
    if not value.startswith("s3://"):
        return value
    key = quote(value.removeprefix("s3://").lstrip("/"), safe="/")
    return f"{media_base_url()}/api/media/{key}"


def delete_stored_file(stored_url: str | None, upload_dir: str) -> bool:
    """Remove the local file a stored location points at. Returns True if it went.

    Shared by content deletion, screenshot retention and the orphan sweep so the
    path-escape guard exists once. A stored value is attacker-influenced in principle, so
    the resolved path must still sit inside the uploads root — otherwise a crafted
    "/uploads/../../etc/passwd" would delete outside it.
    """
    if not stored_url or "/uploads/" not in stored_url:
        return False
    relative_path = stored_url.split("/uploads/", 1)[1]
    root = pathlib.Path(upload_dir).resolve()
    try:
        target = pathlib.Path(upload_dir, relative_path).resolve()
    except (OSError, ValueError):
        return False
    if not target.is_relative_to(root) or not target.exists():
        return False
    try:
        target.unlink()
        return True
    except OSError:
        return False
