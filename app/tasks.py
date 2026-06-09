import asyncio
from app.db import async_session_maker


async def offline_sweeper():
    """Background task: marks screens offline if no heartbeat in 90 seconds.
    Full implementation in B4 — this is a non-crashing stub."""
    while True:
        try:
            async with async_session_maker() as session:
                from sqlalchemy import text
                await session.execute(
                    text(
                        "UPDATE screens SET status = 'offline' WHERE status = 'online' AND last_seen_at < now() - interval '90 seconds'"
                    )
                )
                await session.commit()
        except Exception:
            pass
        await asyncio.sleep(30)
