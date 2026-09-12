"""Ad Placement & Campaign Management Service."""

import logging
from dataclasses import dataclass
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
    """What the client owes, what they have handed over, and what is left.

    One derivation, because there were five and they disagreed. The bookings section, the
    ad's own header, the invoices page and the invoice PDF each subtracted the payment from
    the total in their own way, and `is_paid` -- a bare boolean -- was read as "settled in
    full" by all of them while being set to true by ANY payment. Recording 5,000 against a
    50,000 campaign therefore printed "Paid in full" on the ad page, "Paid" on the screen
    page, and "Part paid - 45,000 outstanding" on the invoice, off the same row.

    `is_paid` survives as the stored flag and is now kept equal to "balance is zero"
    wherever money or the total moves. A booking marked paid before payments were recorded
    has no amount behind it, so its receipt is taken at face value and counted as settled --
    otherwise migrating that flag into arithmetic would reopen every historical campaign.
    """
    total = total_price_paise(placement)
    # The SUM of the receipts, not the latest one. A deposit in March and the balance in
    # May are two rows and one campaign.
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
    """Re-derive `is_paid` from the money after the total or the receipt changed.

    Called from every path that can move either side of the sum -- recording a payment,
    selling an extension, cancelling one, moving the booking to another plan, correcting
    the price. Without it an extension sold against a settled booking left the flag reading
    "paid" over a balance the client still owed.

    Only touched when at least one receipt exists. A booking whose flag predates payments
    has no amount to compare against, and flipping it to unpaid here would present every
    historical campaign as owing its full price again.
    """
    if not placement.payments:
        return
    settled = settlement(placement)
    placement.is_paid = settled["status"] == "paid"



def playlist_for_target(scope: TenantScope, target: schemas.PlacementTargetRef) -> models.Playlist:
    """The playlist a booking should write into for this screen or group.

    A place with no playlist yet gets one, otherwise selling an ad to a brand new screen
    would silently do nothing. This is also why the dashboard does not ask an operator to
    create a playlist for a freshly paired TV -- the first booking provisions it.
    """
    if target.screen_id is not None:
        screen = scope.get(models.Screen, target.screen_id)
        if not screen:
            raise HTTPException(status_code=422, detail=f"Unknown screen {target.screen_id}")
        if screen.playlist_id:
            playlist = scope.get(models.Playlist, screen.playlist_id)
            if playlist:
                return playlist

        # The screen has no playlist of its OWN, but it may still be playing one it
        # inherits from a group. Two things must not happen here, and both used to:
        #
        #   - writing the advert into the inherited playlist would put it on every other
        #     screen in that group, which is not what was sold. The booking would report
        #     one location while ten TVs ran it.
        #   - giving the screen a fresh empty playlist silently takes the group's loop
        #     away from it -- the screen goes from playing the venue's content to playing
        #     one advert and nothing else.
        #
        # So it gets its own playlist seeded with what it was already playing, and the
        # advert lands on top.
        #
        # ponytail: a fork, not a link. Later edits to the group's loop no longer reach
        # this screen -- which is what "this screen is booked separately" has to mean --
        # but it is a real divergence and the screen page's "inherited from group" notice
        # correctly stops showing.
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


@dataclass(frozen=True)
class SystemScope:
    """Organisation-scoped access for background work that has no signed-in user.

    `place_advert` and `playlist_for_target` need `db`, `organization_id`, `get` and
    `query`. TenantScope derives those from a User, which a reconcile loop does not have.
    The filters are the same ones TenantScope applies, so background work cannot reach
    across organisations or resurrect archived rows either.
    """

    db: Session
    organization_id: int

    def get(self, model, record_id):
        if not record_id:
            return None
        return self.query(model).filter(model.id == record_id).first()

    def query(self, model):
        query = self.db.query(model)
        organization_column = getattr(model, "organization_id", None)
        if organization_column is not None:
            query = query.filter(organization_column == self.organization_id)
        archived_column = getattr(model, "deleted_at", None)
        if archived_column is not None:
            query = query.filter(archived_column.is_(None))
        return query


