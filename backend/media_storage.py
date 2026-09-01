"""Reading and writing media wherever it happens to live.

The transcoder needs a real file on disk -- ffmpeg cannot read `s3://` -- and then needs
to put four renditions and a thumbnail back where the original came from. Only that
fetch/store pair differs between local disk and R2/S3, so it is isolated here and the
worker stays a single code path.

Before this existed the worker simply refused: any `s3://` source raised
NotImplementedError, so with cloud storage configured -- the deployment the README
documents -- every video upload ended in `status="failed"` and no rendition was ever
produced. Capability-based rendition selection then had nothing to select from and every
panel, however cheap, was handed the original 4K file.
"""

from __future__ import annotations

import os
import pathlib
import shutil
from typing import Optional

from .media_urls import is_s3_enabled, get_s3_config

UPLOAD_DIR = os.path.join(
    pathlib.Path(__file__).parent.parent.absolute(), "uploads"
)
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "olrac-media")


def _client():
    import boto3

    cfg = get_s3_config()
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        region_name=cfg["region_name"],
    )


def storage_key_for(stored_url: str) -> str:
    """The backend-relative key inside a stored location.

    Both schemes carry the same "<org_id>/<filename>" key; they differ only in prefix.
    """
    if stored_url.startswith("s3://"):
        return stored_url[len("s3://"):]
    if "/uploads/" in stored_url:
        return stored_url.split("/uploads/", 1)[1]
    raise ValueError(f"Unrecognised storage location: {stored_url}")


def is_remote(stored_url: str) -> bool:
    return stored_url.startswith("s3://")


def fetch_to(stored_url: str, destination: pathlib.Path) -> pathlib.Path:
    """Put the bytes of `stored_url` at `destination` and return it.

    A local file is copied rather than used in place: the worker writes its renditions
    beside the file it is given, and a scratch directory keeps half-finished output out of
    the uploads tree if the transcode dies midway.
    """
    key = storage_key_for(stored_url)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if is_remote(stored_url):
        cfg = get_s3_config()
        _client().download_file(cfg["bucket"], key, str(destination))
        return destination

    source = pathlib.Path(UPLOAD_DIR) / key
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")
    shutil.copy2(source, destination)
    return destination


def store(local_path: pathlib.Path, key: str, content_type: Optional[str] = None) -> str:
    """Persist `local_path` under `key` and return the location to save on the row.

    The return value matches whatever `routers/content.py` would have written for a direct
    upload -- `s3://<key>` or `/uploads/<key>` -- so a rendition is indistinguishable from
    an original as far as `resolve_media_url` is concerned.
    """
    if is_s3_enabled():
        cfg = get_s3_config()
        extra = {"ContentType": content_type} if content_type else None
        if extra:
            _client().upload_file(str(local_path), cfg["bucket"], key, ExtraArgs=extra)
        else:
            _client().upload_file(str(local_path), cfg["bucket"], key)
        return f"s3://{key}"

    target = pathlib.Path(UPLOAD_DIR) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.resolve() != local_path.resolve():
        shutil.copy2(local_path, target)
    return f"/uploads/{key}"


def delete(stored_url: str) -> bool:
    """Remove a stored object. Best effort -- a missing object is not an error.

    Local deletion goes through `media_urls.delete_stored_file`, which carries the
    path-escape guard; this adds the object-storage half so a deleted asset does not leave
    its bytes (and the storage quota they consume) behind in the bucket forever.
    """
    if not stored_url:
        return False
    if not is_remote(stored_url):
        from .media_urls import delete_stored_file

        return delete_stored_file(stored_url, UPLOAD_DIR)

    cfg = get_s3_config()
    try:
        _client().delete_object(Bucket=cfg["bucket"], Key=storage_key_for(stored_url))
        return True
    except Exception:
        return False
