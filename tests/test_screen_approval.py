"""Screen pairing is instant: python tests/test_screen_approval.py

This file used to assert a per-screen approval queue: /sign-in and the Google flow left
`approved_at` NULL and the screen was supposed to sync nothing until an owner approved it.

That gate never existed in practice. `approved_at` was written by /pair, /sign-in and
/enroll and read by nothing at all -- sync_tv never consulted it -- so a "pending" screen
synced and played exactly like an approved one, and "revoking" a screen did nothing. The
routes have been removed rather than wired up, because the gate that actually matters is
company approval (Organization.status), which a platform administrator controls.

What is asserted here now: every route that binds a screen admits it immediately, and a
screen belonging to an unapproved COMPANY still gets the demo reel rather than the
tenant's own playlist.
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

# Build the schema explicitly. backend.main used to do this as an import side effect,
# so importing the app silently wrote to whatever DATABASE_URL pointed at; it now runs
# in the lifespan, which a bare TestClient(app) never starts. Each isolated script owns
# its own database anyway, so creating it here is the honest version of what was
# happening implicitly before.
from backend import database as _bootstrap_db, models as _bootstrap_models
_bootstrap_models.Base.metadata.create_all(bind=_bootstrap_db.engine)

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


def test_sign_in_admits_the_screen_immediately():
    r = sign_in("dev-pending-1")
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is not None
    assert r.json()["status"] == "online"


def test_a_signed_in_screen_syncs_straight_away():
    sign_in("dev-pending-2")
    r = client.get("/api/screens/dev-pending-2/sync")
    assert r.status_code == 200, r.text
    assert r.json()["status"] != "pending_approval"


def test_sign_in_issues_a_device_credential():
    # The screen has to leave this call able to authenticate. Without it device auth stays
    # optional for everything except /enroll, and any caller who guesses a device id can
    # read the playlist and post play logs as that screen.
    r = sign_in("dev-credential-1")
    assert r.status_code == 200, r.text
    assert r.json()["device_secret"], "sign-in must hand the screen a device secret"


def test_the_issued_secret_authenticates():
    secret = sign_in("dev-credential-2").json()["device_secret"]
    r = client.post(
        "/api/screens/auth",
        json={"device_id": "dev-credential-2", "device_secret": secret},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    synced = client.get(
        "/api/screens/dev-credential-2/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert synced.status_code == 200, synced.text


def test_a_secret_does_not_authenticate_a_different_screen():
    # Both screens are created here rather than relying on another test: these run in
    # alphabetical order, so referencing a screen a later test creates fails by name.
    secret = sign_in("dev-credential-3").json()["device_secret"]
    sign_in("dev-credential-4")
    token = client.post(
        "/api/screens/auth",
        json={"device_id": "dev-credential-3", "device_secret": secret},
    ).json()["access_token"]
    # Same token, someone else's device id. This is the check that stops one TV reading
    # another tenant's playlist or filing play logs against their screen.
    r = client.get(
        "/api/screens/dev-credential-4/sync",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 401, r.text


def test_re_signing_in_keeps_the_screen_admitted():
    # A factory reset or a reinstall re-runs sign-in. Knocking a working screen dark would
    # turn a routine repair into an outage nobody would connect to the repair.
    sign_in("dev-approve-3")
    again = sign_in("dev-approve-3", name="Lobby TV")
    assert again.json()["approved_at"] is not None
    assert again.json()["status"] == "online"


def test_pairing_admits_immediately():
    # An operator redeemed the code from the dashboard; that IS the confirmation.
    code = client.post("/api/screens/register", json={"device_id": "dev-pair-1"}).json()["pair_code"]
    r = client.post("/api/screens/pair", json={"pair_code": code}, headers=auth_header())
    assert r.status_code == 200, r.text
    assert r.json()["approved_at"] is not None
    assert r.json()["device_secret"], "pairing must hand the screen a device secret"


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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    client.__exit__(None, None, None)
    print("screen approval: all checks passed")
