"""Play logs must roll up into hourly rows on every dialect, not just Postgres.

`aggregate_play_logs_sync` was a single Postgres statement built on `date_trunc`,
`UPDATE … RETURNING` and `IS NOT DISTINCT FROM`. On SQLite the whole statement
raised, the failure was swallowed by a `print`, and every play log stayed
unaggregated forever -- so proof of play, the booking report and the per-advert
tiles all reported zero on a database full of plays, with nothing in the logs to
say why. Production runs Postgres so it worked there; the test suite runs SQLite,
which is exactly where this went unnoticed.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-play-agg-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "play_agg.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"

from backend import database, models  # noqa: E402
from backend.worker import aggregate_play_logs_sync  # noqa: E402


def _log(event_id, screen_id, org_id, started, *, media_id=42, status="completed"):
    return models.PlayLog(
        event_id=event_id,
        screen_id=screen_id,
        organization_id=org_id,
        media_id=media_id,
        device_started_at=started,
        device_finished_at=started,
        corrected_started_at=started,
        corrected_finished_at=started,
        duration_ms=5000,
        status=status,
        aggregated=False,
    )


def run():
    models.Base.metadata.create_all(bind=database.engine)
    session = database.SessionLocal()
    try:
        org = models.Organization(name="Agg Co", slug="agg-co")
        session.add(org)
        session.flush()
        screen = models.Screen(organization_id=org.id, name="Lobby", device_id="agg-1")
        session.add(screen)
        session.flush()

        # Two different minutes of the same hour must land in one bucket -- that grouping
        # is what date_trunc did and what SQLite has no function for.
        hour = datetime(2026, 9, 11, 10, 0, tzinfo=timezone.utc)
        session.add(_log("e1", screen.id, org.id, hour.replace(minute=5)))
        session.add(_log("e2", screen.id, org.id, hour.replace(minute=47)))
        session.add(_log("e3", screen.id, org.id, hour.replace(minute=52), status="error"))
        # A different hour is its own row.
        session.add(_log("e4", screen.id, org.id, hour.replace(hour=11)))
        session.commit()

        assert aggregate_play_logs_sync(session) == 1, "aggregation reported failure"
        session.expire_all()

        rows = {
            r.date_hour: r
            for r in session.query(models.PlayLogHourlyRollup).all()
        }
        assert len(rows) == 2, f"expected one row per hour, got {len(rows)}"

        first = rows[hour]
        assert first.total_plays == 3, f"three plays in the 10:00 hour, got {first.total_plays}"
        assert first.completed_plays == 2, first.completed_plays
        assert first.error_plays == 1, first.error_plays
        assert first.duration_ms == 15000, first.duration_ms
        assert first.media_id == 42, "media_id must survive, or the per-advert report finds nothing"

        left = session.query(models.PlayLog).filter(models.PlayLog.aggregated.is_(False)).count()
        assert left == 0, f"{left} play logs were never marked aggregated"

        # Idempotent: the endpoint aggregates on every batch upload and every report read,
        # so a second pass must not bill the advertiser for the same play twice.
        assert aggregate_play_logs_sync(session) == 1
        session.expire_all()
        again = session.query(models.PlayLogHourlyRollup).filter_by(date_hour=hour).one()
        assert again.total_plays == 3, f"re-running double counted: {again.total_plays}"
    finally:
        session.close()

    print("Play log aggregation passed: hourly buckets, media attribution, idempotent re-run")


if __name__ == "__main__":
    run()
