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
    """Folder in Cloudflare R2 / storage, named after the account's email.

    Named rather than numbered so the bucket is legible: `19/` identifies nobody, while
    `alice@example.com/` names the customer without a database lookup.

    The address is safe to use as the sole folder name because `users.email` is globally
    unique, so one address belongs to exactly one account and therefore one organisation.
    (An earlier version appended the organisation id to guard against a collision that the
    unique constraint already makes impossible.)

    Sanitised anyway, because this is a trust boundary rather than a formatting nicety: the
    value reaches a storage key and a URL, PATCH /api/auth/me lets an account choose it,
    and a "/" would silently file objects under an invented folder. EmailStr rejects those
    today; this does not depend on that staying true.

    Note the address appears in presigned URLs, so it is visible to anyone holding one --
    a TV, or a browser's history. Return str(organization.id) here if that is ever
    unwanted; nothing else needs to change.
    """
    email = (getattr(organization, "owner_email", None) or "").strip().lower()
    if email:
        cleaned = email.translate(_UNSAFE_IN_KEY).replace("..", "-").strip("-. ")
        if cleaned:
            return cleaned
    slug = (getattr(organization, "slug", None) or "").strip()
    if slug:
        return slug
    return f"org-{organization.id}"


R2_ENDPOINT_DEFAULT = "https://3fe4487a2b8fd1e2e541bf0e0f4c7c42.r2.cloudflarestorage.com"
R2_KEY_ID_DEFAULT = "734d432aeb20a3f4bbd484ca83a8a82b"
R2_SECRET_DEFAULT = "ef6c0c74667843ec08f396b12ab0e8929d409c8c8062713da09cd17c6c628acf"
R2_BUCKET_DEFAULT = "olrac"


def get_s3_config() -> dict[str, str]:
    raw_key = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    key_id = raw_key if (raw_key and raw_key != "mock") else R2_KEY_ID_DEFAULT

    raw_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    secret = raw_secret if raw_secret else R2_SECRET_DEFAULT

    raw_endpoint = os.getenv("S3_ENDPOINT_URL", "").strip()
    endpoint = raw_endpoint if raw_endpoint else R2_ENDPOINT_DEFAULT

    raw_bucket = os.getenv("S3_BUCKET_NAME", "").strip()
    bucket = raw_bucket if raw_bucket else R2_BUCKET_DEFAULT

    region = (os.getenv("AWS_REGION") or "auto").strip()
    return {
        "endpoint_url": endpoint,
        "aws_access_key_id": key_id,
        "aws_secret_access_key": secret,
        "bucket": bucket,
        "region_name": region,
    }


def is_s3_enabled() -> bool:
    cfg = get_s3_config()
    return bool(cfg["aws_access_key_id"] and cfg["aws_access_key_id"] != "mock")


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

        cfg = get_s3_config()
        client = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint_url"],
            aws_access_key_id=cfg["aws_access_key_id"],
            aws_secret_access_key=cfg["aws_secret_access_key"],
            region_name=cfg["region_name"],
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg["bucket"], "Key": value.removeprefix("s3://")},
            ExpiresIn=3600 * 24 * 7,
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