def repair_orphaned_targets(scope, placement: models.AdPlacement) -> int:
    """Put a booking back on every place it has silently fallen off. Returns how many.

    A target holds the playlist item it created, and that column is ON DELETE SET NULL,
    while PlaylistItem cascades from BOTH its playlist and its content. So deleting a
    playlist or a creative takes the items away and nulls the link on every booking that
    used them -- the booking survives, still Running and still Paid, playing on nothing.

    A target left like that is ALWAYS breakage, never intent: stopping an advert in one
    place goes through `unplace_advert`, which deletes the target row outright. A target
    that still exists with no item is a broken invariant, so it is safe to restore.

    Idempotent and additive. A target still holding its item is untouched, so this cannot
    duplicate an advert into a loop.
    """
    orphaned = [target for target in placement.targets if target.playlist_item_id is None]
    if not orphaned:
        return 0

    for target in orphaned:
        ref = schemas.PlacementTargetRef(
            screen_id=target.screen_id,
            group_id=target.group_id,
            # Its own window if it had one, so a location sold ten days does not silently
            # inherit the booking's thirty on the way back.
            days=(
                max(1, round((target.ends_at - target.starts_at).total_seconds() / 86400))
                if target.ends_at and target.starts_at
                else None
            ),
        )
        # From the ORIGINAL assignment date, not today: the client's report divides this
        # location's plays by the days it really ran, and restarting the clock here would
        # report a location that has run all month as a late addition.
        restored = place_advert(scope, placement, ref, assigned_at=target.assigned_at)
        # The new row carries the item; the empty one it replaces would otherwise sit there
        # as a second, permanently unplaced copy of the same location.
        scope.db.delete(target)
        logger.info(
            "Booking %s re-placed on %s (target %s -> %s)",
            placement.id,
            f"screen {target.screen_id}" if target.screen_id else f"group {target.group_id}",
            target.id,
            restored.id,
        )
    return len(orphaned)


def reconcile_unplaced_bookings(db: Session, now=None) -> int:
    """Restore every RUNNING booking that has lost the items it placed.

    Runs on a timer in the app process rather than as a scheduled job, deliberately: the
    scheduled jobs need Redis, and this is most needed exactly when the deployment is in a
    degraded state. A booking that is sold, paid and playing on nothing is invisible from
    the dashboard -- it still reads "Running" -- so waiting for someone to notice and press
    a button is waiting for a client to ring up about an advert that never ran.

    Only bookings whose window is open now. A finished one is supposed to have no items.
    """
    now = now or models.utcnow()
    placements = (
        db.query(models.AdPlacement)
        .join(models.AdPlacementTarget,
              models.AdPlacementTarget.placement_id == models.AdPlacement.id)
        .filter(
            models.AdPlacementTarget.playlist_item_id.is_(None),
            models.AdPlacement.starts_at <= now,
            models.AdPlacement.effective_ends_at > now,
        )
        .distinct()
        .all()
    )
    repaired = 0
    for placement in placements:
        # One booking per transaction. Committing once at the end looks tidier and is wrong:
        # a single unrepairable booking rolls the session back, and the rollback takes every
        # repair already staged in that pass with it. Observed doing exactly that -- three
        # bookings came back, a fourth silently did not, and the difference was only which
        # side of the failure they were processed on.
        try:
            count = repair_orphaned_targets(
                SystemScope(db=db, organization_id=placement.organization_id), placement
            )
            if count:
                db.commit()
                repaired += count
        except Exception:
            # A deleted screen, a creative that is gone. Must not stop the rest.
            db.rollback()
            logger.exception("Could not re-place booking %s", placement.id)
    if repaired:
        logger.info("Re-placed %d location(s) on bookings that had fallen off their screens", repaired)
    return repaired


class PlacementService(BaseService):
    """Application Service orchestrating ad placements and target scheduling."""

    def __init__(self, db: Session, repo: Optional[PlacementRepository] = None):
        super().__init__(db)
        self.repo = repo or PlacementRepository(db)

    def list_placements(self, scope: TenantScope) -> List[models.AdPlacement]:
        return self.repo.list_by_scope(scope)

    def get_placement(self, scope: TenantScope, placement_id: int) -> Optional[models.AdPlacement]:
        return self.repo.get_by_scope(scope, placement_id)
