from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from uuid import UUID
from app.models import Playlist, PlaylistItem, Content, Screen, GroupScreen


async def resolve_playlist_for_screen(
    session: AsyncSession, screen_id: UUID
) -> list[dict]:
    """Resolve the effective playlist for a screen.

    Rule (B5 will fully implement this):
      1. Find the groups this screen belongs to.
      2. If any group has a playlist with ≥1 item → use that group playlist.
      3. Otherwise → use the screen's own playlist (or [] if none).
      4. Return items ordered by position, each with full content data.
    """
    # Step 1: check group membership
    group_result = await session.execute(
        select(GroupScreen).where(GroupScreen.screen_id == screen_id)
    )
    group_links = group_result.scalars().all()

    for link in group_links:
        playlist_result = await session.execute(
            select(Playlist)
            .options(joinedload(Playlist.items).joinedload(PlaylistItem.content))
            .where(Playlist.group_id == link.group_id)
        )
        group_playlist = playlist_result.unique().scalar_one_or_none()
        if group_playlist and group_playlist.items:
            return _items_to_dicts(group_playlist.items)

    # Step 3: fall back to screen's own playlist
    playlist_result = await session.execute(
        select(Playlist)
        .options(joinedload(Playlist.items).joinedload(PlaylistItem.content))
        .where(Playlist.screen_id == screen_id)
    )
    screen_playlist = playlist_result.unique().scalar_one_or_none()
    if screen_playlist:
        return _items_to_dicts(screen_playlist.items)

    return []


def _items_to_dicts(items: list[PlaylistItem]) -> list[dict]:
    """Convert PlaylistItem ORM rows to the API response shape."""
    result = []
    for item in sorted(items, key=lambda i: i.position):
        c = item.content
        result.append(
            {
                "id": str(item.id),
                "position": item.position,
                "duration_override": item.duration_override,
                "content": {
                    "id": str(c.id),
                    "name": c.name,
                    "type": c.type,
                    "orientation": c.orientation,
                    "public_url": c.public_url,
                    "duration_seconds": c.duration_seconds,
                },
            }
        )
    return result
