import hashlib
import logging
import os
import pathlib
import shutil
import subprocess
import uuid
from typing import Optional

import boto3
from fastapi import Query, APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from arq import create_pool
from .. import models, schemas
from ..database import REDIS_SETTINGS
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from .. import media_storage
from ..media_urls import is_s3_enabled, resolve_media_url, storage_prefix

router = APIRouter()


def queue_processing(db, content: models.Content) -> None:
    """Hand a video to the transcode worker, ensuring it is processed immediately.

    In standalone or single-host deployments where an external arq worker process may not
    be active, we launch process_media_sync in a daemon thread so video processing and
    renditions are generated immediately without hanging on 'processing'.
    """
    import threading
    from ..worker import process_media_sync

    threading.Thread(target=process_media_sync, args=(content.id,), daemon=True).start()

UPLOAD_DIR = os.path.join(pathlib.Path(__file__).parent.parent.parent.absolute(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# The extension came straight off the client filename and was appended to the stored
# name, with nothing checking it. /uploads is mounted as StaticFiles, so uploading
# "poster.html" -- or an SVG with a <script> in it, which is the easy one to miss --
# stored and then served attacker-controlled markup from the API's own origin. Signage
# only ever plays pictures and video, so the set of things worth accepting is short and
# an allowlist costs nothing.
ALLOWED_UPLOAD_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
    ".mp4", ".mov", ".webm", ".mkv", ".m4v",
}
from ..media_urls import get_s3_config, is_s3_enabled, storage_prefix


def get_s3_client():
    cfg = get_s3_config()
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint_url"],
        aws_access_key_id=cfg["aws_access_key_id"],
        aws_secret_access_key=cfg["aws_secret_access_key"],
        region_name=cfg["region_name"],
    )


def public_upload_url(storage_key: str) -> str:
    """Where an asset lives, stored as a path rather than a full URL.

    This used to bake an absolute origin into the database at upload time, so every row
    pointed at whatever host uploaded it — in practice a stale http://localhost:8000.
    Thumbnails 404'd in the dashboard, and a TV could never download the media at all
    because "localhost" on a TV means the TV. The origin is now applied when the record is
    served, so the same row works from this machine, from a phone on the LAN, and from a
    public deployment.
    """
    return f"/uploads/{storage_key}"


