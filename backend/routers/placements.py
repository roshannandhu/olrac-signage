"""Selling an advert: which client, for how long, in which places.

The placement is a record of the deal. The thing that actually plays is still an ordinary
playlist item, created and removed by this module on the placement's behalf. Everything
downstream — the player sync, proof-of-play, rendition selection, rotation — keeps reading
playlist items and needs no knowledge that bookings exist.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, text

from .. import models, schemas
from ..tenancy import TenantScope, require_tenant_roles
from ..media_urls import resolve_media_url
from .playlists import bump_playlist

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

        # The screen has no playlist of its OWN, but it may still be playing one it
        # inherits from a group. Two things must not happen here, and both used to:
        #
        #   - writing the advert into the inherited playlist would put it on every other
        #     screen in that group, which is not what was sold. The booking would report
        #     one location while ten TVs ran it.
        #   - giving the screen a fresh empty playlist, as this did, silently takes the
        #     group's loop away from it -- the screen goes from playing the venue's
        #     content to playing one advert and nothing else.
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
                scope.db.add(models.PlaylistItem(
                    playlist_id=playlist.id,
                    content_id=source.content_id,
                    duration=source.duration,
                    order=source.order,
                    start_at=source.start_at,
                    end_at=source.end_at,
                    transition=source.transition,
                    transition_ms=source.transition_ms,
                    rotation=source.rotation,
                ))
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


def _place(
    scope: TenantScope,
    placement: models.AdPlacement,
    ref: schemas.PlacementTargetRef,
    assigned_at=None,
) -> models.AdPlacementTarget:
    """Put the booked advert into one place and remember the item we created.

    `assigned_at` is when this place actually starts carrying the advert, and it is passed
    in rather than defaulted to the clock because the three callers mean different things:

    * creating a booking -- the booking's own start, even when it is backdated. Every place
      named in that request was sold as part of it.
    * adding a place later -- now. That screen genuinely has fewer days on air.
    * splitting a group -- the ORIGINAL target's date, because nothing about what the
      client bought changed; only how it is recorded did.

    Defaulting all three to now looked right and quietly reported a backdated booking's
    screens as one day old, dividing a fortnight of plays by a single day.
    """
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

    # This location's own run length, when one was sold. `days` is what the operator types
    # -- "30 in the mall, 10 in the shop, 50 at the airport" -- and it is resolved to a
    # date here so everything downstream compares dates and never has to know which of the
    # two the sale was expressed in.
    target_starts_at = max(placement.starts_at, assigned_at or models.utcnow())
    target_ends_at = None
    if getattr(ref, "days", None):
        target_ends_at = target_starts_at + timedelta(days=ref.days)

    item = models.PlaylistItem(
        playlist_id=playlist.id,
        content_id=placement.content_id,
        duration=duration,
        order=next_order,
        # The paid window is enforced by the same start/end the player already honours.
        # max(): a screen added mid-campaign must not be told to have started on a date in
        # the past, and a backdated booking must not start a screen before it was sold.
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
        # Left NULL when the location runs for the booking's own window, so the common
        # case stores nothing and keeps inheriting.
        starts_at=target_starts_at if target_ends_at else None,
        ends_at=target_ends_at,
    )
    scope.db.add(target)
    scope.db.flush()
    # The player's sync is CONDITIONAL: sync_tv compares its `since` against a marker
    # built from screen.assignment_updated_at, playlist.updated_at and group.updated_at,
    # and answers 204 when nothing is newer. Adding a row to playlist_items moves none of
    # those on its own, so a booked advert was written to the database, shown correctly on
    # every dashboard, and never sent to a screen that already had its playlist -- the TV
    # kept getting 204 and kept playing the old loop. Bookings are not a second scheduler;
    # they edit the playlist, so they have to mark it edited like every other edit does.
    bump_playlist(playlist)
    return target


def _unplace(scope: TenantScope, target: models.AdPlacementTarget) -> None:
    """Remove the advert from this one place, leaving every other place untouched."""
    if target.playlist_item_id:
        item = scope.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.id == target.playlist_item_id
        ).first()
        if item:
            # Before the delete, while the item can still name its playlist. Same reason as
            # _place: without this the screen is never told, and an advert whose booking was
            # cancelled or moved keeps playing -- which bills the wrong advertiser.
            if item.playlist:
                bump_playlist(item.playlist)
            scope.db.delete(item)
    scope.db.delete(target)


def effective_ends_at(placement: models.AdPlacement) -> "datetime":
    """When the run actually finishes, extensions counted.

    starts_at/ends_at stay as SOLD -- they are the original deal and an invoice should
    still be able to show it. Everything that asks "is this still running" wants this
    instead, so it lives in one place rather than being re-derived at each call site.
    """
    # Delegates to the model property so the report and the "ending soon" alert cannot
    # drift apart on what the end date is.
    return placement.effective_ends_at


def total_price_paise(placement: models.AdPlacement) -> int:
    """The booking plus every extension sold against it."""
    return placement.price_paise + sum(e.additional_price_paise for e in placement.extensions)


def resolve_client(scope: TenantScope, client_id: int | None) -> models.Client | None:
    """Look a client up inside the tenant, 404 if it is not theirs.

    Via scope.get rather than a bare query so naming another tenant's client id is a 404
    and not a booking silently attributed to a stranger's customer.
    """
    if client_id is None:
        return None
    client = scope.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def resolve_tenant_plan(scope: TenantScope, plan_id: int | None) -> models.TenantPlan | None:
    if plan_id is None:
        return None
    plan = scope.get(models.TenantPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def sync_placement_window(scope: TenantScope, placement: models.AdPlacement) -> None:
    """Push each location's run window onto the playlist item it placed.

    The player enforces the paid window through PlaylistItem.start_at/end_at, so an
    extension that only wrote a row here would be invisible on every screen: the advert
    would stop on the original date the client no longer holds.

    Per TARGET, not per booking. Two reasons:

      - A location may be sold its own length -- 30 days in a mall, 10 in a shop, 50 at an
        airport, one client, one booking. AdPlacementTarget.effective_ends_at falls back to
        the booking's, so a target with no window of its own is unaffected.

      - This used to assign `placement.starts_at` to every item, which silently undid the
        per-target start _place computes with max(placement.starts_at, assigned_at). A
        screen added on day 10 of a campaign had its start reset to day 1 the next time
        anything re-synced the window -- an extension, a date edit -- and then billed from
        a date it was not yet running.

    Bumps each affected playlist for the same reason _place does -- sync_tv answers 204
    until playlist.updated_at moves, so without it the screens keep the old window until
    something unrelated happens to touch the playlist.
    """
    playlists = set()
    for target in placement.targets:
        if not target.playlist_item_id:
            continue
        item = scope.db.query(models.PlaylistItem).filter(
            models.PlaylistItem.id == target.playlist_item_id
        ).first()
        if not item:
            continue
        item.start_at = target.effective_starts_at
        item.end_at = target.effective_ends_at
        if item.playlist:
            playlists.add(item.playlist)
    for playlist in playlists:
        bump_playlist(playlist)


def _serialize(scope: TenantScope, placement: models.AdPlacement) -> schemas.PlacementResponse:
    screen_names = dict(scope.db.query(models.Screen.id, models.Screen.name).all())
    group_names = dict(scope.db.query(models.ScreenGroup.id, models.ScreenGroup.name).all())
    now = models.utcnow()
    ends = effective_ends_at(placement)
    days_left = max(0, (ends - now).days) if ends > now else 0
    content = placement.content or scope.get(models.Content, placement.content_id)
    creative_name = content.name if content else None
    creative_thumb = resolve_media_url(content.thumbnail or content.file_url) if content else None
    # Groups expanded, the same way the cap counts them, so "3 of 5" means three TVs and
    # not three rows.
    usage = plan_screen_usage(placement.plan, set(_booking_screen_ids(scope, placement)))

    return schemas.PlacementResponse(
        id=placement.id,
        content_id=placement.content_id,
        creative_name=creative_name,
        creative_thumbnail_url=creative_thumb,
        advertiser=placement.advertiser,
        client=schemas.ClientResponse.model_validate(placement.client) if placement.client else None,
        plan=schemas.TenantPlanResponse.model_validate(placement.plan) if placement.plan else None,
        extensions=[schemas.ExtensionResponse.model_validate(e) for e in placement.extensions],
        effective_ends_at=ends,
        days_remaining=days_left,
        total_price_paise=total_price_paise(placement),
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
                starts_at=t.starts_at,
                ends_at=t.ends_at,
                # Reported as days too, because that is the unit the deal was struck in
                # and the dashboard should not have to subtract two dates to show it back.
                days=(
                    max(1, round((t.ends_at - t.starts_at).total_seconds() / 86400))
                    if t.ends_at and t.starts_at
                    else None
                ),
            )
            for t in placement.targets
        ],
        screens_used=usage["used"],
        plan_max_locations=usage["allowed"],
        screens_unused=usage["unused"],
        payment=(
            schemas.PaymentResponse(
                id=placement.payment.id,
                amount_paise=placement.payment.amount_paise,
                method=placement.payment.method,
                reference=placement.payment.reference,
                paid_at=placement.payment.paid_at,
                notes=placement.payment.notes,
                # The name, not the id: this is read by a human chasing a receipt.
                recorded_by=(
                    placement.payment.recorded_by.username
                    if placement.payment.recorded_by else None
                ),
                created_at=placement.payment.created_at,
            )
            if placement.payment else None
        ),
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


def ensure_ad_slot_quota(scope: TenantScope) -> None:
    """Reject the caller when the organisation is already at its ad-slot limit.

    Two tiers, in the same order and with the same "0 means unlimited" rule that
    screens.ensure_screen_quota uses for screens:

    1. The per-org limit a platform administrator set (Organization.max_ad_slots).
    2. The package the org is on (Plan.max_ad_slots), as the fallback.

    Only tier 1 existed, so a tenant on a package with an ad limit and no hand-set override
    was silently unlimited -- and every organisation defaults to max_ad_slots=0.

    "Active" means anything not yet finished, including a booking that has not started, so
    a future campaign holds its slot rather than being sellable twice.
    """
    org = scope.db.query(models.Organization).filter(
        models.Organization.id == scope.organization_id
    ).first()
    if not org:
        return

    # Same derivation as screens, via the shared property: override when set, otherwise
    # the package. This was the correct fallback written out inline here while
    # ensure_screen_quota had a subtly different one that returned early on a 0 override --
    # two copies of one rule that disagreed.
    limit = org.effective_max_ad_slots
    if limit is None:
        return

    # On the EFFECTIVE end. Counting the sold `ends_at` freed the slot of any campaign kept
    # running by an extension or a longer per-location window, so a tenant at their limit
    # could sell past it simply by having extended something.
    active_ads = scope.db.query(models.AdPlacement).filter(
        models.AdPlacement.organization_id == scope.organization_id,
        models.AdPlacement.effective_ends_at >= models.utcnow(),
    ).count()
    if active_ads >= limit:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Ad slot quota reached ({active_ads}/{limit}). "
                f"Contact your platform administrator to increase your ad limit."
            ),
        )


@router.post("/", response_model=schemas.PlacementResponse, status_code=201)
def create_placement(
    payload: schemas.PlacementCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    if not scope.get(models.Content, payload.content_id):
        raise HTTPException(status_code=404, detail="Content not found")

    ensure_ad_slot_quota(scope)

    client = resolve_client(scope, payload.client_id)
    plan = resolve_tenant_plan(scope, payload.plan_id)

    # The client record is the name of record; `advertiser` follows it. A booking may still
    # be made on a bare name -- schemas.PlacementCreate requires one or the other.
    advertiser = client.name if client else (payload.advertiser or "").strip()

    # A plan fills in what the caller left at its default. COPIED, never read through: the
    # tenant reprices plans as their business changes and a sold campaign must keep the
    # terms it was sold on. See routers/tenant_plans.
    price_paise = payload.price_paise
    ends_at = payload.ends_at
    if plan:
        if not price_paise:
            price_paise = plan.price_paise
        if ends_at is None:
            ends_at = payload.starts_at + timedelta(days=plan.duration_days)

    placement = models.AdPlacement(
        organization_id=scope.organization_id,
        content_id=payload.content_id,
        advertiser=advertiser,
        client_id=client.id if client else None,
        plan_id=plan.id if plan else None,
        price_paise=price_paise,
        is_paid=payload.is_paid,
        starts_at=payload.starts_at,
        ends_at=ends_at,
        notes=payload.notes,
    )
    scope.db.add(placement)
    scope.db.flush()

    # Checked before the first item is placed, so a booking that breaches its plan is
    # refused whole rather than half-created.
    ensure_plan_locations(scope, plan, set(), _screens_for_refs(scope, payload.targets))

    for ref in payload.targets:
        _place(scope, placement, ref, assigned_at=payload.starts_at)

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
    # `is_paid` is deliberately not in this list any more. It is now the shadow of the
    # payment record, set only by POST/DELETE /payment, so the flag and the receipt cannot
    # tell different stories -- which they could when a blind PUT alongside a date edit
    # could mark a campaign paid with no amount, method or date behind it.
    for field in ("advertiser", "price_paise", "notes", "starts_at", "ends_at"):
        if field in fields:
            setattr(placement, field, getattr(payload, field))

    if "client_id" in fields:
        client = resolve_client(scope, payload.client_id)
        placement.client_id = client.id if client else None
        # The label follows the record, so a report never prints a name the booking is no
        # longer attributed to.
        if client:
            placement.advertiser = client.name
    if "plan_id" in fields:
        plan = resolve_tenant_plan(scope, payload.plan_id)
        # Against the screens the booking ALREADY reaches. Moving a six-screen booking onto
        # a five-screen plan is the same breach as adding a sixth screen to that plan, and
        # this path let it through -- the plan was enforced when screens changed but not
        # when the plan did.
        ensure_plan_locations(scope, plan, set(_booking_screen_ids(scope, placement)), set())
        placement.plan_id = plan.id if plan else None

    if placement.ends_at <= placement.starts_at:
        raise HTTPException(status_code=422, detail="The end date must be after the start date")

    # Every placed item carries the booking's window, so moving the dates moves them all --
    # and the screens have to be told, which the previous version of this did not do. It
    # rewrote item.start_at/end_at and stopped, leaving playlist.updated_at untouched, so
    # sync_tv answered 204 and every screen kept running the OLD window. A booking moved
    # earlier kept playing past the date it was moved to.
    if fields & {"starts_at", "ends_at"}:
        sync_placement_window(scope, placement)

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

    # The plan's screen count binds here too, not only at creation -- adding places one at
    # a time was otherwise the way straight past it.
    ensure_plan_locations(
        scope, placement.plan,
        set(_booking_screen_ids(scope, placement)),
        _screens_for_refs(scope, [ref]),
    )

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

    # No ensure_plan_locations here, deliberately. A group target already counts as every
    # member, and `keep` is a subset of those, so a split can only hold the screen count
    # level or lower it. Checking would be dead code at best -- and at worst it would refuse
    # a split on a booking that is already over its plan, which is the very edit that fixes
    # the breach.

    # Read before _unplace deletes the row it lives on. Splitting changes only how the
    # booking is recorded, not what the client bought, so each surviving screen keeps the
    # date the GROUP was assigned -- taking `now` here would silently reset a fortnight of
    # airtime to today on every screen in the group.
    group_assigned_at = target.assigned_at

    _unplace(scope, target)
    for screen in keep:
        _place(scope, placement, schemas.PlacementTargetRef(screen_id=screen.id),
               assigned_at=group_assigned_at)

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


@router.post("/{placement_id}/extensions", response_model=schemas.PlacementResponse, status_code=201)
def add_extension(
    placement_id: int,
    payload: schemas.ExtensionCreate,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Sell more time on a booking that is already running.

    A row per extension, not an `extended_to` column: a campaign that performs is extended
    more than once and each sale has to survive on the invoice.
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Defaults to continuing from wherever the run currently finishes, so back-to-back
    # extensions cannot leave an unpaid gap the advert would go dark in.
    starts = payload.extended_from or effective_ends_at(placement)
    if payload.extended_to <= starts:
        raise HTTPException(
            status_code=422,
            detail="The extension must end after it begins",
        )

    extension = models.AdPlacementExtension(
        placement_id=placement.id,
        extended_from=starts,
        extended_to=payload.extended_to,
        additional_price_paise=payload.additional_price_paise,
        is_paid=payload.is_paid,
        notes=payload.notes,
    )
    scope.db.add(extension)
    scope.db.flush()
    scope.db.refresh(placement)

    # Without this the extension is a database row and nothing else: the player stops the
    # advert on PlaylistItem.end_at, which is still the original date.
    sync_placement_window(scope, placement)

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.delete("/{placement_id}/extensions/{extension_id}", response_model=schemas.PlacementResponse)
def remove_extension(
    placement_id: int,
    extension_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    extension = scope.db.query(models.AdPlacementExtension).filter(
        models.AdPlacementExtension.id == extension_id,
        # Scoped through the placement, which scope.get already proved is this tenant's.
        # Querying the extension by id alone would let one tenant delete another's.
        models.AdPlacementExtension.placement_id == placement.id,
    ).first()
    if not extension:
        raise HTTPException(status_code=404, detail="Extension not found")

    scope.db.delete(extension)
    scope.db.flush()
    scope.db.refresh(placement)
    # Pulls the run back in: an extension that was cancelled must stop playing.
    sync_placement_window(scope, placement)

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.get("/{placement_id}/plan-options", response_model=list[schemas.PlanOption])
def plan_options(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
):
    """Every plan this booking could move to, with one marked as the one to pick.

    The recommendation is answered from what the client is ACTUALLY using -- the cheapest
    active plan that covers the screens already assigned. A client on Basic running five
    screens is told to move up because five screens is what they are being given, not
    because a heuristic guessed at their appetite.
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    used = len(_booking_screen_ids(scope, placement))
    current = placement.plan
    current_price = current.price_paise if current else 0
    plans = scope.query(models.TenantPlan).filter(
        models.TenantPlan.is_active.is_(True)
    ).order_by(models.TenantPlan.price_paise).all()

    options = [
        schemas.PlanOption(
            plan=schemas.TenantPlanResponse.model_validate(plan),
            is_current=bool(current and plan.id == current.id),
            # max_locations of 0 means uncapped, so it fits anything.
            fits=plan.max_locations <= 0 or plan.max_locations >= used,
            price_difference_paise=max(0, plan.price_paise - current_price),
            extra_days=plan.duration_days,
        )
        for plan in plans
    ]

    # Cheapest that fits and is not the one they are already on. `plans` is already ordered
    # by price, so the first match is the cheapest. Nothing is recommended when the current
    # plan is the only one that fits -- an upgrade prompt with nowhere better to go is
    # noise, and recommending a costlier plan for no reason is worse than that.
    upgrade = next((o for o in options if o.fits and not o.is_current), None)
    if upgrade is not None:
        upgrade.recommended = True
    return options


