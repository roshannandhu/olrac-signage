"""Screen Repository for database persistence operations."""

from typing import Optional, List, Dict, Set, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from .base import BaseRepository
from .. import models
from ..tenancy import TenantScope


class ScreenRepository(BaseRepository[models.Screen]):
    """Repository handling database operations for Screens and ScreenGroups."""

    def __init__(self, db: Session):
        super().__init__(models.Screen, db)

    def get_by_device_id(
        self, device_id: str, include_deleted: bool = False
    ) -> Optional[models.Screen]:
        """Look up a screen by its unique hardware device_id."""
        query = self.db.query(models.Screen).filter(models.Screen.device_id == device_id)
        if not include_deleted:
            query = query.filter(models.Screen.deleted_at.is_(None))
        return query.first()

    def get_by_pair_code(self, pair_code: str) -> Optional[models.Screen]:
        """Look up a screen by its 6-digit active pairing code."""
        return (
            self.db.query(models.Screen)
            .filter(
                models.Screen.pair_code == pair_code,
                models.Screen.deleted_at.is_(None),
            )
            .first()
        )

    def list_by_scope(
        self,
        scope: TenantScope,
        group_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[models.Screen]:
        """List screens within tenant scope with optional group and status filtering."""
        query = scope.query(models.Screen)
        if group_id is not None:
            query = query.filter(models.Screen.group_id == group_id)
        if status is not None:
            query = query.filter(models.Screen.status == status)
        return query.order_by(models.Screen.id.asc()).all()

    def get_groups_by_org_ids(self, org_ids: List[int]) -> Dict[int, models.ScreenGroup]:
        """Map screen groups by id for the given organization IDs."""
        valid_ids = {org_id for org_id in org_ids if org_id is not None}
        if not valid_ids:
            return {}
        groups = (
            self.db.query(models.ScreenGroup)
            .filter(models.ScreenGroup.organization_id.in_(valid_ids))
            .all()
        )
        return {group.id: group for group in groups}

    def get_active_emergency_broadcasts(self, org_id: int) -> List[models.EmergencyBroadcast]:
        """Retrieve active emergency broadcasts for an organization."""
        return (
            self.db.query(models.EmergencyBroadcast)
            .filter(
                models.EmergencyBroadcast.organization_id == org_id,
                models.EmergencyBroadcast.is_active == True,
            )
            .all()
        )

    def count_screens_in_org(self, org_id: int) -> int:
        """Count active (non-deleted) screens in an organization."""
        return (
            self.db.query(func.count(models.Screen.id))
            .filter(
                models.Screen.organization_id == org_id,
                models.Screen.deleted_at.is_(None),
            )
            .scalar()
            or 0
        )
