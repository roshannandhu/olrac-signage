import os
import uuid
import json
import logging
import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .. import models, schemas, database
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from .content import is_s3_enabled, s3_client, S3_BUCKET, UPLOAD_DIR, public_upload_url
from ..media_urls import resolve_media_url
from .screens import verify_device_auth

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()

@router.post("/{screen_id}/request-screenshot")
async def request_screenshot(
    screen_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    try:
        redis = database.get_redis()
        await redis.publish(f"screen:{screen.device_id}", json.dumps({"type": "request_screenshot"}))
    except Exception as e:
        logger.warning(f"Failed to publish request_screenshot to redis: {e}")
        
    return {"status": "ok", "message": "Screenshot requested"}


@router.post("/device/{device_id}/screenshot")
def upload_device_screenshot(
    device_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    screen = verify_device_auth(device_id, credentials, db)
    
    extension = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    stem = str(uuid.uuid4())
    unique_filename = f"{stem}{extension}"
    storage_key = f"screenshots/{screen.organization_id}/{unique_filename}"
    
    file.file.seek(0)
    
    if is_s3_enabled():
        try:
            s3_client.upload_fileobj(
                file.file,
                S3_BUCKET,
                storage_key,
                ExtraArgs={"ContentType": file.content_type or "image/jpeg"},
            )
            # Stored in the canonical "s3://<key>" form, like every other asset, and
            # resolved to a fetchable URL on read (list_screenshots below already calls
            # resolve_media_url). It used to be saved as a public https://pub-... URL,
            # which media_storage.is_remote() does not recognise -- so the nightly
            # prune deleted the row, silently failed to delete the object, and every
            # screenshot ever taken stayed in the bucket forever.
            file_url = f"s3://{storage_key}"
        except Exception as e:
            logger.error(f"Failed to upload screenshot to S3: {e}")
            raise HTTPException(status_code=500, detail="Storage error")
    else:
        org_dir = os.path.join(UPLOAD_DIR, str(screen.organization_id))
        os.makedirs(org_dir, exist_ok=True)
        local_path = os.path.join(org_dir, unique_filename)
        with open(local_path, "wb") as f:
            f.write(file.file.read())
        # Use existing content router's public_upload_url mapping for simplicity,
        # but note it maps to /uploads/{org_id}/{filename} which matches our folder.
        storage_key = f"{screen.organization_id}/{unique_filename}"
        file_url = public_upload_url(storage_key)

    screenshot = models.ScreenshotLog(
        organization_id=screen.organization_id,
        screen_id=screen.id,
        file_url=file_url
    )
    db.add(screenshot)
    db.commit()
    db.refresh(screenshot)
    
    return {"status": "ok", "url": resolve_media_url(file_url) or file_url}


@router.get("/{screen_id}/screenshots")
def list_screenshots(
    screen_id: int,
    limit: int = 10,
    scope: TenantScope = Depends(get_tenant_scope),
):
    screen = scope.get(models.Screen, screen_id)
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
        
    logs = (
        scope.query(models.ScreenshotLog)
        .filter(models.ScreenshotLog.screen_id == screen_id)
        .order_by(models.ScreenshotLog.created_at.desc())
        .limit(limit)
        .all()
    )
    
    return [
        {
            "id": log.id,
            "file_url": resolve_media_url(log.file_url) or log.file_url,
            "created_at": log.created_at
        }
        for log in logs
    ]
