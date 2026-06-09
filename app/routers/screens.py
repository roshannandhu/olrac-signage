import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin, require_screen
from app.models import Profile, Screen
from app.responses import ok, fail
from app.schemas import PairIn, ScreenPatchIn, ScreenRead
from app.security import generate_screen_token, generate_pairing_code
from app.services.playlist import resolve_playlist_for_screen


def _parse_tags(tags_str: str | None) -> list[str]:
    if not tags_str or not tags_str.strip():
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]

router = APIRouter()


# ── PUBLIC (called by TV on first launch) ───────────────────────────────


@router.post("/request-code")
async def request_code(session: AsyncSession = Depends(get_session)):
    """Generate a 6-digit pairing code and screen_token for a new screen."""
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_pairing_code()
        # Check uniqueness
        existing = await session.execute(
            select(Screen).where(
                Screen.pairing_code == code, Screen.status == "pending"
            )
        )
        if existing.scalar_one_or_none() is None:
            break
    else:
        return fail("Could not generate unique code", "code_gen_error", 500)

    screen_token = generate_screen_token()

    screen = Screen(
        name="Unpaired screen",
        pairing_code=code,
        pairing_code_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        status="pending",
        orientation="D0",
        screen_token=screen_token,
    )
    session.add(screen)
    await session.commit()

    return ok({"code": code, "screen_token": screen_token})


# ── ADMIN: pair a pending screen ────────────────────────────────────────


@router.post("/pair")
async def pair_screen(
    body: PairIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Link a pending screen to the admin's account."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Screen).where(
            Screen.pairing_code == body.code,
            Screen.status == "pending",
            Screen.pairing_code_expires_at > now,
        )
    )
    screen = result.scalar_one_or_none()
    if screen is None:
        return fail("Invalid or expired code", "bad_code", 404)

    screen.name = body.name
    screen.orientation = body.orientation
    screen.owner_id = profile.id
    screen.status = "offline"
    screen.pairing_code = None
    screen.pairing_code_expires_at = None

    await session.commit()
    await session.refresh(screen)
    return ok(ScreenRead.model_validate(screen))


# ── TV: read self + playlist ────────────────────────────────────────────


@router.get("/me")
async def me(
    screen: Screen = Depends(require_screen),
    session: AsyncSession = Depends(get_session),
):
    """TV polls this every 30s. Returns screen + resolved playlist."""
    playlist = await resolve_playlist_for_screen(session, screen.id)
    return ok(
        {
            "screen": ScreenRead.model_validate(screen),
            "playlist": playlist,
        }
    )


# ── ADMIN: list all screens ─────────────────────────────────────────────


@router.get("")
async def list_screens(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Screen)
        .where(Screen.owner_id == profile.id)
        .order_by(Screen.created_at.desc())
    )
    screens = result.scalars().all()
    return ok([ScreenRead.model_validate(s) for s in screens])


# ── ADMIN: update screen ────────────────────────────────────────────────


@router.patch("/{screen_id}")
async def patch_screen(
    screen_id: uuid.UUID,
    body: ScreenPatchIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Screen).where(Screen.id == screen_id, Screen.owner_id == profile.id)
    )
    screen = result.scalar_one_or_none()
    if screen is None:
        return fail("Screen not found", "not_found", 404)

    update_data = body.model_dump(exclude_unset=True)
    if "tags" in update_data and update_data["tags"] is not None:
        update_data["tags"] = _parse_tags(update_data["tags"])

    for field, value in update_data.items():
        if value is not None:
            setattr(screen, field, value)

    await session.commit()
    await session.refresh(screen)
    return ok(ScreenRead.model_validate(screen))


# ── SCREEN: heartbeat ──────────────────────────────────────────────────


@router.post("/{screen_id}/heartbeat")
async def heartbeat(
    screen_id: uuid.UUID,
    screen: Screen = Depends(require_screen),
    session: AsyncSession = Depends(get_session),
):
    """TV calls this every 30s to stay 'online'."""
    if screen.id != screen_id:
        return fail("Token/screen mismatch", "forbidden", 403)

    screen.last_seen_at = datetime.now(timezone.utc)
    screen.status = "online"
    await session.commit()
    return ok({"ok": True})


# ── ADMIN: delete screen ────────────────────────────────────────────────


@router.delete("/{screen_id}")
async def delete_screen(
    screen_id: uuid.UUID,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Screen).where(Screen.id == screen_id, Screen.owner_id == profile.id)
    )
    screen = result.scalar_one_or_none()
    if screen is None:
        return fail("Screen not found", "not_found", 404)

    await session.delete(screen)
    await session.commit()
    return ok({"ok": True})
