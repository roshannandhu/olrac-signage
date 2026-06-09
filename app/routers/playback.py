from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_screen
from app.models import Screen, PlaybackLog
from app.responses import ok
from app.schemas import PlaybackLogIn

router = APIRouter()


@router.post("/playback/log")
async def log_playback(
    body: list[PlaybackLogIn],
    screen: Screen = Depends(require_screen),
    session: AsyncSession = Depends(get_session),
):
    """Bulk-insert playback log entries from a screen."""
    inserted = 0
    for entry in body:
        # Skip entries whose content_id doesn't exist (ignore, don't fail)
        from sqlalchemy import select
        from app.models import Content

        c_result = await session.execute(
            select(Content).where(Content.id == entry.content_id)
        )
        if c_result.scalar_one_or_none() is None:
            continue

        log = PlaybackLog(
            screen_id=screen.id,
            content_id=entry.content_id,
            played_at=entry.played_at,
            duration_played=entry.duration_played,
        )
        session.add(log)
        inserted += 1

    await session.commit()
    return ok({"ok": True, "inserted": inserted})
