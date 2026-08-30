"""The two things that decide whether a free-tier deployment survives its own telemetry.

Both were verified by hand while being fixed and then had no guard, which is how they got
into this state in the first place:

* `play_log_hourly_rollups` had no prune at all -- no cron, no endpoint, no setting. It
  grows one row per (org, campaign, screen, media, hour) forever, ~36k rows a day for a
  hundred screens, and filled a 500MB database on its own in about two months.
* The storage quota summed only `Content.file_size_bytes`. A transcode adds a full-size
  master and a smaller rendition on top, so a 10GB quota admitted far more than 10GB of
  objects and the bucket filled while the dashboard still reported room to spare.

Run directly:  python tests/test_storage_budget.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_budget_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "budget-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"


def main() -> None:
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        admin = psycopg2.connect(
            "postgresql://postgres:postgres@localhost:5432/postgres", connect_timeout=3
        )
    except Exception:
        print("storage budget: SKIPPED (PostgreSQL is not reachable on localhost:5432)")
        return

    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    admin.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')
    admin.close()

    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from backend import models
    from backend.database import Base, SessionLocal, engine
    from backend.main import app
    from backend.routers.auth import create_access_token, get_password_hash
    import backend.worker as worker

    Base.metadata.create_all(bind=engine)
    worker.SessionLocal = SessionLocal
    client = TestClient(app)

    db = SessionLocal()
    org = models.Organization(name="Budget", slug=f"budget-{uuid.uuid4().hex[:6]}")
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = org.id

    screen = models.Screen(name="Panel", organization_id=org_id,
                           device_id=f"budget-tv-{uuid.uuid4().hex[:6]}")
    db.add(screen)
    db.commit()
    db.refresh(screen)
    screen_id = screen.id

    owner = models.User(
        organization_id=org_id, username=f"owner-{uuid.uuid4().hex[:6]}",
        role="owner", is_active=True, hashed_password=get_password_hash("password123"),
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    owner_username = owner.username

    # --- rollups are pruned ----------------------------------------------------------
    now = datetime.now(timezone.utc)
    rows = []
    for index in range(400):
        # Half beyond any sane retention, half recent. Distinct hours: the table has a
        # unique index across (org, campaign, screen, media, hour).
        old = index % 2 == 0
        rows.append({
            "organization_id": org_id,
            "campaign_id": None,
            "screen_id": screen_id,
            "media_id": index,
            "date_hour": now - timedelta(days=500 if old else 1, hours=index),
            "total_plays": 1,
            "completed_plays": 1,
            "partial_plays": 0,
            "error_plays": 0,
        })
    db.execute(models.PlayLogHourlyRollup.__table__.insert(), rows)
    db.commit()

    before = db.execute(text("SELECT count(*) FROM play_log_hourly_rollups")).scalar()
    assert before == 400, before

    os.environ["ROLLUP_RETENTION_DAYS"] = "400"
    asyncio.run(worker.prune_play_log_rollups(None))

    after = db.execute(text("SELECT count(*) FROM play_log_hourly_rollups")).scalar()
    assert after == 200, (
        f"rollup prune left {after} rows, expected the 200 recent ones; before this "
        "existed nothing ever deleted from this table"
    )

    # A second run must be idempotent -- it is scheduled nightly and mostly finds nothing.
    asyncio.run(worker.prune_play_log_rollups(None))
    assert db.execute(text("SELECT count(*) FROM play_log_hourly_rollups")).scalar() == 200

    # Retention is honoured, not hard-coded.
    os.environ["ROLLUP_RETENTION_DAYS"] = "0"
    asyncio.run(worker.prune_play_log_rollups(None))
    assert db.execute(text("SELECT count(*) FROM play_log_hourly_rollups")).scalar() == 0, (
        "ROLLUP_RETENTION_DAYS is not being read"
    )
    os.environ["ROLLUP_RETENTION_DAYS"] = "400"

    # --- the quota counts renditions, not just the source ----------------------------
    org_row = db.query(models.Organization).filter(models.Organization.id == org_id).one()
    org_row.storage_quota_bytes = 10_000
    db.commit()

    content = models.Content(
        organization_id=org_id, name="Clip", type="video",
        file_url="s3://org/clip_1080p.mp4", status="ready", file_size_bytes=4_000,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    # Renditions push the organisation over its quota even though the Content rows alone
    # would still fit; this is the arithmetic that used to be missed.
    db.add(models.MediaRendition(
        content_id=content.id, resolution="480p", width=854, height=480, rotation=0,
        duration_ms=1000, codec="h264", sha256="b" * 64, file_size_bytes=5_000,
        file_url="s3://org/clip_480p.mp4",
    ))
    db.commit()
    db.close()

    auth = {"Authorization": f"Bearer {create_access_token(data={'sub': owner_username})}"}
    response = client.post(
        "/api/content/upload",
        headers=auth,
        data={"name": "Another", "tags": "t"},
        files={"file": ("another.png", b"x" * 2_000, "image/png")},
    )
    assert response.status_code == 413, (
        "upload was accepted at 4,000 + 5,000 + 2,000 bytes against a 10,000 byte quota; "
        f"renditions are not being counted (got {response.status_code}: {response.text[:200]})"
    )


if __name__ == "__main__":
    main()
    print("storage budget: all checks passed")
