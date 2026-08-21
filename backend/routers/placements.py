"""Selling an advert: which client, for how long, in which places.

The placement is a record of the deal. The thing that actually plays is still an ordinary
playlist item, created and removed by this module on the placement's behalf. Everything
downstream — the player sync, proof-of-play, rendition selection, rotation — keeps reading
playlist items and needs no knowledge that bookings exist.
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, text

from .. import models, schemas
from ..tenancy import TenantScope, require_tenant_roles

logger = logging.getLogger(__name__)

# How far behind the clock a screen may be before its figures are called into question.
# Matches the hour the Alerts page treats as offline.
REPORTING_GRACE = timedelta(hours=1)

router = APIRouter()


def _playlist_for_target(scope: TenantScope, target: schemas.PlacementTargetRef) -> models.Playlist:
    """The playlist a booking should write into for this screen or group.

    A place with no playlist yet gets one, otherwise selling an ad to a brand new screen
    would silently do nothing.
    """
    if target.screen_id is not None:
        screen = scope.get(models.Screen, target.screen_id)
        if not screen:
            raise HTTPException(status_code=422, detail=f"Unknown screen {target.screen_id}")
        if screen.playlist_id:
            playlist = scope.get(models.Playlist, screen.playlist_id)
            if playlist:
                return playlist
        playlist = models.Playlist(
            organization_id=scope.organization_id,
            name=f"{screen.name or f'Screen {screen.id}'} loop",
        )
        scope.db.add(playlist)
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


def _place(scope: TenantScope, placement: models.AdPlacement, ref: schemas.PlacementTargetRef) -> models.AdPlacementTarget:
    """Put the booked advert into one place and remember the item we created."""
    playlist = _playlist_for_target(scope, ref)
    content = scope.get(models.Content, placement.content_id)

    # A video runs for its own length; an image needs a chosen dwell time.
    duration = 10
    if content and content.type == "video" and content.duration_ms:
        duration = max(1, round(content.duration_ms / 1000))

    next_order = (
        scope.db.query(func.coalesce(func.max(models.PlaylistItem.order), -1))
        .filter(models.PlaylistItem.playlist_id == playlist.id)
        .scalar()
    ) + 1

    item = models.PlaylistItem(
        playlist_id=playlist.id,
        content_id=placement.content_id,
        duration=duration,
        order=next_order,
        # The paid window is enforced by the same start/end the player already honours.
        start_at=placement.starts_at,
        end_at=placement.ends_at,
    )
    scope.db.add(item)
    scope.db.flush()

    target = models.AdPlacementTarget(
        placement_id=placement.id,
        screen_id=ref.screen_id,
        group_id=ref.group_id,
        playlist_item_id=item.id,
    )
    scope.db.add(target)
    scope.db.flush()
    return target


def _unplace(scope: TenantScope, target: models.AdPlacementTarget) -> None:
    """Remove the advert from this one place, leaving every other place untouched."""
    if target.playlist_item_id:
        item = scope.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.id == target.playlist_item_id
        ).first()
        if item:
            scope.db.delete(item)
    scope.db.delete(target)


def _serialize(scope: TenantScope, placement: models.AdPlacement) -> schemas.PlacementResponse:
    screen_names = dict(scope.db.query(models.Screen.id, models.Screen.name).all())
    group_names = dict(scope.db.query(models.ScreenGroup.id, models.ScreenGroup.name).all())
    return schemas.PlacementResponse(
        id=placement.id,
        content_id=placement.content_id,
        advertiser=placement.advertiser,
        price_paise=placement.price_paise,
        is_paid=placement.is_paid,
        starts_at=placement.starts_at,
        ends_at=placement.ends_at,
        notes=placement.notes,
        created_at=placement.created_at,
        targets=[
            schemas.PlacementTargetResponse(
                id=t.id,
                screen_id=t.screen_id,
                group_id=t.group_id,
                name=(screen_names.get(t.screen_id) or f"Screen {t.screen_id}") if t.screen_id
                else (group_names.get(t.group_id) or f"Group {t.group_id}"),
                kind="screen" if t.screen_id else "group",
                is_placed=t.playlist_item_id is not None,
            )
            for t in placement.targets
        ],
    )


@router.get("/", response_model=list[schemas.PlacementResponse])
def list_placements(
    content_id: int | None = None,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
):
    query = scope.query(models.AdPlacement)
    if content_id is not None:
        query = query.filter(models.AdPlacement.content_id == content_id)
    return [_serialize(scope, p) for p in query.order_by(models.AdPlacement.created_at.desc()).all()]


@router.post("/", response_model=schemas.PlacementResponse, status_code=201)
def create_placement(
    payload: schemas.PlacementCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    if not scope.get(models.Content, payload.content_id):
        raise HTTPException(status_code=404, detail="Content not found")

    placement = models.AdPlacement(
        organization_id=scope.organization_id,
        content_id=payload.content_id,
        advertiser=payload.advertiser.strip(),
        price_paise=payload.price_paise,
        is_paid=payload.is_paid,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        notes=payload.notes,
    )
    scope.db.add(placement)
    scope.db.flush()

    for ref in payload.targets:
        _place(scope, placement, ref)

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.put("/{placement_id}", response_model=schemas.PlacementResponse)
def update_placement(
    placement_id: int,
    payload: schemas.PlacementUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    fields = payload.model_fields_set
    for field in ("advertiser", "price_paise", "is_paid", "notes", "starts_at", "ends_at"):
        if field in fields:
            setattr(placement, field, getattr(payload, field))
    if placement.ends_at <= placement.starts_at:
        raise HTTPException(status_code=422, detail="The end date must be after the start date")

    # Every placed item carries the booking's window, so moving the dates moves them all.
    if "starts_at" in fields or "ends_at" in fields:
        for target in placement.targets:
            if target.playlist_item_id:
                item = scope.db.query(models.PlaylistItem).filter(
                    models.PlaylistItem.id == target.playlist_item_id
                ).first()
                if item:
                    item.start_at = placement.starts_at
                    item.end_at = placement.ends_at

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.post("/{placement_id}/targets", response_model=schemas.PlacementResponse, status_code=201)
def add_target(
    placement_id: int,
    ref: schemas.PlacementTargetRef,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    already = any(
        (t.screen_id == ref.screen_id and ref.screen_id is not None)
        or (t.group_id == ref.group_id and ref.group_id is not None)
        for t in placement.targets
    )
    if already:
        raise HTTPException(status_code=409, detail="This booking already runs in that place")

    _place(scope, placement, ref)
    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.delete("/{placement_id}/targets/{target_id}", response_model=schemas.PlacementResponse)
def remove_target(
    placement_id: int,
    target_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Stop this advert playing in one place. Everywhere else is unaffected."""
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    target = next((t for t in placement.targets if t.id == target_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="This booking does not run in that place")

    _unplace(scope, target)
    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.post("/{placement_id}/targets/{target_id}/split", response_model=schemas.PlacementResponse)
def split_group_target(
    placement_id: int,
    target_id: int,
    payload: schemas.PlacementSplit,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Take a group booking off one screen without disturbing the rest of the group.

    A group target places a single item in the shared group playlist, so it cannot be
    removed from one member alone. This replaces it with one target per remaining screen,
    which gives the same result and keeps a single rule deciding what plays.
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    target = next((t for t in placement.targets if t.id == target_id), None)
    if not target or not target.group_id:
        raise HTTPException(status_code=404, detail="That is not a group booking")

    members = scope.query(models.Screen).filter(models.Screen.group_id == target.group_id).all()
    keep = [s for s in members if s.id not in set(payload.exclude_screen_ids)]
    if not keep:
        raise HTTPException(status_code=422, detail="That would leave the booking with nowhere to play")

    _unplace(scope, target)
    for screen in keep:
        _place(scope, placement, schemas.PlacementTargetRef(screen_id=screen.id))

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.delete("/{placement_id}")
def delete_placement(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    for target in list(placement.targets):
        _unplace(scope, target)
    scope.db.delete(placement)
    scope.db.commit()
    return {"status": "deleted"}


def _booking_screen_ids(scope: TenantScope, placement: models.AdPlacement) -> list[int]:
    """Every screen this booking actually reaches.

    A group target is expanded to its current members, because that is what the advert
    physically played on — the client bought "the mall", not "a row in a groups table".
    """
    screen_ids: set[int] = set()
    group_ids: list[int] = []
    for target in placement.targets:
        if target.screen_id:
            screen_ids.add(target.screen_id)
        elif target.group_id:
            group_ids.append(target.group_id)
    if group_ids:
        members = scope.query(models.Screen).filter(models.Screen.group_id.in_(group_ids)).all()
        screen_ids.update(screen.id for screen in members)
    return sorted(screen_ids)


def build_booking_report(scope: TenantScope, placement: models.AdPlacement) -> dict:
    """Proof of delivery for one booking: only its window, only its screens.

    Scoping is the whole point. The per-advert report elsewhere totals every play of that
    creative for all time; handing that to a client would bill them for another client's
    booking of the same file, or for plays from before they paid.
    """
    content = scope.get(models.Content, placement.content_id)
    screen_ids = _booking_screen_ids(scope, placement)
    generated_at = models.utcnow()

    empty = {"total_plays": 0, "completed_plays": 0, "error_plays": 0, "success_percent": 0.0}
    if not screen_ids:
        return {
            "placement_id": placement.id,
            "advertiser": placement.advertiser,
            "content_name": content.name if content else "Unknown",
            "content_id": placement.content_id,
            "starts_at": placement.starts_at,
            "ends_at": placement.ends_at,
            "price_paise": placement.price_paise,
            "is_paid": placement.is_paid,
            "generated_at": generated_at,
            "totals": empty,
            "per_screen": [],
            "per_location": [],
            "daily": [],
            "stale_screens": [],
        }

    window = [
        models.PlayLogHourlyRollup.organization_id == scope.organization_id,
        models.PlayLogHourlyRollup.media_id == placement.content_id,
        models.PlayLogHourlyRollup.screen_id.in_(screen_ids),
        models.PlayLogHourlyRollup.date_hour >= placement.starts_at,
        models.PlayLogHourlyRollup.date_hour <= placement.ends_at,
    ]

    totals_row = scope.db.query(
        func.coalesce(func.sum(models.PlayLogHourlyRollup.total_plays), 0),
        func.coalesce(func.sum(models.PlayLogHourlyRollup.completed_plays), 0),
        func.coalesce(func.sum(models.PlayLogHourlyRollup.error_plays), 0),
    ).filter(*window).one()
    total, completed, errors = totals_row
    totals = {
        "total_plays": total,
        "completed_plays": completed,
        "error_plays": errors,
        "success_percent": round(completed / total * 100, 1) if total else 0.0,
    }

    counts = dict(
        scope.db.query(
            models.PlayLogHourlyRollup.screen_id,
            func.coalesce(func.sum(models.PlayLogHourlyRollup.total_plays), 0),
        ).filter(*window).group_by(models.PlayLogHourlyRollup.screen_id).all()
    )
    completions = dict(
        scope.db.query(
            models.PlayLogHourlyRollup.screen_id,
            func.coalesce(func.sum(models.PlayLogHourlyRollup.completed_plays), 0),
        ).filter(*window).group_by(models.PlayLogHourlyRollup.screen_id).all()
    )

    # Every booked screen appears, including ones with no plays — a client is entitled to
    # see that a screen they paid for delivered nothing.
    screens = scope.query(models.Screen).filter(models.Screen.id.in_(screen_ids)).all()
    per_screen = []
    stale = []
    for screen in screens:
        # A screen that has not reported since before the period ended may still be holding
        # play counts locally, so its figure can only rise later.
        #
        # The cutoff needs a grace window, not just "before now": proof-of-play arrives in
        # batches, so a screen reporting normally is always a little behind the clock and
        # would otherwise be flagged on every report.
        cutoff = min(placement.ends_at, generated_at - REPORTING_GRACE)
        is_stale = screen.last_seen is None or screen.last_seen < cutoff
        row = {
            "screen_id": screen.id,
            "screen_name": screen.name or f"Screen {screen.id}",
            "location": screen.location,
            "latitude": screen.latitude,
            "longitude": screen.longitude,
            "online": screen.status == "online",
            "last_seen": screen.last_seen,
            "total_plays": counts.get(screen.id, 0),
            "completed_plays": completions.get(screen.id, 0),
            "counts_may_be_incomplete": is_stale,
        }
        per_screen.append(row)
        if is_stale:
            stale.append(row["screen_name"])
    per_screen.sort(key=lambda r: r["total_plays"], reverse=True)

    places: dict[str, dict] = {}
    for row in per_screen:
        key = row["location"] or "Location not set"
        place = places.setdefault(key, {"location": key, "screens": 0, "total_plays": 0})
        place["screens"] += 1
        place["total_plays"] += row["total_plays"]

    daily_rows = scope.db.query(
        func.date_trunc("day", models.PlayLogHourlyRollup.date_hour).label("day"),
        func.coalesce(func.sum(models.PlayLogHourlyRollup.total_plays), 0).label("plays"),
    ).filter(*window).group_by(text("1")).order_by(text("1")).all()

    return {
        "placement_id": placement.id,
        "advertiser": placement.advertiser,
        "content_name": content.name if content else "Unknown",
        "content_id": placement.content_id,
        "starts_at": placement.starts_at,
        "ends_at": placement.ends_at,
        "price_paise": placement.price_paise,
        "is_paid": placement.is_paid,
        "generated_at": generated_at,
        "totals": totals,
        "per_screen": per_screen,
        "per_location": sorted(places.values(), key=lambda p: p["total_plays"], reverse=True),
        "daily": [{"date": r.day.date().isoformat(), "total_plays": r.plays} for r in daily_rows],
        "stale_screens": stale,
    }


@router.get("/{placement_id}/report")
def get_booking_report(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
):
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    return build_booking_report(scope, placement)


@router.get("/{placement_id}/report.pdf")
def download_booking_report(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
):
    """The client-facing PDF for one booking."""
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    from ..reports.booking_report import build_pdf

    report = build_booking_report(scope, placement)
    pdf = build_pdf(report)
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in placement.advertiser).strip() or "client"
    filename = f"{safe} - playback report.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
