import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_admin
from app.models import Profile, Screen, PlaybackLog, Content
from app.responses import ok, fail

router = APIRouter()


def _default_range():
    """Return (from, to) for the last 7 days."""
    now = datetime.now(timezone.utc)
    return now - timedelta(days=7), now


@router.get("/summary")
async def report_summary(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
):
    frm, to = _default_range() if from_date is None else (from_date, to_date or datetime.now(timezone.utc))

    query = (
        select(
            Content.id.label("content_id"),
            Content.name,
            Content.type,
            func.count(PlaybackLog.id).label("play_count"),
            func.count(func.distinct(PlaybackLog.screen_id)).label("screen_count"),
            func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
        )
        .join(PlaybackLog, PlaybackLog.content_id == Content.id)
        .join(Screen, PlaybackLog.screen_id == Screen.id)
        .where(Screen.owner_id == profile.id)
        .where(PlaybackLog.played_at.between(frm, to))
        .group_by(Content.id, Content.name, Content.type)
        .order_by(func.count(PlaybackLog.id).desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return ok(
        [
            {
                "content_id": str(r.content_id),
                "name": r.name,
                "type": r.type,
                "screen_count": r.screen_count,
                "play_count": r.play_count,
                "total_duration": r.total_duration,
            }
            for r in rows
        ]
    )


@router.get("/by-screen")
async def report_by_screen(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
):
    frm, to = _default_range() if from_date is None else (from_date, to_date or datetime.now(timezone.utc))

    query = (
        select(
            Screen.id.label("screen_id"),
            Screen.name.label("screen_name"),
            func.count(PlaybackLog.id).label("play_count"),
            func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
        )
        .join(PlaybackLog, PlaybackLog.screen_id == Screen.id)
        .where(Screen.owner_id == profile.id)
        .where(PlaybackLog.played_at.between(frm, to))
        .group_by(Screen.id, Screen.name)
        .order_by(func.count(PlaybackLog.id).desc())
    )

    result = await session.execute(query)
    rows = result.all()

    return ok(
        [
            {
                "screen_id": str(r.screen_id),
                "screen_name": r.screen_name,
                "play_count": r.play_count,
                "total_duration": r.total_duration,
            }
            for r in rows
        ]
    )


@router.get("/hourly")
async def report_hourly(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
):
    frm, to = _default_range() if from_date is None else (from_date, to_date or datetime.now(timezone.utc))

    hour_col = func.date_trunc("hour", PlaybackLog.played_at).label("hour")

    query = (
        select(
            Screen.id.label("screen_id"),
            Screen.name.label("screen_name"),
            hour_col,
            func.count(PlaybackLog.id).label("play_count"),
            func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
        )
        .join(PlaybackLog, PlaybackLog.screen_id == Screen.id)
        .where(Screen.owner_id == profile.id)
        .where(PlaybackLog.played_at.between(frm, to))
        .group_by(Screen.id, Screen.name, hour_col)
        .order_by(hour_col.asc())
    )

    result = await session.execute(query)
    rows = result.all()

    return ok(
        [
            {
                "screen_id": str(r.screen_id),
                "screen_name": r.screen_name,
                "hour": r.hour.isoformat() if r.hour else None,
                "play_count": r.play_count,
                "total_duration": r.total_duration,
            }
            for r in rows
        ]
    )


@router.get("/export")
async def export_report(
    profile: Profile = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
    type: str = Query(..., pattern="^(summary|by-screen|hourly)$"),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
):
    """Stream a CSV export for the given report type."""
    frm, to = _default_range() if from_date is None else (from_date, to_date or datetime.now(timezone.utc))

    if type == "summary":
        query = (
            select(
                Content.id.label("content_id"),
                Content.name,
                Content.type,
                func.count(func.distinct(PlaybackLog.screen_id)).label("screen_count"),
                func.count(PlaybackLog.id).label("play_count"),
                func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
            )
            .join(PlaybackLog, PlaybackLog.content_id == Content.id)
            .join(Screen, PlaybackLog.screen_id == Screen.id)
            .where(Screen.owner_id == profile.id)
            .where(PlaybackLog.played_at.between(frm, to))
            .group_by(Content.id, Content.name, Content.type)
            .order_by(func.count(PlaybackLog.id).desc())
        )
        result = await session.execute(query)
        rows = result.all()
        header = ["content_id", "name", "type", "screen_count", "play_count", "total_duration"]
        data = [[str(r.content_id), r.name, r.type, r.screen_count, r.play_count, r.total_duration] for r in rows]

    elif type == "by-screen":
        query = (
            select(
                Screen.id.label("screen_id"),
                Screen.name.label("screen_name"),
                func.count(PlaybackLog.id).label("play_count"),
                func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
            )
            .join(PlaybackLog, PlaybackLog.screen_id == Screen.id)
            .where(Screen.owner_id == profile.id)
            .where(PlaybackLog.played_at.between(frm, to))
            .group_by(Screen.id, Screen.name)
            .order_by(func.count(PlaybackLog.id).desc())
        )
        result = await session.execute(query)
        rows = result.all()
        header = ["screen_id", "screen_name", "play_count", "total_duration"]
        data = [[str(r.screen_id), r.screen_name, r.play_count, r.total_duration] for r in rows]

    elif type == "hourly":
        hour_col = func.date_trunc("hour", PlaybackLog.played_at).label("hour")
        query = (
            select(
                Screen.id.label("screen_id"),
                Screen.name.label("screen_name"),
                hour_col,
                func.count(PlaybackLog.id).label("play_count"),
                func.coalesce(func.sum(PlaybackLog.duration_played), 0).label("total_duration"),
            )
            .join(PlaybackLog, PlaybackLog.screen_id == Screen.id)
            .where(Screen.owner_id == profile.id)
            .where(PlaybackLog.played_at.between(frm, to))
            .group_by(Screen.id, Screen.name, hour_col)
            .order_by(hour_col.asc())
        )
        result = await session.execute(query)
        rows = result.all()
        header = ["screen_id", "screen_name", "hour", "play_count", "total_duration"]
        data = [[str(r.screen_id), r.screen_name, r.hour.isoformat() if r.hour else "", r.play_count, r.total_duration] for r in rows]

    else:
        return fail("Unknown report type", "bad_type", 400)

    # Build CSV in memory
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(data)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="olrac-report-{type}.csv"',
        },
    )
