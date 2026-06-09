from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Profile, Screen
from app.responses import ApiError
from app.supabase_client import supabase


async def require_admin(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Profile:
    """Verify the Supabase Auth JWT and return the authenticated profile.

    Uses supabase.auth.get_user() which works with both asymmetric (JWKS)
    and symmetric (HS256) signing.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError("Not authenticated", "unauthenticated", 401)

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError("Not authenticated", "unauthenticated", 401)

    try:
        user_response = supabase.auth.get_user(token)
    except Exception:
        raise ApiError("Invalid or expired token", "unauthenticated", 401)

    user = user_response.user
    if user is None or user.id is None:
        raise ApiError("Invalid or expired token", "unauthenticated", 401)

    result = await session.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()

    if profile is None:
        email = user.email or ""
        profile = Profile(
            id=user.id,
            email=email,
            name=email.split("@")[0] or "Admin",
            role="admin",
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

    return profile


async def require_screen(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> Screen:
    """Look up the opaque screen_token and return the screen row.

    Screens may ONLY: read their own data (/screens/me), heartbeat, and
    POST playback logs.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise ApiError("Not authenticated", "unauthenticated", 401)

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ApiError("Not authenticated", "unauthenticated", 401)

    result = await session.execute(select(Screen).where(Screen.screen_token == token))
    screen = result.scalar_one_or_none()

    if screen is None:
        raise ApiError("Invalid screen token", "unauthenticated", 401)

    return screen
