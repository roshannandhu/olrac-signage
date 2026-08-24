"""A self-enrolled screen waits for an operator: python tests/test_screen_approval.py

Signing in on the TV proves who the installer is; it does not prove the operator wanted
that device in the fleet. So /sign-in and the Google flow leave the screen pending and it
syncs nothing until approved, while /pair and /enroll -- which already carry an operator's
intent -- admit the screen immediately.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-approval-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "approval.db"
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
os.environ["SECRET_KEY"] = "approval-test-secret-key-not-for-production"
os.environ["INITIAL_ADMIN_USERNAME"] = "approval-owner"
os.environ["INITIAL_ADMIN_PASSWORD"] = "approval-password-123"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend.limiter import limiter  # noqa: E402
from backend.main import app  # noqa: E402

# This file drives /sign-in and /auth/token dozens of times in a few seconds, which is
# exactly what the per-IP caps exist to stop. The caps are a separate concern from the
# approval gate, so they are off here rather than being worked around with sleeps.
limiter.enabled = False

# As a context manager, so the lifespan runs and seeds the initial owner. A bare
# TestClient(app) skips startup entirely and every sign-in comes back 401.
client = TestClient(app)
client.__enter__()

# The seeded org lands on the Free plan, which caps at 5 screens -- this file enrols more
# than that. Raised here rather than by enrolling fewer screens: the cap is a real product
# limit with its own test (test_quotas.py), and it is not what the approval gate is about.
def _lift_screen_cap() -> None:
    from backend import database, models

    db = database.SessionLocal()
    try:
        for plan in db.query(models.Plan).all():
            plan.max_screens = 1000
        db.commit()
    finally:
        db.close()


_lift_screen_cap()


_token: str | None = None


def auth_header() -> dict[str, str]:
    global _token
    if _token is None:
        r = client.post(
            "/api/auth/token",
            data={"username": "approval-owner", "password": "approval-password-123"},
        )
        assert r.status_code == 200, r.text
        _token = r.json()["access_token"]
    return {"Authorization": f"Bearer {_token}"}


def sign_in(device_id: str, name: str = "Lobby TV"):
    return client.post(
        "/api/screens/sign-in",
        json={
            "device_id": device_id,
            "username": "approval-owner",
            "password": "approval-password-123",
            "name": name,
        },
    )


def test_sign_in_leaves_the_screen_pending():
    r = sign_in("dev-pending-1")
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is None


def test_a_pending_screen_syncs_nothing():
    sign_in("dev-pending-2")
    r = client.get("/api/screens/dev-pending-2/sync")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "pending_approval"
    assert body["playlist"] is None


def test_approval_admits_the_screen():
    sign_in("dev-approve-1")
    screen_id = sign_in("dev-approve-1").json()["id"]

    r = client.post(f"/api/screens/{screen_id}/approve", headers=auth_header())
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is not None

    body = client.get("/api/screens/dev-approve-1/sync").json()
    assert body["status"] != "pending_approval"


def test_approving_twice_keeps_the_first_timestamp():
    # The queue is worked in bulk; a double-click must not rewrite when it was admitted.
    screen_id = sign_in("dev-approve-2").json()["id"]
    first = client.post(f"/api/screens/{screen_id}/approve", headers=auth_header()).json()["approved_at"]
    second = client.post(f"/api/screens/{screen_id}/approve", headers=auth_header()).json()["approved_at"]
    assert first == second


def test_re_signing_in_does_not_send_an_approved_screen_back_to_the_queue():
    # A factory reset or a reinstall re-runs sign-in. Knocking a working screen dark would
    # turn a routine repair into an outage nobody would connect to the repair.
    screen_id = sign_in("dev-approve-3").json()["id"]
    client.post(f"/api/screens/{screen_id}/approve", headers=auth_header())
    again = sign_in("dev-approve-3", name="Lobby TV")
    assert again.json()["approved_at"] is not None


def test_revoking_puts_it_back_in_the_queue():
    screen_id = sign_in("dev-revoke-1").json()["id"]
    client.post(f"/api/screens/{screen_id}/approve", headers=auth_header())
    r = client.post(f"/api/screens/{screen_id}/revoke-approval", headers=auth_header())
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is None
    assert client.get("/api/screens/dev-revoke-1/sync").json()["status"] == "pending_approval"


def test_pairing_admits_immediately():
    # An operator redeemed the code from the dashboard; that IS the confirmation.
    code = client.post("/api/screens/register", json={"device_id": "dev-pair-1"}).json()["pair_code"]
    r = client.post("/api/screens/pair", json={"pair_code": code}, headers=auth_header())
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is not None


def test_enrolment_token_admits_immediately():
    # Zero-touch must stay zero-touch: an owner already authorised this by issuing the token.
    token = client.post(
        "/api/enrollment-tokens/",
        json={"description": "site A", "max_uses": 5},
        headers=auth_header(),
    ).json()["token"]
    r = client.post(
        "/api/screens/enroll",
        json={"device_id": "dev-enroll-1", "enrollment_token": token, "installation_id": "i1"},
    )
    assert r.status_code == 200, r.text
    detail = client.get("/api/screens/", headers=auth_header()).json()
    enrolled = [s for s in detail if s["device_id"] == "dev-enroll-1"]
    assert enrolled and enrolled[0]["approved_at"] is not None


def test_only_an_owner_can_approve():
    screen_id = sign_in("dev-perm-1").json()["id"]
    r = client.post(f"/api/screens/{screen_id}/approve")
    assert r.status_code in (401, 403), r.text


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    client.__exit__(None, None, None)
    print("screen approval: all checks passed")
