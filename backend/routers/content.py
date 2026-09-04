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


# Everything serialize_content walks below Content, in one batched query each.
#
# Content.ad_placements is already lazy="selectin", but that only batches the placements
# themselves -- the client, the plan, the targets and each target's screen underneath them
# are all default-lazy, and serialize_content reads every one of them for every row. So the
# library listing cost 3 queries per ad-carrying asset plus one per target: a 100-advert
# account with three screens each was roughly 600 round trips, and at ~114 ms to the
# database's region that is over a minute for one page.
#
# This is the same defect the note on Content.playlist_items describes, one level deeper --
# it came back when the 1:1 ad/client enrichment was added to serialize_content. Requested
# at the call site rather than on the relationships because only the routes that actually
# serialise Content pay for it; /sync embeds ContentResponse without ever reading the
# placement block.
CONTENT_LOADERS = (
    selectinload(models.Content.playlist_items),
    selectinload(models.Content.ad_placements).selectinload(models.AdPlacement.client),
    selectinload(models.Content.ad_placements).selectinload(models.AdPlacement.plan),
    selectinload(models.Content.ad_placements)
    .selectinload(models.AdPlacement.targets)
    .selectinload(models.AdPlacementTarget.screen),
)


def serialize_content(content: models.Content) -> schemas.ContentResponse:
    # ContentResponse.absolutise_urls already resolved file_url and thumbnail; doing it
    # again here was a no-op that made it look like there were two places media URLs got
    # built.
    payload = schemas.ContentResponse.model_validate(content)

    # 1:1 Ad & Client enriched metadata
    placements = getattr(content, "ad_placements", [])
    if placements:
        latest = sorted(placements, key=lambda p: p.id, reverse=True)[0]
        payload.placement_id = latest.id
        payload.client_id = latest.client_id
        if latest.client:
            payload.client_name = latest.client.name
            payload.client_email = latest.client.email
            payload.client_phone = latest.client.phone
        elif latest.advertiser:
            payload.client_name = latest.advertiser

        if latest.plan:
            payload.plan_id = latest.plan_id
            payload.plan_name = latest.plan.name

        payload.placement_price_paise = latest.price_paise
        payload.placement_starts_at = latest.starts_at
        payload.placement_ends_at = latest.effective_ends_at
        payload.placement_notes = latest.notes

        target_screens = []
        target_screen_names = []
        target_days: dict[int, int] = {}
        for t in getattr(latest, "targets", []):
            if t.screen_id:
                target_screens.append(t.screen_id)
                # Only locations sold their own length report one; the rest follow the
                # booking and are absent, which is what the modal reads to decide whether
                # to open its per-location panel at all.
                if t.starts_at and t.ends_at:
                    target_days[t.screen_id] = max(
                        1, round((t.ends_at - t.starts_at).total_seconds() / 86400)
                    )
                screen = getattr(t, "screen", None)
                if screen and screen.name:
                    target_screen_names.append(screen.name)
                else:
                    target_screen_names.append(f"Screen #{t.screen_id}")
        payload.screen_ids = target_screens
        payload.screen_names = target_screen_names
        payload.screen_days = target_days

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

    temp_local_file = os.path.join(UPLOAD_DIR, storage_key)
    os.makedirs(os.path.dirname(temp_local_file), exist_ok=True)
    file.file.seek(0)
    with open(temp_local_file, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if is_s3_enabled():
        cfg = get_s3_config()
        s3 = get_s3_client()
        bucket = cfg["bucket"]
        try:
            with open(temp_local_file, "rb") as f_in:
                s3.upload_fileobj(
                    f_in,
                    bucket,
                    storage_key,
                    ExtraArgs={"ContentType": content_type_header},
                )
            file_url = f"s3://{storage_key}"
            if content_type == "image":
                thumbnail = file_url
            else:
                thumbnail_path = generate_video_thumbnail(temp_local_file, stem, storage_prefix(organization))
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
                        os.remove(thumbnail_path)
                    except Exception:
                        pass
                else:
                    thumbnail = file_url

            try:
                if os.path.exists(temp_local_file):
                    os.remove(temp_local_file)
            except Exception:
                pass
        except Exception as exc:
            try:
                if os.path.exists(temp_local_file):
                    os.remove(temp_local_file)
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}")
    else:
        file_url = public_upload_url(storage_key)
        if content_type == "image":
            thumbnail = file_url
        else:
            thumbnail_path = generate_video_thumbnail(temp_local_file, stem, storage_prefix(organization))
            if thumbnail_path:
                thumbnail = public_upload_url(f"{storage_prefix(organization)}/{os.path.basename(thumbnail_path)}")
            else:
                thumbnail = file_url

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
    # expires_at walks playlist_items and the ad block walks the placement's client, plan
    # and targets. Requested here rather than on the relationships because eager-loading
    # playlist_items globally closes a cycle with PlaylistItem.content and slows the
    # playlist editor instead -- see the note on the model, and CONTENT_LOADERS above.
    query = scope.query(models.Content).options(*CONTENT_LOADERS)
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


