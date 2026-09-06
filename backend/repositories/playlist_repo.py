"""Playlist Repository for database persistence operations."""

from typing import Optional, List, Set
from sqlalchemy.orm import Session, selectinload

from .base import BaseRepository
from .. import models
from ..tenancy import TenantScope


# Eager-load chain to avoid N+1 queries when loading playlist with content and items
PLAYLIST_LOAD = (
    selectinload(models.Playlist.items)
    .selectinload(models.PlaylistItem.content)
    .selectinload(models.Content.playlist_items),
)


class PlaylistRepository(BaseRepository[models.Playlist]):
    """Repository handling database operations for Playlists and PlaylistItems."""

    def __init__(self, db: Session):
        super().__init__(models.Playlist, db)

    def list_by_scope(self, scope: TenantScope) -> List[models.Playlist]:
        """Fetch all playlists for tenant scope with eager loaded content and items."""
        return (
            scope.query(models.Playlist)
            .options(*PLAYLIST_LOAD)
            .order_by(models.Playlist.updated_at.desc())
            .all()
        )

    def get_by_scope(self, scope: TenantScope, playlist_id: int) -> Optional[models.Playlist]:
        """Fetch a single playlist with eager loaded relations within tenant scope."""
        return (
            scope.query(models.Playlist)
            .options(*PLAYLIST_LOAD)
            .filter(models.Playlist.id == playlist_id)
            .first()
        )

    def get_item(self, playlist_id: int, item_id: int) -> Optional[models.PlaylistItem]:
        """Fetch a specific playlist item by id and playlist id."""
        return (
            self.db.query(models.PlaylistItem)
            .filter(
                models.PlaylistItem.id == item_id,
                models.PlaylistItem.playlist_id == playlist_id,
            )
            .first()
        )

    def add_item(self, item: models.PlaylistItem) -> models.PlaylistItem:
        """Add a new item to a playlist."""
        self.db.add(item)
        self.db.flush()
        return item

    def delete_item(self, item: models.PlaylistItem) -> None:
        """Remove a playlist item."""
        self.db.delete(item)
        self.db.flush()
