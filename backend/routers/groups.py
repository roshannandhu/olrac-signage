from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from .. import models, schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles

router = APIRouter()


def serialize_group(group: models.ScreenGroup) -> schemas.ScreenGroupResponse:
    return schemas.ScreenGroupResponse(
        id=group.id,
        name=group.name,
        parent_id=group.parent_id,
        is_dynamic=group.is_dynamic,
        dynamic_criteria=group.dynamic_criteria,
        playlist_id=group.playlist_id,
        created_at=group.created_at,
        updated_at=group.updated_at,
        screen_count=len(group.screens),
    )


# Matches MAX_GROUP_DEPTH in routers/screens.py, which walks the same chain at sync time.
MAX_GROUP_DEPTH = 32


def validate_parent(scope: TenantScope, parent_id: int | None, group_id: int | None) -> None:
    """Reject a parent that is not ours, is the group itself, or would close a loop.

    `parent_id` was previously assigned straight from the request body with no checks at
    all. Two things went wrong with that. A tenant could name another organisation's group
    as their parent, because nothing confirmed the id was in scope. And nothing stopped
    A -> B -> A, which is worse than it sounds: resolve_screen_playlist and the emergency
    broadcast lookup both walk `group.parent` in a `while` loop on the sync path, so one
    cycle would hang a request thread and hold its database connection open, for every
    screen in that group, forever.
    """
    if parent_id is None:
        return
    if group_id is not None and parent_id == group_id:
        raise HTTPException(status_code=400, detail="A group cannot be its own parent")

    parent = scope.get(models.ScreenGroup, parent_id)
    if not parent:
        # Same 404 wording as a missing group, so this cannot be used to probe which group
        # ids exist in other organisations.
        raise HTTPException(status_code=404, detail="Parent group not found")

    if group_id is None:
        return

    # Walk up from the proposed parent: meeting ourselves means this edge closes a loop.
    seen = {group_id}
    current = parent
    for _ in range(MAX_GROUP_DEPTH):
        if current is None:
            return
        if current.id in seen:
            raise HTTPException(status_code=400, detail="That parent would create a loop in the group tree")
        seen.add(current.id)
        current = current.parent
    raise HTTPException(status_code=400, detail="Group hierarchy is too deep")


@router.get("/", response_model=list[schemas.ScreenGroupResponse])
def list_groups(
    scope: TenantScope = Depends(get_tenant_scope),
):
    groups = scope.query(models.ScreenGroup).order_by(models.ScreenGroup.name).all()
    return [serialize_group(group) for group in groups]


@router.post("/", response_model=schemas.ScreenGroupResponse, status_code=201)
def create_group(
    payload: schemas.ScreenGroupCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    name = payload.name.strip()
    if scope.query(models.ScreenGroup).filter(models.ScreenGroup.name == name).first():
        raise HTTPException(status_code=409, detail="Group name already exists")
    validate_parent(scope, payload.parent_id, group_id=None)
    group = models.ScreenGroup(
        name=name, 
        organization_id=scope.organization_id,
        parent_id=payload.parent_id,
        is_dynamic=payload.is_dynamic,
        dynamic_criteria=payload.dynamic_criteria
    )
    scope.db.add(group)
    scope.db.commit()
    scope.db.refresh(group)
    return serialize_group(group)


@router.put("/{group_id}", response_model=schemas.ScreenGroupResponse)
def update_group(
    group_id: int,
    payload: schemas.ScreenGroupUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    group = scope.get(models.ScreenGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    validate_parent(scope, payload.parent_id, group_id=group.id)
    group.name = payload.name.strip()
    group.parent_id = payload.parent_id
    group.is_dynamic = payload.is_dynamic
    group.dynamic_criteria = payload.dynamic_criteria
    group.updated_at = models.utcnow()
    scope.db.commit()
    scope.db.refresh(group)
    return serialize_group(group)


@router.put("/{group_id}/screens", response_model=schemas.ScreenGroupResponse)
def set_group_screens(
    group_id: int,
    payload: schemas.ScreenGroupMembersUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    group = scope.get(models.ScreenGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    requested_ids = set(payload.screen_ids)
    screens = scope.query(models.Screen).filter(models.Screen.id.in_(requested_ids)).all() if requested_ids else []
    if len(screens) != len(requested_ids):
        raise HTTPException(status_code=404, detail="One or more screens were not found")

    now = models.utcnow()
    for current in list(group.screens):
        if current.id not in requested_ids:
            current.group_id = None
            current.assignment_updated_at = now
    for screen in screens:
        screen.group_id = group.id
        screen.assignment_updated_at = now
    group.updated_at = now
    scope.db.commit()
    scope.db.refresh(group)
    return serialize_group(group)


@router.post("/{group_id}/assign/{playlist_id}", response_model=schemas.ScreenGroupResponse)
async def assign_group_playlist(
    group_id: int,
    playlist_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    group = scope.get(models.ScreenGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    playlist = scope.get(models.Playlist, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    now = models.utcnow()
    group.playlist_id = playlist.id
    group.updated_at = now
    playlist.updated_at = now
    for screen in group.screens:
        screen.assignment_updated_at = now
    scope.db.commit()
    scope.db.refresh(group)
    
    import json
    from .. import database
    try:
        redis = database.get_redis()
        await redis.publish(f"group:{group.id}", json.dumps({"type": "playlist_changed"}))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish to redis: {e}")
    
    return serialize_group(group)


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    group = scope.get(models.ScreenGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    now = models.utcnow()
    for screen in group.screens:
        screen.group_id = None
        screen.assignment_updated_at = now
    scope.db.delete(group)
    scope.db.commit()
    return {"status": "ok"}
