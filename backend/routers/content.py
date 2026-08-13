import hashlib
import logging
import os
import pathlib
import shutil
import subprocess
import uuid
from typing import Optional

import boto3
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func

logger = logging.getLogger(__name__)

from arq import create_pool
from .. import models, schemas
from ..database import REDIS_SETTINGS
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from .screens import is_s3_enabled, resolve_media_url

router = APIRouter()

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
    return f"{os.getenv('PUBLIC_BASE_URL', 'http://localhost:8000').rstrip('/')}/uploads/{storage_key}"


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
    )
    scope.db.add(content)
    scope.db.commit()
    scope.db.refresh(content)
    
    if content.type == "video":
        import asyncio
        async def _enqueue():
            pool = await create_pool(REDIS_SETTINGS)
            await pool.enqueue_job("process_media", content.id)
            await pool.close()
        try:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(_enqueue())
            except RuntimeError:
                asyncio.run(_enqueue())
        except Exception as e:
            # If Redis is down, the job won't be enqueued and remains in 'processing' state.
            pass
            
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
    scope.db.commit()
    scope.db.refresh(content)

    import asyncio
    async def _enqueue():
        pool = await create_pool(REDIS_SETTINGS)
        await pool.enqueue_job("process_media", content.id)
        await pool.close()
    try:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_enqueue())
        except RuntimeError:
            asyncio.run(_enqueue())
    except Exception as e:
        logger.warning(f"Failed to enqueue retry for content {content.id}: {e}")

    return serialize_content(content)

@router.get("/", response_model=list[schemas.ContentResponse])
def get_all_content(
    search: str | None = None,
    tag: str | None = None,
    scope: TenantScope = Depends(get_tenant_scope),
):
    query = scope.query(models.Content)
    if search:
        query = query.filter(models.Content.name.ilike(f"%{search}%"))
    if tag:
        query = query.filter(models.Content.tags.ilike(f"%{tag}%"))
    return [serialize_content(item) for item in query.order_by(models.Content.uploaded_at.desc()).all()]


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

    for stored_url in (content.file_url, content.thumbnail):
        if stored_url and "/uploads/" in stored_url:
            relative_path = stored_url.split("/uploads/", 1)[1]
            local_path = pathlib.Path(UPLOAD_DIR, relative_path).resolve()
            upload_root = pathlib.Path(UPLOAD_DIR).resolve()
            if local_path.is_relative_to(upload_root) and local_path.exists():
                try:
                    local_path.unlink()
                except OSError:
                    pass
    scope.db.delete(content)
    scope.db.commit()
    return {"status": "ok"}