@router.put("/{content_id}/client-ad", response_model=schemas.ContentResponse)
def update_content_client_ad(
    content_id: int,
    payload: schemas.ContentClientAdUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    content = scope.get(models.Content, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if payload.name and payload.name.strip():
        content.name = payload.name.strip()

    # Stripped once, here, because the create and update branches below had drifted: one
    # stored the note as typed and the other trimmed it, so the same text round-tripped
    # differently depending on whether the booking already existed.
    notes = payload.notes.strip() if payload.notes else None

    # Find or create Client
    client_name = payload.client_name.strip()
    client = scope.db.query(models.Client).filter(
        models.Client.organization_id == scope.organization_id,
        models.Client.name.ilike(client_name)
    ).first()

    # `notes` is deliberately NOT written to the client on either branch. The field it
    # comes from is labelled "Campaign Notes / Reference" in the editor and belongs to this
    # booking; writing it here as well meant a per-campaign reference typed against one
    # advert silently replaced the client's permanent note -- the one /dashboard/clients
    # shows -- and then leaked into every later booking through the editor's prefill.
    if not client:
        import re, random
        base_code = re.sub(r'[^A-Za-z0-9]', '', client_name.upper())[:6] or "CLNT"
        rand_suffix = f"{random.randint(100, 999)}"
        client = models.Client(
            organization_id=scope.organization_id,
            name=client_name,
            client_code=f"{base_code}{rand_suffix}",
            email=payload.client_email.strip() if payload.client_email else None,
            phone=payload.client_phone.strip() if payload.client_phone else None,
        )
        scope.db.add(client)
        scope.db.flush()
    else:
        if payload.client_email is not None:
            client.email = payload.client_email.strip() if payload.client_email else None
        if payload.client_phone is not None:
            client.phone = payload.client_phone.strip() if payload.client_phone else None

    # Find existing placement or create new.
    #
    # Everything about a booking below this point is delegated to routers/placements. This
    # used to be a second implementation of it, and every guard that surrounds _place and
    # _unplace everywhere else had been missed here: the ad-slot quota, the plan's location
    # cap counted properly, and above all the push of a changed window onto the playlist
    # item the player actually reads.
    from .placements import (
        _place,
        _screens_for_refs,
        _unplace,
        ensure_ad_slot_quota,
        ensure_plan_locations,
        sync_placement_window,
    )
    from datetime import timedelta
    placement = scope.db.query(models.AdPlacement).filter(
        models.AdPlacement.organization_id == scope.organization_id,
        models.AdPlacement.content_id == content.id
    ).order_by(models.AdPlacement.id.desc()).first()

    plan = scope.get(models.TenantPlan, payload.plan_id) if payload.plan_id else None

    if not placement:
        # The organisation's ad-slot limit binds on this path too. create_placement has
        # always checked it; selling through this editor instead was the way round it.
        ensure_ad_slot_quota(scope)
        now = models.utcnow()
        duration_days = plan.duration_days if plan else 30
        price_paise = plan.price_paise if plan else 0
        placement = models.AdPlacement(
            organization_id=scope.organization_id,
            content_id=content.id,
            client_id=client.id,
            advertiser=client.name,
            plan_id=plan.id if plan else None,
            price_paise=price_paise,
            starts_at=now,
            ends_at=now + timedelta(days=duration_days),
            notes=notes,
        )
        scope.db.add(placement)
        scope.db.flush()
    else:
        placement.client_id = client.id
        placement.advertiser = client.name
        # Tested with `in model_fields_set` rather than `if plan:` so that an explicit null
        # clears the plan. Testing the resolved object meant a booking put on the wrong
        # plan could be moved to another one but never taken off one.
        if "plan_id" in payload.model_fields_set:
            placement.plan_id = plan.id if plan else None
            # Price is NOT copied again here. It is copied once, when the booking is
            # created, and then it is the agreed figure -- routers/placements.py says so
            # where it first copies it, and test_tenant_plans pins that repricing a plan
            # never rebills a campaign already sold on it. Reassigning it on every edit
            # broke that through this door: renaming a client, or correcting a phone
            # number, silently rebilled the booking at today's list price.
        if payload.notes is not None:
            placement.notes = notes

    # Update assigned screens if provided
    if payload.screen_ids is not None:
        target_screen_ids = set(payload.screen_ids)
        # The plan's screen count binds on this path too, and `existing` has to carry the
        # screens reached through GROUP targets, which this edit leaves untouched. Passing
        # an empty set counted a ten-screen group as nothing and let the cap be walked past.
        kept_group_screens = _screens_for_refs(
            scope, [t for t in placement.targets if t.group_id]
        )
        ensure_plan_locations(scope, plan or placement.plan, kept_group_screens, target_screen_ids)

        # Remove targets not in target_screen_ids
        for target in list(placement.targets):
            if target.screen_id and target.screen_id not in target_screen_ids:
                # _unplace already deletes the target row; a second delete here was
                # redundant.
                _unplace(scope, target)
        # Those deletes have to land before placement.targets is read again below, or the
        # re-window loop writes dates onto rows that are already on their way out.
        scope.db.flush()

        # Re-price the run length of places that are already on the booking. Handling only
        # new targets would mean an operator could add a location with 30 days but never
        # afterwards correct it to 10, and the modal would show a number the campaign was
        # not actually running to.
        for target in placement.targets:
            if not target.screen_id:
                continue
            days = (payload.screen_days or {}).get(target.screen_id)
            if days:
                # effective_starts_at is max(own-or-booking, assigned_at) -- the same rule
                # _place applies to a new target, read off the model so there is one copy
                # of it. Using assigned_at bare let a backdated booking start a screen
                # before it had been sold.
                base = target.effective_starts_at
                target.starts_at = base
                target.ends_at = base + timedelta(days=days)
            elif payload.screen_days is not None:
                # Explicitly cleared: this location goes back to following the booking.
                target.starts_at = None
                target.ends_at = None

        # Add new targets
        existing_screen_ids = {t.screen_id for t in placement.targets if t.screen_id}
        for s_id in target_screen_ids:
            if s_id not in existing_screen_ids:
                ref = schemas.PlacementTargetRef(
                    screen_id=s_id,
                    days=(payload.screen_days or {}).get(s_id),
                )
                _place(scope, placement, ref)

        # The whole point of the loop above. Target rows are the record of what was sold;
        # PlaylistItem.start_at/end_at is what the player enforces, and nothing here copied
        # one onto the other -- so correcting a location from 30 days to 10 updated the
        # dashboard and the invoice while the TV kept playing it for 30. It also bumps each
        # affected playlist, without which sync answers 204 and the screen never hears
        # about the change at all.
        sync_placement_window(scope, placement)

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


# Declared last on purpose: FastAPI matches routes in declaration order, so a bare
# "/{content_id}" placed above "/{content_id}/retry" or "/{content_id}/client-ad" would
# swallow them.
@router.get("/{content_id}", response_model=schemas.ContentResponse)
def get_content_item(
    content_id: int,
    scope: TenantScope = Depends(get_tenant_scope),
):
    """One asset, for the pages that show a single advert.

    The detail page used to fetch the whole library and pick its row out in the browser,
    which meant an asset older than the listing's 500-row cap simply rendered "not found"
    -- and every link to one from Campaigns or Invoices dead-ended. It also paid for
    serialising 499 rows nobody was going to look at.
    """
    content = (
        scope.query(models.Content)
        .options(*CONTENT_LOADERS)
        .filter(models.Content.id == content_id)
        .first()
    )
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return serialize_content(content)
