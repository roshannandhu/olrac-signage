"""Ad Placement & Campaign Repository for database persistence operations."""

from typing import Optional, List
from sqlalchemy.orm import Session

from .base import BaseRepository
from .. import models
from ..tenancy import TenantScope


class PlacementRepository(BaseRepository[models.AdPlacement]):
    """Repository handling database operations for Ad Placements, Campaigns, and Clients."""

    def __init__(self, db: Session):
        super().__init__(models.AdPlacement, db)

    def list_by_scope(self, scope: TenantScope) -> List[models.AdPlacement]:
        """Fetch all ad placements for tenant scope."""
        return scope.query(models.AdPlacement).order_by(models.AdPlacement.id.desc()).all()

    def get_by_scope(self, scope: TenantScope, placement_id: int) -> Optional[models.AdPlacement]:
        """Fetch a single ad placement within tenant scope."""
        return scope.query(models.AdPlacement).filter(models.AdPlacement.id == placement_id).first()

    def list_clients(self, scope: TenantScope) -> List[models.Client]:
        """Fetch all ad clients for tenant scope."""
        return scope.query(models.Client).order_by(models.Client.name.asc()).all()

    def get_client(self, scope: TenantScope, client_id: int) -> Optional[models.Client]:
        """Fetch an ad client by id."""
        return scope.query(models.Client).filter(models.Client.id == client_id).first()