def generate_video_thumbnail(video_path: str, stem: str, prefix: str) -> str | None:
    """Write a poster frame beside the video it came from.

    Takes the storage PREFIX rather than an organisation id: the caller builds the
    thumbnail's URL from the same prefix, and when this took an id it wrote the file to
    `uploads/19/` while the row pointed at `uploads/alice-example.com-19/`, so every video
    thumbnail 404'd.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    thumbnail_name = f"{stem}-thumbnail.jpg"
    thumbnail_path = os.path.join(UPLOAD_DIR, prefix, thumbnail_name)
    os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
    try:
        subprocess.run(
            [ffmpeg, "-y", "-ss", "00:00:01", "-i", video_path, "-frames:v", "1", "-vf", "scale=640:-2", thumbnail_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        return thumbnail_path if os.path.exists(thumbnail_path) else None
    except (OSError, subprocess.SubprocessError):
        return None


def serialize_content(content: models.Content) -> schemas.ContentResponse:
    payload = schemas.ContentResponse.model_validate(content)
    payload.file_url = resolve_media_url(payload.file_url) or payload.file_url
    payload.thumbnail = resolve_media_url(payload.thumbnail)
    return payload


@router.post("/upload", response_model=schemas.ContentResponse, status_code=201)
def upload_content(
    file: UploadFile = File(...),
    name: str = Form(...),
    tags: Optional[str] = Form(None),
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    file.file.seek(0, os.SEEK_END)
    file_size_bytes = file.file.tell()
    
    file.file.seek(0)
    sha256_hash = hashlib.sha256()
    while chunk := file.file.read(8192):
        sha256_hash.update(chunk)
    sha256 = sha256_hash.hexdigest()
    
    file.file.seek(0)
    organization = scope.db.query(models.Organization).filter(
        models.Organization.id == scope.organization_id
    ).one()
    # Renditions count too. Summing only the source measured roughly a third of what a
    # video really occupies -- a transcode adds a full-size master and a smaller copy on
    # top -- so a 10GB quota let through nearer 25GB of objects and the bucket filled
    # while the dashboard still reported plenty of room.
    used_bytes = scope.query(models.Content).with_entities(
        func.coalesce(func.sum(models.Content.file_size_bytes), 0)
    ).scalar()
    used_bytes += scope.db.query(
        func.coalesce(func.sum(models.MediaRendition.file_size_bytes), 0)
    ).join(
        models.Content, models.Content.id == models.MediaRendition.content_id
    ).filter(models.Content.organization_id == scope.organization_id).scalar()
    if used_bytes + file_size_bytes > organization.storage_quota_bytes:
        remaining = max(organization.storage_quota_bytes - used_bytes, 0)
        raise HTTPException(
            status_code=413,
            detail=f"Storage quota exceeded. This upload is {file_size_bytes} bytes; {remaining} bytes remain. Upgrade your plan to continue.",
        )

    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{extension or file.filename}'. Allowed: "
                + ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
            ),
        )
    stem = str(uuid.uuid4())
    unique_filename = f"{stem}{extension}"
    # Folder named after the owner's address rather than the bare organisation id, so the
    # bucket can be read by a human. storage_prefix keeps the id as a suffix, which is what
    # makes it unique and stable; see its docstring.
    storage_key = f"{storage_prefix(organization)}/{unique_filename}"
    content_type_header = file.content_type or "application/octet-stream"
    content_type = "video" if content_type_header.startswith("video") or extension in {".mp4", ".mov", ".webm"} else "image"
    thumbnail: str | None = None

    if is_s3_enabled():
        cfg = get_s3_config()
        s3 = get_s3_client()
        bucket = cfg["bucket"]
        try:
            file.file.seek(0)
            s3.upload_fileobj(
                file.file,
                bucket,
                storage_key,
                ExtraArgs={"ContentType": content_type_header},
            )
            file_url = f"s3://{storage_key}"
            if content_type == "image":
                thumbnail = file_url
            else:
                temp_video = os.path.join(UPLOAD_DIR, storage_key)
                os.makedirs(os.path.dirname(temp_video), exist_ok=True)
                file.file.seek(0)
                with open(temp_video, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                thumbnail_path = generate_video_thumbnail(temp_video, stem, storage_prefix(organization))
                if thumbnail_path and os.path.exists(thumbnail_path):
                    thumb_key = f"{storage_prefix(organization)}/{os.path.basename(thumbnail_path)}"
                    with open(thumbnail_path, "rb") as thumb_file:
                        s3.upload_fileobj(
                            thumb_file,
                            bucket,
                            thumb_key,
                            ExtraArgs={"ContentType": "image/jpeg"},
                        )
                    thumbnail = f"s3://{thumb_key}"
                try:
                    if os.path.exists(temp_video):
                        os.remove(temp_video)
                except Exception:
                    pass
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}")
    else:
        file_path = os.path.join(UPLOAD_DIR, storage_key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = public_upload_url(storage_key)
        if content_type == "image":
            thumbnail = file_url
        else:
            thumbnail_path = generate_video_thumbnail(file_path, stem, storage_prefix(organization))
            if thumbnail_path:
                thumbnail = public_upload_url(f"{storage_prefix(organization)}/{os.path.basename(thumbnail_path)}")

    content = models.Content(
        organization_id=scope.organization_id,
        type=content_type,
        file_url=file_url,
        thumbnail=thumbnail,
        name=name.strip(),
        tags=tags.strip() if tags else None,
        file_size_bytes=file_size_bytes,
        sha256=sha256,
        status="processing" if content_type == "video" else "ready",
        processing_started_at=models.utcnow() if content_type == "video" else None,
    )
    scope.db.add(content)
    scope.db.commit()
    scope.db.refresh(content)
    
    if content.type == "video":
        queue_processing(scope.db, content)

    return serialize_content(content)


@router.post("/{content_id}/retry", response_model=schemas.ContentResponse)
def retry_content_processing(
    content_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    content = scope.get(models.Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if content.type != "video":
        raise HTTPException(status_code=400, detail="Only video content can be retried")
    
    content.status = "processing"
    content.failed_reason = None
    content.processing_started_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(content)

    queue_processing(scope.db, content)

    return serialize_content(content)

@router.get("/", response_model=list[schemas.ContentResponse])
def get_all_content(
    search: str | None = None,
    tag: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
    scope: TenantScope = Depends(get_tenant_scope),
):
    # expires_at walks playlist_items, so without this the library page pays one extra
    # query per row. Requested here rather than on the relationship because eager-loading
    # it globally closes a cycle with PlaylistItem.content and slows the playlist editor
    # instead -- see the note on the model.
    query = scope.query(models.Content).options(selectinload(models.Content.playlist_items))
    if search:
        query = query.filter(models.Content.name.ilike(f"%{search}%"))
    if tag:
        query = query.filter(models.Content.tags.ilike(f"%{tag}%"))
    # Capped rather than unbounded: this is the library listing, and without a ceiling one
    # request grows with the whole account's upload history forever.
    return [
        serialize_content(item)
        for item in query.order_by(models.Content.uploaded_at.desc()).limit(limit).all()
    ]


@router.put("/{content_id}", response_model=schemas.ContentResponse)
def update_content(
    content_id: int,
    payload: schemas.ContentUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    content = scope.get(models.Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    content.name = payload.name.strip()
    content.tags = payload.tags.strip() if payload.tags else None
    scope.db.commit()
    scope.db.refresh(content)
    return serialize_content(content)


@router.delete("/{content_id}")
def delete_content(
    content_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    content = scope.get(models.Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    playlist_items = list(content.playlist_items)
    affected_playlists = {item.playlist for item in playlist_items}
    for playlist in affected_playlists:
        playlist.updated_at = models.utcnow()
    for item in playlist_items:
        scope.db.delete(item)

    # Renditions are the big one: a video becomes four transcoded files, and deleting the
    # content row cascaded the database rows away while leaving every file on disk. At
    # 500 MB an advert that stranded gigabytes per deletion.
    stored = [content.file_url, content.thumbnail]
    stored.extend(rendition.file_url for rendition in content.renditions)
    for stored_url in stored:
        # Through media_storage, which handles both backends. delete_stored_file only
        # understands "/uploads/" paths and returns False for an "s3://" key without
        # touching anything -- so on object storage this loop deleted the database rows
        # and left all six objects (original, four renditions, thumbnail) in the bucket
        # for good. The quota they consumed was never released either.
        media_storage.delete(stored_url)

    scope.db.delete(content)
    scope.db.commit()
    return {"status": "ok"}
