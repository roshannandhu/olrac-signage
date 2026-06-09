from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import Profile
from app.responses import ok, fail
from app.schemas import RegisterIn, LoginIn, ProfileRead
from app.supabase_client import supabase

router = APIRouter()


@router.post("/register")
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    """Create a new admin user via Supabase Auth and a matching profile row."""
    try:
        user_response = supabase.auth.admin.create_user(
            {
                "email": body.email,
                "password": body.password,
                "email_confirm": True,
            }
        )
    except Exception as exc:
        msg = str(exc)
        if "already" in msg.lower() and "registered" in msg.lower() or "duplicate" in msg.lower():
            return fail("Email already registered", "email_taken", 409)
        return fail(f"Registration failed: {msg}", "registration_error", 400)

    supabase_user = user_response.user
    if supabase_user is None:
        return fail("Registration failed", "registration_error", 400)

    profile = Profile(
        id=supabase_user.id,
        email=body.email,
        name=body.name,
        role="admin",
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    return ok(ProfileRead.model_validate(profile))


@router.post("/login")
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    """Authenticate with email + password via Supabase Auth."""
    try:
        auth_response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        msg = str(exc)
        if any(kw in msg.lower() for kw in ("invalid", "bad", "not found")):
            return fail("Invalid credentials", "bad_credentials", 401)
        return fail("Login failed", "login_error", 400)

    session_data = auth_response.session
    user = auth_response.user
    if session_data is None or user is None:
        return fail("Invalid credentials", "bad_credentials", 401)

    result = await session.execute(select(Profile).where(Profile.id == user.id))
    profile = result.scalar_one_or_none()

    return ok(
        {
            "access_token": session_data.access_token,
            "refresh_token": session_data.refresh_token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": profile.name if profile else (user.email or "").split("@")[0],
                "role": profile.role if profile else "admin",
            },
        }
    )


@router.get("/me")
async def me(profile: Profile = Depends(require_admin)):
    """Return the authenticated admin's profile."""
    return ok(ProfileRead.model_validate(profile))
