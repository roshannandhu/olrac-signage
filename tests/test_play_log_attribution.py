"""
Regression tests for proof-of-play attribution and durability.

Each of these fails against the pre-fix code:

1. Campaign attribution -- the player sends campaign_id = null on every event, so every
   play_log and rollup row had a NULL campaign and every campaign report read zero.
   Ingest now derives it from the event's playlist.
2. Deleted referents -- play_logs used to carry foreign keys to content/playlists/
   campaigns. Deleting content a device still had queued raised IntegrityError, the
   device retried its oldest batch forever, and every later play on that screen was lost.
3. PIN leak -- /screens/register is unauthenticated and used to return the full
   ScreenResponse, which includes maintenance_pin.
"""
import os
import sys
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-test-attr-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "attr.db"

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

test_db_name = f"olrac_test_{DB_PATH.stem.replace('-', '_')}"
try:
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    conn.cursor().execute(f"CREATE DATABASE {test_db_name} OWNER olrac")
    conn.close()
except Exception:
    pass

os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{test_db_name}"
os.environ["SECRET_KEY"] = "attribution-test-secret-key"

from fastapi.testclient import TestClient
from backend import database, models
from backend.main import app


def _event(started, **overrides):
    event = {
        "event_id": str(uuid.uuid4()),
        "device_started_at": started.isoformat(),
        "device_finished_at": (started + timedelta(seconds=10)).isoformat(),
        "corrected_started_at": started.isoformat(),
        "corrected_finished_at": (started + timedelta(seconds=10)).isoformat(),
        "duration_ms": 10000,
        "status": "completed",
    }
    event.update(overrides)
    return event


def run():
    failures = []

    with TestClient(app) as client:
        db = database.SessionLocal()
        try:
            models.Base.metadata.create_all(bind=db.get_bind())

            org = models.Organization(name="Attr Org", slug="attr-org")
            db.add(org)
            db.commit()
            db.refresh(org)

            screen = models.Screen(organization_id=org.id, device_id="attr-device", status="offline")
            campaign = models.Campaign(organization_id=org.id, name="Attr Campaign")
            db.add_all([screen, campaign])
            db.commit()
            db.refresh(screen)
            db.refresh(campaign)

            # The playlist is what carries the campaign link; the device never sees it.
            playlist = models.Playlist(
                organization_id=org.id, name="Attr Playlist", campaign_id=campaign.id
            )
            doomed = models.Content(organization_id=org.id, name="doomed.mp4", type="video")
            db.add_all([playlist, doomed])
            db.commit()
            db.refresh(playlist)
            db.refresh(doomed)

            db.add(models.EnrollmentToken(organization_id=org.id, token="attr-token", is_active=True))
            db.commit()

            org_id, screen_id = org.id, screen.id
            playlist_id, campaign_id, doomed_id = playlist.id, campaign.id, doomed.id
        finally:
            db.close()

        enroll = client.post(
            "/api/screens/enroll",
            json={"device_id": "attr-device", "enrollment_token": "attr-token"},
        )
        assert enroll.status_code == 200, f"Enrollment failed: {enroll.text}"
        auth = client.post(
            "/api/screens/auth",
            json={"device_id": "attr-device", "device_secret": enroll.json()["device_secret"]},
        )
        assert auth.status_code == 200, f"Auth failed: {auth.text}"
        jwt = {"Authorization": f"Bearer {auth.json()['access_token']}"}

        base = datetime.now(timezone.utc)

        # --- 1. campaign_id derived from the playlist when the device omits it ----------
        attributed = _event(base, playlist_id=playlist_id, media_id=doomed_id)
        res = client.post(
            "/api/screens/play-logs/batch",
            json={
                "device_id": "attr-device",
                "screen_id": screen_id,
                "organization_id": org_id,
                "events": [attributed],
            },
            headers=jwt,
        )
        if res.status_code != 200:
            failures.append(f"Attributed insert rejected: {res.text}")
        else:
            db = database.SessionLocal()
            try:
                stored = db.query(models.PlayLog).filter_by(event_id=attributed["event_id"]).one()
                if stored.campaign_id != campaign_id:
                    failures.append(
                        "campaign_id not derived from playlist: "
                        f"expected {campaign_id}, got {stored.campaign_id}"
                    )
            finally:
                db.close()

        # --- 2. a deleted referent must not wedge the queue -----------------------------
        db = database.SessionLocal()
        try:
            db.query(models.Content).filter_by(id=doomed_id).delete()
            db.query(models.Playlist).filter_by(id=playlist_id).delete()
            db.commit()
        finally:
            db.close()

        orphaned = _event(base + timedelta(minutes=1), playlist_id=playlist_id, media_id=doomed_id)
        res = client.post(
            "/api/screens/play-logs/batch",
            json={
                "device_id": "attr-device",
                "screen_id": screen_id,
                "organization_id": org_id,
                "events": [orphaned],
            },
            headers=jwt,
        )
        if res.status_code != 200 or res.json().get("inserted") != 1:
            failures.append(
                f"Events referencing deleted rows wedged the queue: {res.status_code} {res.text}"
            )

        # --- 3. the unauthenticated register route must not expose the maintenance pin --
        res = client.post("/api/screens/register", json={"device_id": "attr-device"})
        if res.status_code != 200:
            failures.append(f"register failed: {res.text}")
        elif "maintenance_pin" in res.json():
            failures.append("register leaks maintenance_pin to unauthenticated callers")

    if failures:
        print("PLAY LOG ATTRIBUTION FAILURES:")
        for line in failures:
            print("  -", line)
        raise SystemExit(1)

    print(
        "Attribution test passed: campaign derived from playlist, deleted referents do not "
        "wedge the queue, register does not leak the maintenance pin."
    )


if __name__ == "__main__":
    run()
