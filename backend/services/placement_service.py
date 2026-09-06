"""Ad Placement & Campaign Management Service."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .base import BaseService
from ..repositories.placement_repo import PlacementRepository
from .. import models, schemas
from ..tenancy import TenantScope
from .playlist_service import bump_playlist

logger = logging.getLogger(__name__)

REPORTING_GRACE = timedelta(hours=1)


def effective_ends_at(placement: models.AdPlacement) -> datetime:
    """When the campaign run actually finishes, accounting for extensions."""
    return placement.effective_ends_at


def total_price_paise(placement: models.AdPlacement) -> int:
    """The booking plus every extension sold against it in paise."""
    return placement.price_paise + sum(e.additional_price_paise for e in placement.extensions)


def settlement(placement: models.AdPlacement) -> Dict[str, Any]:
    """Calculate client billing settlement (total price, amount paid, balance due)."""
    total = total_price_paise(placement)
    if placement.payments:
        received = sum(p.amount_paise for p in placement.payments)
    else:
        received = total if placement.is_paid else 0
    balance = max(0, total - received)
    if received >= total and (placement.payments or placement.is_paid):
        status = "paid"
    elif received > 0:
        status = "part_paid"
    else:
        status = "unpaid"
    return {"total": total, "received": received, "balance": balance, "status": status}


def refresh_paid_state(placement: models.AdPlacement) -> None:
    """Re-derive is_paid from the money after the total or the receipt changed."""
    if not placement.payments:
        return
    settled = settlement(placement)
    placement.is_paid = settled["status"] == "paid"



def playlist_for_target(scope: TenantScope, target: schemas.PlacementTargetRef) -> models.Playlist:
    """Resolve or dynamically provision the target playlist for screen or group booking."""
    if target.screen_id is not None:
        screen = scope.get(models.Screen, target.screen_id)
        if not screen:
            raise HTTPException(status_code=422, detail=f"Unknown screen {target.screen_id}")
        if screen.playlist_id:
            playlist = scope.get(models.Playlist, screen.playlist_id)
            if playlist:
                return playlist

        inherited_id = screen.resolve_playlist_id()
        playlist = models.Playlist(
            organization_id=scope.organization_id,
            name=f"{screen.name or f'Screen {screen.id}'} loop",
        )
        scope.db.add(playlist)
        scope.db.flush()
        if inherited_id:
            inherited_items = (
                scope.db.query(models.PlaylistItem)
                .filter(models.PlaylistItem.playlist_id == inherited_id)
                .order_by(models.PlaylistItem.order)
                .all()
            )
            for source in inherited_items:
                scope.db.add(
                    models.PlaylistItem(
                        playlist_id=playlist.id,
                        content_id=source.content_id,
                        duration=source.duration,
                        order=source.order,
                        start_at=source.start_at,
                        end_at=source.end_at,
                        transition=source.transition,
                        transition_ms=source.transition_ms,
                        rotation=source.rotation,
                    )
                )
            scope.db.flush()
        screen.playlist_id = playlist.id
        screen.assignment_updated_at = models.utcnow()
        return playlist

    group = scope.get(models.ScreenGroup, target.group_id)
    if not group:
        raise HTTPException(status_code=422, detail=f"Unknown group {target.group_id}")
    if group.playlist_id:
        playlist = scope.get(models.Playlist, group.playlist_id)
        if playlist:
            return playlist
    playlist = models.Playlist(organization_id=scope.organization_id, name=f"{group.name} loop")
    scope.db.add(playlist)
    scope.db.flush()
    group.playlist_id = playlist.id
    return playlist


def place_advert(
    scope: TenantScope,
    placement: models.AdPlacement,
    ref: schemas.PlacementTargetRef,
    assigned_at: Optional[datetime] = None,
) -> models.AdPlacementTarget:
    """Inject booked advert into a playlist and record target allocation."""
    playlist = playlist_for_target(scope, ref)
    content = scope.get(models.Content, placement.content_id)

    duration = 10
    if content and content.type == "video" and content.duration_ms:
        duration = max(1, round(content.duration_ms / 1000))

    next_order = (
        scope.db.query(func.coalesce(func.max(models.PlaylistItem.order), -1))
        .filter(models.PlaylistItem.playlist_id == playlist.id)
        .scalar()
    ) + 1

    target_starts_at = max(placement.starts_at, assigned_at or models.utcnow())
    target_ends_at = None
    if getattr(ref, "days", None):
        target_ends_at = target_starts_at + timedelta(days=ref.days)

    item = models.PlaylistItem(
        playlist_id=playlist.id,
        content_id=placement.content_id,
        duration=duration,
        order=next_order,
        start_at=target_starts_at,
        end_at=target_ends_at or effective_ends_at(placement),
    )
    scope.db.add(item)
    scope.db.flush()

    target = models.AdPlacementTarget(
        placement_id=placement.id,
        screen_id=ref.screen_id,
        group_id=ref.group_id,
        playlist_item_id=item.id,
        assigned_at=assigned_at or models.utcnow(),
        starts_at=target_starts_at if target_ends_at else None,
        ends_at=target_ends_at,
    )
    scope.db.add(target)
    scope.db.flush()
    bump_playlist(playlist)
    return target


def unplace_advert(scope: TenantScope, target: models.AdPlacementTarget) -> None:
    """Remove booked advert from its assigned location."""
    if target.playlist_item_id:
        item = (
            scope.db.query(models.PlaylistItem)
            .filter(models.PlaylistItem.id == target.playlist_item_id)
            .first()
        )
        if item:
            if item.playlist:
                bump_playlist(item.playlist)
            scope.db.delete(item)
    scope.db.delete(target)


class PlacementService(BaseService):
    """Application Service orchestrating ad placements and target scheduling."""

    def __init__(self, db: Session, repo: Optional[PlacementRepository] = None):
        super().__init__(db)
        self.repo = repo or PlacementRepository(db)

    def list_placements(self, scope: TenantScope) -> List[models.AdPlacement]:
        return self.repo.list_by_scope(scope)

    def get_placement(self, scope: TenantScope, placement_id: int) -> Optional[models.AdPlacement]:
        return self.repo.get_by_scope(scope, placement_id)
