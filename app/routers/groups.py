import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import get_session
from app.deps import require_admin
from app.models import (
    Profile, Screen, ScreenGroup, GroupScreen, Playlist, PlaylistItem, Content,
)
from app.responses import ok, fail
from app.schemas import (
    GroupCreateIn, GroupPatchIn, PlaylistPutIn, PlaylistItemRead, GroupRead, ScreenRead,
)

router = APIRouter()


def _build_group_read(group: ScreenGroup, screens: list[Screen], has_playlist: bool) -> dict:
    return {
        "id": str(group.id),
        "name": group.name,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "screens": [ScreenRead.model_validate(s).model_dump() for s in screens],
        "has_playlist": has_playlist,
    }


@router.get("")
async def list_groups(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List all groups owned by the caller, each with its screens."""
    result = await session.execute(
        select(ScreenGroup).where(ScreenGroup.owner_id == profile.id)
    )
    groups = result.scalars().all()

    output = []
    for g in groups:
        # Load screens via group_screens
        gs_result = await session.execute(
            select(Screen)
            .join(GroupScreen, GroupScreen.screen_id == Screen.id)
            .where(GroupScreen.group_id == g.id)
        )
        screens = gs_result.scalars().all()

        # Check for playlist
        pl_result = await session.execute(
            select(Playlist)
            .options(joinedload(Playlist.items))
            .where(Playlist.group_id == g.id)
        )
        pl = pl_result.unique().scalar_one_or_none()
        has_playlist = pl is not None and len(pl.items) > 0

        output.append(_build_group_read(g, screens, has_playlist))

    return ok(output)


@router.post("")
async def create_group(
    body: GroupCreateIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create a screen group with optional screen membership."""
    group = ScreenGroup(owner_id=profile.id, name=body.name)
    session.add(group)
    await session.flush()

    # Validate and link screens
    for sid in body.screen_ids:
        s_result = await session.execute(
            select(Screen).where(Screen.id == sid, Screen.owner_id == profile.id)
        )
        s = s_result.scalar_one_or_none()
        if s is None:
            await session.rollback()
            return fail(f"Screen not found: {sid}", "not_found", 404)
        session.add(GroupScreen(group_id=group.id, screen_id=sid))

    await session.commit()

    # Reload with screens
    gs_result = await session.execute(
        select(Screen)
        .join(GroupScreen, GroupScreen.screen_id == Screen.id)
        .where(GroupScreen.group_id == group.id)
    )
    screens = gs_result.scalars().all()

    return ok(_build_group_read(group, screens, False))


@router.patch("/{group_id}")
async def patch_group(
    group_id: uuid.UUID,
    body: GroupPatchIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Update group name and/or replace screen membership."""
    result = await session.execute(
        select(ScreenGroup).where(
            ScreenGroup.id == group_id, ScreenGroup.owner_id == profile.id
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        return fail("Group not found", "not_found", 404)

    if body.name is not None:
        group.name = body.name

    if body.screen_ids is not None:
        # Replace membership
        await session.execute(
            delete(GroupScreen).where(GroupScreen.group_id == group_id)
        )
        for sid in body.screen_ids:
            s_result = await session.execute(
                select(Screen).where(Screen.id == sid, Screen.owner_id == profile.id)
            )
            s = s_result.scalar_one_or_none()
            if s is None:
                await session.rollback()
                return fail(f"Screen not found: {sid}", "not_found", 404)
            session.add(GroupScreen(group_id=group_id, screen_id=sid))

    await session.commit()

    # Reload
    gs_result = await session.execute(
        select(Screen)
        .join(GroupScreen, GroupScreen.screen_id == Screen.id)
        .where(GroupScreen.group_id == group.id)
    )
    screens = gs_result.scalars().all()

    pl_result = await session.execute(
        select(Playlist)
        .options(joinedload(Playlist.items))
        .where(Playlist.group_id == group.id)
    )
    pl = pl_result.unique().scalar_one_or_none()
    has_playlist = pl is not None and len(pl.items) > 0

    return ok(_build_group_read(group, screens, has_playlist))


@router.put("/{group_id}/playlist")
async def put_group_playlist(
    group_id: uuid.UUID,
    body: PlaylistPutIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Replace a group's playlist in one transaction."""
    result = await session.execute(
        select(ScreenGroup).where(
            ScreenGroup.id == group_id, ScreenGroup.owner_id == profile.id
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        return fail("Group not found", "not_found", 404)

    # Validate content ownership
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

    # Get-or-create playlist for this group
    pl_result = await session.execute(
        select(Playlist).where(Playlist.group_id == group_id)
    )
    playlist = pl_result.scalar_one_or_none()
    if playlist is None:
        playlist = Playlist(group_id=group_id, screen_id=None)
        session.add(playlist)
        await session.flush()

    # Delete existing items
    existing = await session.execute(
        select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id)
    )
    for pi in existing.scalars().all():
        await session.delete(pi)

    # Insert new items
    for pi in body.items:
        new_item = PlaylistItem(
            playlist_id=playlist.id,
            content_id=pi.content_id,
            position=pi.position,
            duration_override=pi.duration_override,
        )
        session.add(new_item)

    playlist.updated_at = None

    await session.commit()

    result = await session.execute(
        select(PlaylistItem)
        .options(joinedload(PlaylistItem.content))
        .where(PlaylistItem.playlist_id == playlist.id)
        .order_by(PlaylistItem.position)
    )
    saved = result.unique().scalars().all()
    return ok([PlaylistItemRead.model_validate(i) for i in saved])


@router.delete("/{group_id}")
async def delete_group(
    group_id: uuid.UUID,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ScreenGroup).where(
            ScreenGroup.id == group_id, ScreenGroup.owner_id == profile.id
        )
    )
    group = result.scalar_one_or_none()
    if group is None:
        return fail("Group not found", "not_found", 404)

    await session.delete(group)
    await session.commit()
    return ok({"ok": True})
