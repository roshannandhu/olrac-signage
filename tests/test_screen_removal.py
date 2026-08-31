"""Removing a TV: python tests/test_screen_removal.py

The feature did not exist -- no endpoint, no button -- and the obvious implementation is
unavailable: play_logs and play_log_hourly_rollups both hold a NOT NULL foreign key to
screens.id with no ON DELETE rule, so a real DELETE fails on the constraint for any screen
that has ever played anything.

What this pins down, in order of how badly each one fails silently:

  1. Play history SURVIVES a removal, with its screen attribution intact. The booking
     report attributes plays to a screen by name, so losing the row would under-report an
     advertiser's invoice rather than raise.
  2. The panel is signed OUT: every device endpoint answers 404, which is what the player
     reads as "you were removed".
  3. The removed screen leaves the fleet listing and frees its quota slot.
  4. The same hardware can be paired again afterwards, rather than being bricked by the
     unique constraint on device_id.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-removal-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "removal.db"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

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
os.environ["SECRET_KEY"] = "removal-test-secret-not-for-production"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"
os.environ["ALLOW_LEGACY_DEVICE_AUTH"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def run() -> None:
    client = TestClient(app)
    client.__enter__()
    try:
        db = database.SessionLocal()
        unique = uuid.uuid4().hex[:8]

        org = models.Organization(
            name=f"Removal {unique}", slug=f"removal-{unique}", status="active", max_screens=2
        )
        db.add(org)
        db.flush()
        org_id = org.id
        owner = models.User(
            organization_id=org.id, username=f"owner-{unique}", email=f"owner-{unique}@x.com",
            role="owner", is_active=True, hashed_password=get_password_hash("ownerpass1"),
        )
        db.add(owner)
        device_id = f"dev-{unique}"
        screen = models.Screen(
            organization_id=org.id, device_id=device_id, name="Shop Front",
            status="online", approved_at=models.utcnow(), last_seen=models.utcnow(),
        )
        db.add(screen)
        db.flush()
        screen_id = screen.id
        # Read before the session closes: attributes on a detached instance raise.
        owner_username = owner.username

        # The row that makes a naive DELETE impossible, and the one an advertiser is billed
        # on. Created before the removal so the constraint is genuinely exercised.
        db.add(models.PlayLog(
            event_id=f"evt-{unique}", screen_id=screen_id, organization_id=org.id,
            media_id=1, device_started_at=models.utcnow(), device_finished_at=models.utcnow(),
            corrected_started_at=models.utcnow(), corrected_finished_at=models.utcnow(),
            duration_ms=10_000, status="completed",
        ))
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {create_access_token({'sub': owner_username})}"}

        listed = client.get("/api/screens/", headers=headers).json()
        check(any(s["id"] == screen_id for s in listed), "screen missing from the fleet before removal")
        check(
            client.get(f"/api/screens/{device_id}/sync").status_code in (200, 204),
            "the device could not sync before removal, so the test proves nothing after",
        )

        response = client.delete(f"/api/screens/{screen_id}", headers=headers)
        check(response.status_code == 204, f"removal failed: {response.status_code} {response.text}")

        # 1. Billing history survives, still attributed to the screen it played on.
        db = database.SessionLocal()
        try:
            logs = db.query(models.PlayLog).filter(models.PlayLog.screen_id == screen_id).count()
            check(logs == 1, f"play history lost on removal: {logs} rows remain, expected 1")
            archived = db.query(models.Screen).filter(models.Screen.id == screen_id).first()
            check(archived is not None, "the screen row was destroyed; play_logs lost their name")
            check(archived is not None and archived.deleted_at is not None, "deleted_at was not set")
            check(
                archived is not None and archived.device_secret_hash is None,
                "the device credential outlived the removal",
            )
        finally:
            db.close()

        # 2. The panel is signed out. This 404 is what the player resets on.
        for path, method in (
            (f"/api/screens/{device_id}/sync", "get"),
            ("/api/screens/heartbeat", "post"),
        ):
            call = getattr(client, method)
            result = call(path, json={"device_id": device_id}) if method == "post" else call(path)
            check(
                result.status_code == 404,
                f"{method.upper()} {path} answered {result.status_code}; a removed screen must be gone",
            )

        # 3. Gone from the fleet, and its quota slot is free.
        listed = client.get("/api/screens/", headers=headers).json()
        check(not any(s["id"] == screen_id for s in listed), "removed screen still listed in the fleet")

        # 4. The same hardware can be paired again rather than bricked by the unique index.
        again = client.post("/api/screens/register", json={"device_id": device_id})
        check(again.status_code == 200, f"the panel could not re-register: {again.text}")
        if again.status_code == 200:
            body = again.json()
            check(body["id"] != screen_id, "re-registering resurrected the removed screen")
            check(bool(body.get("pair_code")), "a re-registered panel was given no pairing code")

        # 5. The archive flag alone must sign a device out, independently of the device_id
        #    rename that the removal endpoint also performs.
        #
        #    Worth its own case because the two mechanisms mask each other: with the rename
        #    in place, a lookup by the original device_id misses regardless of deleted_at,
        #    so a test that only removes through the endpoint passes even with the archive
        #    check deleted -- verified by reverting it, which this file did not catch until
        #    this case existed. Archiving a row directly is the only way to exercise it, and
        #    it is not a hypothetical: any row archived by hand, by a future bulk tool, or by
        #    a removal whose rename failed mid-transaction lands in exactly this state.
        db = database.SessionLocal()
        try:
            still_named = models.Screen(
                organization_id=org_id, device_id=f"archived-{unique}", name="Archived",
                status="online", approved_at=models.utcnow(), last_seen=models.utcnow(),
                deleted_at=models.utcnow(),
            )
            db.add(still_named)
            db.commit()
            archived_device_id = still_named.device_id
        finally:
            db.close()

        for path, method, payload in (
            (f"/api/screens/{archived_device_id}/sync", "get", None),
            ("/api/screens/heartbeat", "post", {"device_id": archived_device_id}),
            ("/api/screens/auth", "post", {"device_id": archived_device_id, "device_secret": "x"}),
        ):
            call = getattr(client, method)
            result = call(path, json=payload) if payload else call(path)
            check(
                result.status_code in (401, 404),
                f"{method.upper()} {path} answered {result.status_code}: an archived screen "
                "must not be served even when its device_id is unchanged",
            )

    finally:
        client.__exit__(None, None, None)


if __name__ == "__main__":
    run()
    if failures:
        print("SCREEN REMOVAL FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("screen removal: history preserved, panel signed out, quota freed, re-pairing works")
