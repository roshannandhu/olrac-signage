import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import Content, Profile
from app.responses import ok, fail
from app.schemas import ContentRead, ContentPatchIn
from app.supabase_client import supabase

router = APIRouter()


def _sanitize_filename(name: str) -> str:
    """Strip path separators and keep only safe chars."""
    import re
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w\.\-]", "_", name)
    return name


def _parse_tags(tags_str: Optional[str]) -> list[str]:
    if not tags_str or not tags_str.strip():
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


@router.get("")
async def list_content(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    type: Optional[str] = Query(None, pattern="^(video|image)$"),
    orientation: Optional[str] = Query(None, pattern="^(landscape|portrait)$"),
    sort: str = Query("newest", pattern="^(newest|oldest|az|za)$"),
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
):
    query = select(Content).where(Content.owner_id == profile.id)

    if type:
        query = query.where(Content.type == type)
    if orientation:
        query = query.where(Content.orientation == orientation)
    if search:
        query = query.where(Content.name.ilike(f"%{search}%"))
    if tags:
        tag_list = _parse_tags(tags)
        if tag_list:
            query = query.where(Content.tags.overlap(tag_list))

    sort_map = {
        "newest": Content.created_at.desc(),
        "oldest": Content.created_at.asc(),
        "az": Content.name.asc(),
        "za": Content.name.desc(),
    }
    query = query.order_by(sort_map.get(sort, Content.created_at.desc()))

    result = await session.execute(query)
    items = result.scalars().all()
    return ok([ContentRead.model_validate(i) for i in items])


@router.post("/upload")
async def upload_content(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
):
    # 1. Detect type from mimetype
    ctype = file.content_type or ""
    if ctype.startswith("image/"):
        content_type = "image"
    elif ctype.startswith("video/"):
        content_type = "video"
    else:
        return fail("Unsupported file type", "bad_type", 400)

    # 2. Build storage path
    file_bytes = await file.read()
    original_name = file.filename or "unnamed"
    safe_name = _sanitize_filename(original_name)
    storage_path = f"{profile.id}/{uuid.uuid4()}-{safe_name}"

    # 3. Upload to Supabase Storage
    try:
        supabase.storage.from_("media").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": ctype, "upsert": "false"},
        )
    except Exception as exc:
        return fail(f"Upload failed: {exc}", "storage_error", 502)

    # 4. Get public URL (strip trailing "?" if any)
    public_url = supabase.storage.from_("media").get_public_url(storage_path)
    if public_url.endswith("?"):
        public_url = public_url[:-1]

    # 5. Insert content row
    content_name = name or original_name
    content = Content(
        owner_id=profile.id,
        name=content_name,
        type=content_type,
        orientation="landscape",  # TODO: real orientation/duration probing
        storage_path=storage_path,
        public_url=public_url,
        duration_seconds=0,
        file_size=len(file_bytes),
        tags=_parse_tags(tags),
    )
    session.add(content)
    await session.commit()
    await session.refresh(content)

    # 6. Return
    return ok(ContentRead.model_validate(content))


@router.patch("/{content_id}")
async def patch_content(
    content_id: uuid.UUID,
    body: ContentPatchIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Content).where(Content.id == content_id, Content.owner_id == profile.id)
    )
    content = result.scalar_one_or_none()
    if content is None:
        return fail("Content not found", "not_found", 404)

    update_data = body.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = _parse_tags(update_data["tags"])

    for field, value in update_data.items():
        if value is not None:
            setattr(content, field, value)

    await session.commit()
    await session.refresh(content)
    return ok(ContentRead.model_validate(content))


@router.delete("/{content_id}")
async def delete_content(
    content_id: uuid.UUID,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Content).where(Content.id == content_id, Content.owner_id == profile.id)
    )
    content = result.scalar_one_or_none()
    if content is None:
        return fail("Content not found", "not_found", 404)

    # Delete from Storage (ignore "not found")
    try:
        supabase.storage.from_("media").remove([content.storage_path])
    except Exception:
        pass

    await session.delete(content)
    await session.commit()
    return ok({"ok": True})
