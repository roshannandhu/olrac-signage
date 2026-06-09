import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_session
from app.deps import require_admin
from app.models import Profile, Screen, Playlist, PlaylistItem, Content
from app.responses import ok, fail
from app.schemas import PlaylistPutIn, PlaylistItemRead

router = APIRouter()


@router.get("/screens/{screen_id}/playlist")
async def get_playlist(
    screen_id: uuid.UUID,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Return the screen's playlist items ordered by position, each joined with content."""
    # Verify screen ownership
    screen_result = await session.execute(
        select(Screen).where(Screen.id == screen_id, Screen.owner_id == profile.id)
    )
    screen = screen_result.scalar_one_or_none()
    if screen is None:
        return fail("Screen not found", "not_found", 404)

    playlist_result = await session.execute(
        select(Playlist)
        .options(joinedload(Playlist.items).joinedload(PlaylistItem.content))
        .where(Playlist.screen_id == screen_id)
    )
    playlist = playlist_result.unique().scalar_one_or_none()

    if playlist is None:
        return ok([])

    items = sorted(playlist.items, key=lambda i: i.position)
    return ok([PlaylistItemRead.model_validate(i) for i in items])


@router.put("/screens/{screen_id}/playlist")
async def put_playlist(
    screen_id: uuid.UUID,
    body: PlaylistPutIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Replace the screen's playlist in one transaction."""
    # Verify screen ownership
    screen_result = await session.execute(
        select(Screen).where(Screen.id == screen_id, Screen.owner_id == profile.id)
    )
    screen = screen_result.scalar_one_or_none()
    if screen is None:
        return fail("Screen not found", "not_found", 404)

    # Validate all content_ids belong to the caller
    for item in body.items:
        c_result = await session.execute(
            select(Content).where(
                Content.id == item.content_id, Content.owner_id == profile.id
            )
        )
        if c_result.scalar_one_or_none() is None:
            return fail(
                f"Unknown content in playlist: {item.content_id}",
                "bad_content",
                400,
            )

    # Get-or-create the playlist row for this screen
    playlist_result = await session.execute(
        select(Playlist).where(Playlist.screen_id == screen_id)
    )
    playlist = playlist_result.scalar_one_or_none()

    if playlist is None:
        playlist = Playlist(screen_id=screen_id, group_id=None)
        session.add(playlist)
        await session.flush()

    # Delete existing items
    existing = await session.execute(
        select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id)
    )
    for item in existing.scalars().all():
        await session.delete(item)

    # Insert new items
    for pi in body.items:
        new_item = PlaylistItem(
            playlist_id=playlist.id,
            content_id=pi.content_id,
            position=pi.position,
            duration_override=pi.duration_override,
        )
        session.add(new_item)

    playlist.updated_at = datetime.now(timezone.utc)  # trigger update explicitly

    await session.commit()

    # Fetch and return saved items
    result = await session.execute(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.content))
        .where(PlaylistItem.playlist_id == playlist.id)
        .order_by(PlaylistItem.position)
    )
    saved = result.unique().scalars().all()
    return ok([PlaylistItemRead.model_validate(i) for i in saved])
