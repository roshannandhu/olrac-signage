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


def is_s3_enabled() -> bool:
    key = os.getenv("AWS_ACCESS_KEY_ID")
    return bool(key and key != "mock")


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
    """Origin that players and browsers should fetch media from.

    Defaults to this machine's LAN address rather than localhost: a TV handed "localhost"
    fetches from itself and gets nothing.
    """
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    host = os.getenv("PUBLIC_HOST", "").strip() or _detect_lan_host()
    return f"http://{host}:{os.getenv('PORT', '8010')}"


def resolve_media_url(value: str | None) -> str | None:
    """Absolute, fetchable URL for a stored media location."""
    if not value:
        return value
    if value.startswith("/uploads/"):
        return f"{media_base_url()}{value}"
    if not value.startswith("s3://"):
        return value
    if not is_s3_enabled():
        return value
    try:
        import boto3

        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "auto"),
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": os.getenv("S3_BUCKET_NAME", "olrac-media"), "Key": value.removeprefix("s3://")},
            ExpiresIn=3600,
        )
    except Exception:
        return value


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
