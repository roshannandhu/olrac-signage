"""SQLite must serve the same instants Postgres does.

`DateTime(timezone=True)` is a no-op on SQLite: it stored an aware UTC value and
read it back naive. Pydantic then emitted ISO text with no offset, and every JSON
client re-read it as *local* time — in IST that aged `last_seen` by 5h30m, so
healthy screens showed "Seen 5 hours ago" and tripped the offline alert. Postgres
was unaffected, so nothing caught it. models.UtcDateTime normalises on read.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-sqlite-utc-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "sqlite_utc.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"

from sqlalchemy import text  # noqa: E402

from backend import database, models, schemas  # noqa: E402


def run():
    models.Base.metadata.create_all(bind=database.engine)
    session = database.SessionLocal()
    try:
        stamped = datetime(2026, 8, 8, 17, 11, 39, tzinfo=timezone.utc)
        screen = models.Screen(device_id="sqlite-utc-device", status="online", last_seen=stamped)
        session.add(screen)
        session.commit()
        session.expire_all()

        stored = session.query(models.Screen).filter_by(device_id="sqlite-utc-device").one()

        assert stored.last_seen.tzinfo is not None, "SQLite returned a naive datetime"
        assert stored.last_seen == stamped, f"instant changed: {stored.last_seen} != {stamped}"

        # The wire format is what actually broke the dashboard: without an offset,
        # JavaScript's Date parses the string as local time.
        emitted = schemas.ScreenResponse.model_validate(stored).model_dump(mode="json")["last_seen"]
        assert emitted.endswith(("+00:00", "Z")), f"serialized without a UTC offset: {emitted}"
        assert "2026-08-08T17:11:39" in emitted, f"unexpected wall time: {emitted}"

        # A naive value already on disk (written before this fix) must also read back
        # as UTC rather than being reinterpreted in the server's local zone.
        session.execute(
            text("UPDATE screens SET last_seen = :stamp WHERE device_id = :device"),
            {"stamp": "2026-08-08 17:11:39.000000", "device": "sqlite-utc-device"},
        )
        session.commit()
        session.expire_all()
        legacy = session.query(models.Screen).filter_by(device_id="sqlite-utc-device").one()
        assert legacy.last_seen == stamped, f"legacy naive row drifted: {legacy.last_seen}"
    finally:
        session.close()

    print("SQLite UTC tests passed successfully")


if __name__ == "__main__":
    run()
