"""Playlist Router - Clean Presentation Layer for Playlist Management."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends

from .. import schemas
from ..tenancy import TenantScope, get_tenant_scope, require_tenant_roles
from ..repositories.playlist_repo import PLAYLIST_LOAD
from ..services.playlist_service import PlaylistService, bump_playlist, set_schedule

router = APIRouter()

# Re-exported for backward compatibility with existing tests/modules
__all__ = ["router", "PLAYLIST_LOAD", "bump_playlist", "set_schedule"]


def _service(scope: TenantScope) -> PlaylistService:
    """Dependency helper to get PlaylistService instance."""
    return PlaylistService(scope.db)


@router.post("/", response_model=schemas.PlaylistResponse, status_code=201)
def create_playlist(
    playlist: schemas.PlaylistCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).create_playlist(playlist, scope)


@router.get("/", response_model=List[schemas.PlaylistResponse])
def get_playlists(
    scope: TenantScope = Depends(get_tenant_scope),
):
    return _service(scope).list_playlists(scope)


@router.get("/{playlist_id}", response_model=schemas.PlaylistResponse)
def get_playlist(
    playlist_id: int,
    scope: TenantScope = Depends(get_tenant_scope),
):
    return _service(scope).get_playlist(playlist_id, scope)


@router.put("/{playlist_id}", response_model=schemas.PlaylistResponse)
def update_playlist(
    playlist_id: int,
    payload: schemas.PlaylistUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).update_playlist(playlist_id, payload, scope)


@router.post("/{playlist_id}/items", response_model=schemas.PlaylistItemResponse, status_code=201)
def add_item_to_playlist(
    playlist_id: int,
    item: schemas.PlaylistItemCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).add_item_to_playlist(playlist_id, item, scope)


@router.put("/{playlist_id}/items/reorder")
def reorder_playlist_items(
    playlist_id: int,
    orders: List[int],
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).reorder_playlist_items(playlist_id, orders, scope)


@router.put("/{playlist_id}/items/{item_id}", response_model=schemas.PlaylistItemResponse)
def update_playlist_item(
    playlist_id: int,
    item_id: int,
    payload: schemas.PlaylistItemUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).update_playlist_item(playlist_id, item_id, payload, scope)


@router.put("/{playlist_id}/transitions", response_model=schemas.PlaylistResponse)
def update_playlist_transitions(
    playlist_id: int,
    payload: schemas.PlaylistTransitionUpdate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).update_playlist_transitions(playlist_id, payload, scope)


@router.delete("/{playlist_id}/items/{item_id}")
def remove_item_from_playlist(
    playlist_id: int,
    item_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).remove_item_from_playlist(playlist_id, item_id, scope)


@router.delete("/{playlist_id}")
def delete_playlist(
    playlist_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    return _service(scope).delete_playlist(playlist_id, scope)
