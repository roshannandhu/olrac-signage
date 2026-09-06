"""Screen Content & Playlist Resolution Service."""

import logging
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session

from .base import BaseService
from ..repositories.screen_repo import ScreenRepository
from .. import models

logger = logging.getLogger(__name__)

MAX_GROUP_DEPTH = 10


def groups_by_id(db: Session, organization_ids: List[Optional[int]]) -> Dict[int, models.ScreenGroup]:
    """Map screen groups by id for fast ancestry walking during playlist resolution."""
    ids = {org_id for org_id in organization_ids if org_id is not None}
    if not ids:
        return {}
    return {
        group.id: group
        for group in db.query(models.ScreenGroup)
        .filter(models.ScreenGroup.organization_id.in_(ids))
        .all()
    }


def resolve_screen_playlist(screen: models.Screen, db: Session) -> Optional[int]:
    """Determine the active playlist ID a screen should be playing right now.

    Priority:
    1. Active Emergency Broadcasts (target_type: screen > group > all)
    2. Inherited group playlist or dynamic group playlist (via models.Screen.resolve_playlist_id)
    """
    groups = groups_by_id(db, [screen.organization_id])

    active_broadcasts = (
        db.query(models.EmergencyBroadcast)
        .filter(
            models.EmergencyBroadcast.organization_id == screen.organization_id,
            models.EmergencyBroadcast.is_active == True,
        )
        .all()
    )

    # Priority 1: Screen-targeted emergency broadcast
    for broadcast in active_broadcasts:
        if broadcast.target_type == "screen" and broadcast.target_id == screen.id:
            return broadcast.playlist_id

    # Priority 2: Group-targeted emergency broadcast across ancestor hierarchy
    screen_group_ids = []
    group = groups.get(screen.group_id)
    for _ in range(MAX_GROUP_DEPTH):
        if group is None:
            break
        screen_group_ids.append(group.id)
        group = groups.get(group.parent_id)

    for broadcast in active_broadcasts:
        if broadcast.target_type == "group" and broadcast.target_id in screen_group_ids:
            return broadcast.playlist_id

    # Priority 3: All-organization emergency broadcast
    for broadcast in active_broadcasts:
        if broadcast.target_type == "all":
            return broadcast.playlist_id

    # Default: Screen's configured playlist (direct, inherited, or dynamic group match)
    return screen.resolve_playlist_id(groups)


class ScreenContentService(BaseService):
    """Application Service for resolving and streaming content configurations for screens."""

    def __init__(self, db: Session, repo: Optional[ScreenRepository] = None):
        super().__init__(db)
        self.repo = repo or ScreenRepository(db)

    def resolve_playlist(self, screen: models.Screen) -> Optional[int]:
        return resolve_screen_playlist(screen, self.db)

    def get_screen_groups(self, organization_ids: List[Optional[int]]) -> Dict[int, models.ScreenGroup]:
        return groups_by_id(self.db, organization_ids)
