import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import Profile, Website
from app.responses import ok, fail
from app.schemas import WebsiteCreateIn, WebsiteRead

router = APIRouter()


@router.get("")
async def list_websites(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Website)
        .where(Website.owner_id == profile.id)
        .order_by(Website.created_at.desc())
    )
    items = result.scalars().all()
    return ok([WebsiteRead.model_validate(w) for w in items])


@router.post("")
async def create_website(
    body: WebsiteCreateIn,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if not body.url.startswith(("http://", "https://")):
        return fail("Invalid URL — must start with http:// or https://", "bad_url", 400)

    website = Website(owner_id=profile.id, name=body.name, url=body.url)
    session.add(website)
    await session.commit()
    await session.refresh(website)
    return ok(WebsiteRead.model_validate(website))


@router.delete("/{website_id}")
async def delete_website(
    website_id: uuid.UUID,
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Website).where(Website.id == website_id, Website.owner_id == profile.id)
    )
    website = result.scalar_one_or_none()
    if website is None:
        return fail("Website not found", "not_found", 404)

    await session.delete(website)
    await session.commit()
    return ok({"ok": True})
