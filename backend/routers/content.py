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

logger = logging.getLogger(__name__)

from arq import create_pool
from .. import models, schemas
from ..database import REDIS_SETTINGS
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from ..media_urls import delete_stored_file
from .screens import is_s3_enabled, resolve_media_url

router = APIRouter()


def queue_processing(db, content: models.Content) -> None:
    """Hand a video to the transcode worker, or mark it failed if we cannot.

    The previous version fired the enqueue into a background task and swallowed every
    exception, so an unreachable Redis left the row at "processing" forever and the
    library showed a spinner that would never resolve. Silent and permanent is the worst
    failure mode available, so a queue that cannot be reached is now a visible failure the
    operator can retry.
    """
    import asyncio

    async def _enqueue():
        pool = await create_pool(REDIS_SETTINGS)
        try:
            await pool.enqueue_job("process_media", content.id)
        finally:
            await pool.close()

    try:
        # Route handlers here are sync, so FastAPI runs them in a worker thread with no
        # event loop of their own — asyncio.run is safe and, unlike create_task, actually
        # propagates the failure back to us.
        asyncio.run(_enqueue())
    except Exception as exc:  # noqa: BLE001 - any queue failure must surface, not vanish
        logger.exception("Could not queue processing for content %s", content.id)
        content.status = "failed"
        content.failed_reason = f"Could not queue processing: {exc}"
        db.commit()

UPLOAD_DIR = os.path.join(pathlib.Path(__file__).parent.parent.parent.absolute(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "olrac-media")

s3_client = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "auto"),
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


def generate_video_thumbnail(video_path: str, stem: str, organization_id: int) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    thumbnail_name = f"{stem}-thumbnail.jpg"
    thumbnail_path = os.path.join(UPLOAD_DIR, str(organization_id), thumbnail_name)
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
    used_bytes = scope.query(models.Content).with_entities(
        func.coalesce(func.sum(models.Content.file_size_bytes), 0)
    ).scalar()
    if used_bytes + file_size_bytes > organization.storage_quota_bytes:
        remaining = max(organization.storage_quota_bytes - used_bytes, 0)
        raise HTTPException(
            status_code=413,
            detail=f"Storage quota exceeded. This upload is {file_size_bytes} bytes; {remaining} bytes remain. Upgrade your plan to continue.",
        )

    extension = os.path.splitext(file.filename or "")[1].lower()
    stem = str(uuid.uuid4())
    unique_filename = f"{stem}{extension}"
    storage_key = f"{scope.organization_id}/{unique_filename}"
    content_type_header = file.content_type or "application/octet-stream"
    content_type = "video" if content_type_header.startswith("video") or extension in {".mp4", ".mov", ".webm"} else "image"
    thumbnail: str | None = None

    if is_s3_enabled():
        try:
            s3_client.upload_fileobj(
                file.file,
                S3_BUCKET,
                storage_key,
                ExtraArgs={"ContentType": content_type_header},
            )
            file_url = f"s3://{storage_key}"
            if content_type == "image":
                thumbnail = file_url
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
            thumbnail_path = generate_video_thumbnail(file_path, stem, scope.organization_id)
            if thumbnail_path:
                thumbnail = public_upload_url(f"{scope.organization_id}/{os.path.basename(thumbnail_path)}")

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
    query = scope.query(models.Content)
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
        delete_stored_file(stored_url, UPLOAD_DIR)

    scope.db.delete(content)
    scope.db.commit()
    return {"status": "ok"}