@router.post("/{placement_id}/upgrade", response_model=schemas.PlacementResponse)
def upgrade_plan(
    placement_id: int,
    payload: schemas.PlanUpgrade,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Move a booking onto a different plan and bill the difference.

    One booking throughout, deliberately. Closing the old sale and opening a new one would
    split a single client's campaign across two records, two reports and two invoices, and
    the proof-of-play a client receives should cover the campaign they think they bought.
    The price difference becomes an extension, which is the shape the codebase already has
    for "more time was sold against this booking".
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    plan = resolve_tenant_plan(scope, payload.plan_id)
    if plan is None:
        raise HTTPException(status_code=422, detail="An upgrade needs a plan to move to")

    # An upgrade must never leave the booking delivering more screens than the plan it is
    # now billed on -- that is the same breach as adding a screen, arrived at sideways.
    ensure_plan_locations(scope, plan, set(_booking_screen_ids(scope, placement)), set())

    difference = payload.price_difference_paise
    if difference is None:
        difference = max(0, plan.price_paise - (placement.plan.price_paise if placement.plan else 0))

    placement.plan_id = plan.id

    if payload.extend:
        # From the current effective end, not from today: back-to-back, so the advert never
        # goes dark between the old plan finishing and the new one starting.
        starts = effective_ends_at(placement)
        scope.db.add(models.AdPlacementExtension(
            placement_id=placement.id,
            extended_from=starts,
            extended_to=starts + timedelta(days=plan.duration_days),
            additional_price_paise=difference,
            is_paid=False,
            notes=f"Upgraded to {plan.name}",
        ))
        scope.db.flush()
        scope.db.refresh(placement)
        # Without this the extension is a row and nothing else -- every placed item still
        # carries the old end date and the player stops the advert on it.
        sync_placement_window(scope, placement)

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.post("/{placement_id}/payment", response_model=schemas.PlacementResponse, status_code=201)
def record_payment(
    placement_id: int,
    payload: schemas.PaymentWrite,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Record what the client paid and how. The only way a booking becomes paid.

    Replaces the existing record rather than adding to it -- one settlement per booking is
    the modelled shape, so re-recording is how a wrong amount or method gets corrected.
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    payment = placement.payment
    if payment is None:
        payment = models.AdPayment(
            organization_id=scope.organization_id,
            placement_id=placement.id,
        )
        scope.db.add(payment)

    payment.amount_paise = payload.amount_paise
    payment.method = payload.method
    payment.reference = (payload.reference or "").strip() or None
    payment.paid_at = payload.paid_at or models.utcnow()
    payment.notes = (payload.notes or "").strip() or None
    # Who took the money. Kept even if they later leave -- the FK is SET NULL, not CASCADE.
    payment.recorded_by_user_id = scope.user.id
    placement.is_paid = True

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


@router.delete("/{placement_id}/payment", response_model=schemas.PlacementResponse)
def clear_payment(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Undo a payment recorded in error. The booking goes back to unpaid."""
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")
    if placement.payment is not None:
        scope.db.delete(placement.payment)
    # Set regardless: a booking marked paid before payments were recorded has no row to
    # delete, and leaving the flag true would make it unclearable.
    placement.is_paid = False

    scope.db.commit()
    scope.db.refresh(placement)
    return _serialize(scope, placement)


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


def _commercials(placement: models.AdPlacement, generated_at: "datetime") -> dict:
    """The client, plan, period and money blocks a client report is built around.

    Shared by both exits of build_booking_report so the "no screens booked" report carries
    the same header as a full one -- a client whose screens were all removed still gets a
    document that names them and what they paid.
    """
    ends = effective_ends_at(placement)
    starts = placement.starts_at

    # Whole days, and never negative: a report pulled on the last afternoon should read
    # "0 days remaining", not "-1".
    day = 86400
    days_total = max(1, round((ends - starts).total_seconds() / day))
    days_remaining = max(0, round((ends - generated_at).total_seconds() / day))
    # Elapsed drives the per-day averages. Clamped to at least 1 so a report pulled on the
    # first day divides by one day rather than by zero, and never exceeds the period so a
    # report pulled after the end does not keep diluting the average.
    days_elapsed = min(days_total, max(1, round((min(generated_at, ends) - starts).total_seconds() / day)))

    client = placement.client
    plan = placement.plan
    organization = placement.organization
    # Whose report this is FROM. The header band and the footer both carry it, so a client
    # receiving the PDF can tell who sent it without opening the covering email.
    return {
        "organization": {
            # brand_name is what the tenant wants a CLIENT to see; `name` is the workspace
            # name they typed at signup, which is often "<person>'s Workspace".
            "name": ((organization.brand_name or organization.name) if organization else "Signage network"),
            "logo": resolve_media_url(organization.logo_url) if organization and organization.logo_url else None,
            "brand_color": organization.brand_color if organization else None,
            "email": getattr(organization, "owner_email", None) if organization else None,
        },
        "client": {
            "name": client.name if client else placement.advertiser,
            "client_code": client.client_code if client else None,
            "email": client.email if client else None,
            "phone": client.phone if client else None,
        },
        "plan": {
            "name": plan.name,
            "description": plan.description,
            "duration_days": plan.duration_days,
            "max_locations": plan.max_locations,
            "ad_slots": plan.ad_slots,
            "support_tier": plan.support_tier,
            "price_paise": plan.price_paise,
        } if plan else None,
        "extensions": [
            {
                "id": e.id,
                "extended_from": e.extended_from,
                "extended_to": e.extended_to,
                "additional_price_paise": e.additional_price_paise,
                "is_paid": e.is_paid,
            }
            for e in placement.extensions
        ],
        "effective_ends_at": ends,
        "days_total": days_total,
        "days_remaining": days_remaining,
        "days_elapsed": days_elapsed,
        "extension_price_paise": sum(e.additional_price_paise for e in placement.extensions),
        "total_price_paise": total_price_paise(placement),
        # For the invoice: its reference number is derived from these two ids, and the
        # payment block is what turns "unpaid" into "unpaid, and here is what we chased".
        # Both live here rather than at each exit so the two report shapes cannot diverge.
        "organization_id": placement.organization_id,
        "payment": {
            "amount_paise": placement.payment.amount_paise,
            "method": placement.payment.method,
            "reference": placement.payment.reference,
            "paid_at": placement.payment.paid_at,
        } if placement.payment else None,
    }


def _screens_for_refs(scope: TenantScope, refs) -> set[int]:
    """Every screen a set of target refs actually reaches, groups expanded."""
    screen_ids: set[int] = set()
    group_ids = [ref.group_id for ref in refs if getattr(ref, "group_id", None)]
    screen_ids.update(ref.screen_id for ref in refs if getattr(ref, "screen_id", None))
    if group_ids:
        members = scope.query(models.Screen).filter(models.Screen.group_id.in_(group_ids)).all()
        screen_ids.update(member.id for member in members)
    return screen_ids


def plan_screen_usage(plan, screen_ids: set[int]) -> dict:
    """How much of a plan's screen allowance a set of screens uses. Measures; never raises.

    Separate from the check below because the two halves are not symmetrical. Going OVER a
    plan is a refusal -- the tenant is about to deliver something they did not sell. Going
    UNDER is not: a plan bought for five screens and running on three is a booking the
    client has paid for and is not receiving, which is worth saying loudly and is never
    worth blocking a sale over. Raising on it would make "sell now, pick the screens on
    Monday" impossible.

    `allowed` of 0 means the plan does not cap locations (or there is no plan), so nothing
    is over or unused.
    """
    allowed = plan.max_locations if plan and plan.max_locations > 0 else 0
    used = len(screen_ids)
    return {
        "used": used,
        "allowed": allowed,
        "over": max(0, used - allowed) if allowed else 0,
        "unused": max(0, allowed - used) if allowed else 0,
    }


def ensure_plan_locations(scope: TenantScope, plan, existing: set[int], adding: set[int]) -> None:
    """A plan sells a number of TVs, so it has to actually cap them.

    Counted on EXPANDED screens, not on target rows: a single group target can carry ten
    screens, so counting targets would wave a ten-screen group straight past a five-TV
    plan -- the limit would read as enforced and mean nothing.

    Distinct from ensure_ad_slot_quota above, which is the limit OLRAC places on the
    TENANT. This is the limit the tenant placed on their own client, so the message has to
    make clear which of the two was hit.

    Every path that can change which screens a booking reaches has to come through here.
    Three of them did not: a plan swap on PUT, a group split, and the client-ad editor in
    routers/content.py, each of which could leave a booking delivering more screens than
    the plan it is billed on.
    """
    total = existing | adding
    usage = plan_screen_usage(plan, total)
    if usage["over"]:
        raise HTTPException(
            status_code=409,
            detail=(
                f"The {plan.name} plan covers {plan.max_locations} screen"
                f"{'' if plan.max_locations == 1 else 's'}, and this would make {len(total)}. "
                "Move the booking to a larger plan, or remove a screen."
            ),
        )


def build_booking_report(scope: TenantScope, placement: models.AdPlacement) -> dict:
    """Proof of delivery for one booking: only its window, only its screens.

    Scoping is the whole point. The per-advert report elsewhere totals every play of that
    creative for all time; handing that to a client would bill them for another client's
    booking of the same file, or for plays from before they paid.
    """
    content = scope.get(models.Content, placement.content_id)
    screen_ids = _booking_screen_ids(scope, placement)
    generated_at = models.utcnow()

    # Resolved, not raw: the column holds "s3://<key>" or "/uploads/<path>".
    # Fall back to file_url if thumbnail is unset so images always render.
    raw_thumb = (content.thumbnail or content.file_url) if content else None
    content_thumbnail = resolve_media_url(raw_thumb) if raw_thumb else None

    import hashlib
    verify_payload = f"{placement.id}:{placement.organization_id}:{placement.advertiser}:{placement.starts_at.isoformat()}"
    token_hash = hashlib.sha256(verify_payload.encode()).hexdigest()[:8].upper()
    certificate_id = f"POP-{placement.id:04d}-{token_hash}"
    verification_url = f"https://olrac-signage.abhinavsanthosh221.workers.dev/verify/pop?cert={certificate_id}&id={placement.id}"

    empty = {"total_plays": 0, "completed_plays": 0, "error_plays": 0, "success_percent": 0.0}
    if not screen_ids:
        return {
            "placement_id": placement.id,
            "advertiser": placement.advertiser,
            "content_name": content.name if content else "Unknown",
            "content_id": placement.content_id,
            "content_type": content.type if content else "image",
            "content_file_url": content.file_url if content else None,
            "content_thumbnail": content_thumbnail,
            "certificate_id": certificate_id,
            "verification_url": verification_url,
            **_commercials(placement, generated_at),
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
        models.PlayLogHourlyRollup.organization_id == placement.organization_id,
        models.PlayLogHourlyRollup.media_id == placement.content_id,
        models.PlayLogHourlyRollup.screen_id.in_(screen_ids),
        models.PlayLogHourlyRollup.date_hour >= placement.starts_at,
        # The EFFECTIVE end, not the sold one. Bounding on placement.ends_at dropped every
        # play bought through an extension -- the client paid for the extra fortnight and
        # the report showed none of it.
        models.PlayLogHourlyRollup.date_hour <= effective_ends_at(placement),
    ]

    commercials = _commercials(placement, generated_at)
    ends = effective_ends_at(placement)

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
    # A screen reached through a GROUP inherits that group target's assignment date -- the
    # group is what was sold, so every member started when the group was added.
    assigned_at: dict[int, "datetime"] = {}
    for target in placement.targets:
        if target.screen_id:
            assigned_at[target.screen_id] = target.assigned_at
        elif target.group_id:
            for member in scope.query(models.Screen).filter(models.Screen.group_id == target.group_id).all():
                assigned_at.setdefault(member.id, target.assigned_at)

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
        cutoff = min(effective_ends_at(placement), generated_at - REPORTING_GRACE)
        is_stale = screen.last_seen is None or screen.last_seen < cutoff
        row = {
            "screen_id": screen.id,
            "screen_name": screen.name or f"Screen {screen.id}",
            "location": screen.location,
            # When this screen joined the booking. A screen added mid-campaign has fewer
            # days on air than the campaign has run, and dividing its plays by the campaign
            # length would report it as the worst performer rather than the newest.
            "assigned_at": assigned_at.get(screen.id) or placement.starts_at,
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
        place = places.setdefault(key, {
            "location": key, "screens": 0, "total_plays": 0,
            "_earliest_assignment": row["assigned_at"],
        })
        place["screens"] += 1
        place["total_plays"] += row["total_plays"]
        place["_earliest_assignment"] = min(place["_earliest_assignment"], row["assigned_at"])

    # Over days ELAPSED, not days sold. Dividing a mid-campaign total by the full period
    # understates every row on the page, and a client reading "1,200/day" on a report they
    # were told covers 30 days will multiply it out and ask where the rest went.
    #
    # And elapsed FOR THAT LOCATION: a screen added on the tenth day of a campaign has had
    # ten fewer days to play, so dividing it by the campaign's elapsed days reports a late
    # addition as an underperformer. The earliest assignment in the location wins, since
    # that is when the location started carrying the advert at all.
    day = 86400
    for place in places.values():
        started = place.pop("_earliest_assignment")
        elapsed = (min(generated_at, ends) - max(started, placement.starts_at)).total_seconds() / day
        place["days_elapsed"] = max(1, min(commercials["days_elapsed"], round(elapsed)))
        place["plays_per_day_avg"] = round(place["total_plays"] / place["days_elapsed"], 1)

    daily_rows = scope.db.query(
        func.date_trunc("day", models.PlayLogHourlyRollup.date_hour).label("day"),
        func.coalesce(func.sum(models.PlayLogHourlyRollup.total_plays), 0).label("plays"),
    ).filter(*window).group_by(text("1")).order_by(text("1")).all()

    return {
        "placement_id": placement.id,
        "advertiser": placement.advertiser,
        "content_name": content.name if content else "Unknown",
        "content_id": placement.content_id,
        "content_type": content.type if content else "image",
        "content_file_url": content.file_url if content else None,
        "content_thumbnail": content_thumbnail,
        "certificate_id": certificate_id,
        "verification_url": verification_url,
        **commercials,
        "starts_at": placement.starts_at,
        "ends_at": placement.ends_at,
        "price_paise": placement.price_paise,
        "is_paid": placement.is_paid,
        "generated_at": generated_at,
        "totals": totals,
        "per_screen": per_screen,
        "per_location": sorted(places.values(), key=lambda p: p["total_plays"], reverse=True),
        # Reported, never enforced. A plan's "5 locations" is what was quoted, and real
        # sales add a sixth screen mid-campaign; refusing that would mean editing the plan
        # to sell one extra TV. But the client's report prints the plan's inclusions, so a
        # booking running past them has to be visible rather than a quiet contradiction
        # between the plan card and the table underneath it.
        "plan_locations_exceeded": bool(
            placement.plan and len(places) > placement.plan.max_locations
        ),
        "plan_max_locations": placement.plan.max_locations if placement.plan else None,
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

    pdf, filename = _render_report(scope, placement)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{placement_id}/invoice.pdf")
def download_invoice(
    placement_id: int,
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor", "viewer")),
):
    """The commercial document: what was sold, what it cost, what was paid.

    Separate from report.pdf because they answer to different people. The report proves
    delivery and is safe to forward to anyone; this one restates the terms.
    """
    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    pdf, filename = _render_invoice(scope, placement)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _render_invoice(scope: TenantScope, placement: models.AdPlacement) -> tuple[bytes, str]:
    """The invoice PDF and the name to give it. Mirrors _render_report."""
    from ..reports.invoice import build_pdf, invoice_number

    report = build_booking_report(scope, placement)
    return build_pdf(report), f"{invoice_number(report)}.pdf"


def _render_report(scope: TenantScope, placement: models.AdPlacement) -> tuple[bytes, str]:
    """The PDF and the name to give it. Shared by the download and the email."""
    from ..reports.booking_report import build_pdf

    report = build_booking_report(scope, placement)
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in placement.advertiser).strip() or "client"
    return build_pdf(report), f"{safe} - playback report.pdf"


@router.get("/email-status")
def email_status():
    from .. import mailer
    configured = mailer.is_configured()
    return {
        "is_configured": configured,
        "sender": mailer.sender() if configured else None,
        "missing_variables": [] if configured else mailer.missing_configuration(),
    }


@router.post("/{placement_id}/email")
def email_booking_report(
    placement_id: int,
    document: str = "report",
    scope: TenantScope = Depends(require_tenant_roles("owner", "editor")),
):
    """Send the client their own report, or their invoice.

    The address comes from the client record, never from the request: accepting a
    recipient here would turn an authenticated tenant endpoint into a way to mail an
    arbitrary attachment to an arbitrary address from this server's domain. `document`
    chooses which PDF rather than a second route existing, so that guard is written once.
    """
    from .. import mailer

    placement = scope.get(models.AdPlacement, placement_id)
    if not placement:
        raise HTTPException(status_code=404, detail="Booking not found")

    client = placement.client
    if not client or not client.email:
        raise HTTPException(
            status_code=422,
            detail="This booking has no client email address. Add one on the client record first.",
        )

    if document not in ("report", "invoice"):
        raise HTTPException(status_code=422, detail="document must be 'report' or 'invoice'")

    is_invoice = document == "invoice"
    pdf, filename = (_render_invoice if is_invoice else _render_report)(scope, placement)
    organization = scope.db.query(models.Organization).filter(
        models.Organization.id == placement.organization_id
    ).first()
    sender_name = organization.name if organization else "your signage partner"
    noun = "invoice" if is_invoice else "playback report"

    try:
        mailer.send(
            to=client.email,
            subject=f"{'Invoice' if is_invoice else 'Playback report'} - {placement.advertiser}",
            body=(
                f"Hello {client.name},\n\n"
                f"Attached is the {noun} for your campaign "
                f"\"{placement.advertiser}\", covering "
                f"{placement.starts_at:%d %b %Y} to {effective_ends_at(placement):%d %b %Y}.\n\n"
                f"Regards,\n{sender_name}"
            ),
            attachment=pdf,
            attachment_name=filename,
        )
    except mailer.MailNotConfigured as exc:
        # 503 rather than 500: nothing is wrong with the request, the server simply cannot
        # send mail yet. The message names the missing variables so it is actionable.
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - SMTP failures are many and all mean the same here
        logger.exception("Failed to email report for placement %s", placement.id)
        raise HTTPException(status_code=502, detail=f"Could not send the email: {exc}")

    return {"status": "sent", "to": client.email}
