from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

router = APIRouter()


def bump_playlist(playlist: models.Playlist) -> None:
    playlist.updated_at = models.utcnow()


def set_schedule(item: models.PlaylistItem, payload: schemas.ScheduleBase | None) -> None:
    if payload is None:
        item.schedule = None
        return
    schedule = item.schedule or models.Schedule()
    schedule.days_of_week = ",".join(str(day) for day in payload.days_of_week) or None
    schedule.start_time = payload.start_time
    schedule.end_time = payload.end_time
    item.schedule = schedule


@router.post("/", response_model=schemas.PlaylistResponse, status_code=201)
def create_playlist(
    playlist: schemas.PlaylistCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    db_playlist = models.Playlist(
        organization_id=scope.organization_id,
        name=playlist.name.strip(),
        default_transition=playlist.default_transition,
        default_transition_ms=playlist.default_transition_ms,
    )
    scope.db.add(db_playlist)
    scope.db.commit()
    scope.db.refresh(db_playlist)
    return db_playlist


@router.get("/", response_model=list[schemas.PlaylistResponse])
def get_playlists(
    scope: TenantScope = Depends(get_tenant_scope),
):
    return scope.query(models.Playlist).order_by(models.Playlist.updated_at.desc()).all()


@router.get("/{playlist_id}", response_model=schemas.PlaylistResponse)
def get_playlist(
    playlist_id: int,
    scope: TenantScope = Depends(get_tenant_scope),
):
    db_playlist = scope.get(models.Playlist, playlist_id)
    if not db_playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return db_playlist


@router.put("/{playlist_id}", response_model=schemas.PlaylistResponse)
def update_playlist(
    playlist_id: int,
    payload: schemas.PlaylistUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    fields = payload.model_fields_set
    if "name" in fields:
        if payload.name is None:
            raise HTTPException(status_code=422, detail="name cannot be null")
        playlist.name = payload.name.strip()
    if "default_transition" in fields:
        if payload.default_transition is None:
            raise HTTPException(status_code=422, detail="default_transition cannot be null")
        playlist.default_transition = payload.default_transition
    if "default_transition_ms" in fields:
        if payload.default_transition_ms is None:
            raise HTTPException(status_code=422, detail="default_transition_ms cannot be null")
        playlist.default_transition_ms = payload.default_transition_ms
    bump_playlist(playlist)
    scope.db.commit()
    scope.db.refresh(playlist)
    return playlist


@router.post("/{playlist_id}/items", response_model=schemas.PlaylistItemResponse, status_code=201)
def add_item_to_playlist(
    playlist_id: int,
    item: schemas.PlaylistItemCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    db_playlist = scope.get(models.Playlist, playlist_id)
    if not db_playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    content = scope.get(models.Content, item.content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # A video should play for its own length unless the caller says otherwise. The
    # schema default of 10s is only meaningful for images; applying it to video
    # truncates every advert longer than ten seconds.
    duration = item.duration
    if "duration" not in item.model_fields_set and content.duration_ms:
        duration = max(1, round(content.duration_ms / 1000))

    db_item = models.PlaylistItem(
        playlist_id=playlist_id,
        content_id=item.content_id,
        duration=duration,
        order=item.order,
        start_at=item.start_at,
        end_at=item.end_at,
        transition=item.transition,
        transition_ms=item.transition_ms,
    )
    if item.schedule is not None:
        set_schedule(db_item, item.schedule)
    bump_playlist(db_playlist)
    scope.db.add(db_item)
    scope.db.commit()
    scope.db.refresh(db_item)
    return db_item


@router.put("/{playlist_id}/items/reorder")
def reorder_playlist_items(
    playlist_id: int,
    orders: list[int],
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    current_ids = {item.id for item in playlist.items}
    if len(orders) != len(set(orders)) or set(orders) != current_ids:
        raise HTTPException(status_code=422, detail="orders must contain every playlist item exactly once")

    by_id = {item.id: item for item in playlist.items}
    for index, item_id in enumerate(orders):
        by_id[item_id].order = index
    bump_playlist(playlist)
    scope.db.commit()
    return {"status": "ok", "updated_at": playlist.updated_at}


@router.put("/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistItemResponse)
def update_playlist_item(
    playlist_id: int,
    item_id: int,
    payload: schemas.PlaylistItemUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    if not scope.get(models.Playlist, playlist_id):
        raise HTTPException(status_code=404, detail="Item not found")
    item = scope.db.query(models.PlaylistItem).filter(
        models.PlaylistItem.id == item_id,
        models.PlaylistItem.playlist_id == playlist_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    fields = payload.model_fields_set
    if "duration" in fields:
        item.duration = payload.duration
    # A video occupies the screen for exactly as long as the clip runs, so its duration
    # tracks the media rather than whatever a form last posted. Images keep a real choice.
    if item.content and item.content.type == "video" and item.content.duration_ms:
        item.duration = max(1, round(item.content.duration_ms / 1000))
    if "rotation" in fields:
        item.rotation = payload.rotation
    if "start_at" in fields:
        item.start_at = payload.start_at
    if "end_at" in fields:
        item.end_at = payload.end_at
    if item.start_at and item.end_at and item.end_at <= item.start_at:
        raise HTTPException(status_code=422, detail="end_at must be after start_at")
    if "schedule" in fields:
        set_schedule(item, payload.schedule)
    if "transition" in fields:
        item.transition = payload.transition
    if "transition_ms" in fields:
        item.transition_ms = payload.transition_ms

    bump_playlist(item.playlist)
    scope.db.commit()
    scope.db.refresh(item)
    return item


@router.put("/{playlist_id}/transitions", response_model=schemas.PlaylistResponse)
def update_playlist_transitions(
    playlist_id: int,
    payload: schemas.PlaylistTransitionUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    playlist.default_transition = payload.transition
    playlist.default_transition_ms = payload.transition_ms
    if payload.apply_to_all:
        for item in playlist.items:
            item.transition = payload.transition
            item.transition_ms = payload.transition_ms
    bump_playlist(playlist)
    scope.db.commit()
    scope.db.refresh(playlist)
    return playlist


@router.delete("/{playlist_id}/items/{item_id}")
def remove_item_from_playlist(
    playlist_id: int,
    item_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    if not scope.get(models.Playlist, playlist_id):
        raise HTTPException(status_code=404, detail="Item not found")
    item = scope.db.query(models.PlaylistItem).filter(
        models.PlaylistItem.id == item_id,
        models.PlaylistItem.playlist_id == playlist_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    playlist = item.playlist
    scope.db.delete(item)
    bump_playlist(playlist)
    scope.db.commit()
    return {"status": "ok"}


@router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    now = models.utcnow()
    for screen in playlist.screens:
        screen.playlist_id = None
        screen.assignment_updated_at = now
    for group in playlist.groups:
        group.playlist_id = None
        group.updated_at = now
        for screen in group.screens:
            screen.assignment_updated_at = now
    scope.db.delete(playlist)
    scope.db.commit()
    return {"status": "ok"}
