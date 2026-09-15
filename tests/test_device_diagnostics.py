"""A screen can report its own state for support to read, and only the screen itself can.

TVs sit in venues far from whoever supports them. When one misbehaves in a way only its own
settings reveal -- a locked accessibility switch, a revoked permission -- the player's report
is the only way to see it without sending someone.
"""
import json
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-diag-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-diagnostics")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def run() -> None:
    db = database.SessionLocal()
    org = models.Organization(name="Venue", slug=f"v-{uuid.uuid4().hex[:8]}", status="active")
    db.add(org)
    db.flush()
    screen = models.Screen(organization_id=org.id, device_id="tv-diag", status="online")
    db.add(screen)
    db.flush()
    from backend.services import issue_device_secret
    secret = issue_device_secret(screen)
    screen_id = screen.id
    db.commit()
    db.close()

    client = TestClient(app)
    token = client.post("/api/screens/auth", json={"device_id": "tv-diag", "device_secret": secret}).json()["access_token"]
    device = {"Authorization": f"Bearer {token}"}
    report = {"watchdog_enabled": False, "restricted_op": "error: SecurityException", "sdk": 34}

    ok = client.post("/api/screens/diagnostics", headers=device, json={"device_id": "tv-diag", "report": report})
    check(ok.status_code == 200, f"an authenticated screen could not report: {ok.status_code} {ok.text}")

    db = database.SessionLocal()
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == f"device_diagnostics:{screen_id}").first()
    check(row is not None and json.loads(row.value)["report"] == report, "the report was not stored as sent")
    db.close()

    again = client.post("/api/screens/diagnostics", headers=device,
                        json={"device_id": "tv-diag", "report": {"watchdog_enabled": True}})
    check(again.status_code == 200, "a second report was refused")
    db = database.SessionLocal()
    rows = db.query(models.SystemSetting).filter(models.SystemSetting.key == f"device_diagnostics:{screen_id}").all()
    check(len(rows) == 1 and json.loads(rows[0].value)["report"] == {"watchdog_enabled": True},
          "a newer report did not replace the old one")
    db.close()

    anonymous = client.post("/api/screens/diagnostics", json={"device_id": "tv-diag", "report": report})
    check(anonymous.status_code in (401, 403),
          f"a caller with only the device id could overwrite a screen's diagnostics: {anonymous.status_code}")

    huge = client.post("/api/screens/diagnostics", headers=device,
                       json={"device_id": "tv-diag", "report": {"blob": "x" * 20_000}})
    check(huge.status_code == 413, f"an oversized report was accepted: {huge.status_code}")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("DIAGNOSTICS FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - screens report their own state, and only they can")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
