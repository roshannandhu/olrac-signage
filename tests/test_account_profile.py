"""
Self-service account endpoints behind the dashboard's profile menu.

Covers the security-relevant behaviour, not just the happy path: PUT /api/users/{id} can
already set a password but is owner-gated and verifies nothing, so these routes are the
only way a non-owner rotates a credential -- and the only place a current-password check
exists at all.
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-test-acct-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "acct.db"

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
os.environ["SECRET_KEY"] = "account-test-secret-key"

from fastapi.testclient import TestClient
from backend import database, models
from backend.main import app
from backend.routers.auth import get_password_hash


def _token(client, username, password):
    res = client.post("/api/auth/token", data={"username": username, "password": password})
    assert res.status_code == 200, f"login failed for {username}: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def run():
    failures = []

    with TestClient(app) as client:
        db = database.SessionLocal()
        try:
            models.Base.metadata.create_all(bind=db.get_bind())
            org = models.Organization(name="Acct Org", slug="acct-org")
            db.add(org)
            db.commit()
            db.refresh(org)

            db.add_all([
                models.User(
                    organization_id=org.id, username="acct-viewer",
                    hashed_password=get_password_hash("original-pass"), role="viewer",
                ),
                models.User(
                    organization_id=org.id, username="acct-other",
                    hashed_password=get_password_hash("other-pass"), role="viewer",
                    email="taken@example.com",
                ),
            ])
            db.commit()
        finally:
            db.close()

        headers = _token(client, "acct-viewer", "original-pass")

        # --- /me exposes the profile fields the account menu renders -------------------
        me = client.get("/api/auth/me", headers=headers)
        if me.status_code != 200:
            failures.append(f"/me failed: {me.text}")
        else:
            for field in ("full_name", "email", "organization_name"):
                if field not in me.json():
                    failures.append(f"/me missing {field}")
            if me.json().get("organization_name") != "Acct Org":
                failures.append(f"organization_name not resolved: {me.json().get('organization_name')}")

        # --- a viewer can edit their own profile --------------------------------------
        res = client.patch(
            "/api/auth/me",
            json={"full_name": "Acct Viewer", "email": "viewer@example.com"},
            headers=headers,
        )
        if res.status_code != 200 or res.json().get("full_name") != "Acct Viewer":
            failures.append(f"profile update failed: {res.status_code} {res.text}")

        # --- profile edit must not be a privilege escalation path ---------------------
        res = client.patch("/api/auth/me", json={"role": "owner"}, headers=headers)
        after = client.get("/api/auth/me", headers=headers).json()
        if after.get("role") != "viewer":
            failures.append(f"role escalated through PATCH /me: now {after.get('role')}")

        # --- duplicate email is rejected rather than silently colliding ---------------
        res = client.patch("/api/auth/me", json={"email": "taken@example.com"}, headers=headers)
        if res.status_code != 409:
            failures.append(f"duplicate email not rejected: {res.status_code} {res.text}")

        # --- wrong current password is refused ----------------------------------------
        res = client.post(
            "/api/auth/change-password",
            json={"current_password": "not-the-password", "new_password": "brand-new-pass"},
            headers=headers,
        )
        if res.status_code != 403:
            failures.append(f"wrong current password accepted: {res.status_code} {res.text}")

        # ...and the old password still works afterwards
        if client.post(
            "/api/auth/token", data={"username": "acct-viewer", "password": "original-pass"}
        ).status_code != 200:
            failures.append("failed password change invalidated the existing password")

        # --- reusing the same password is refused --------------------------------------
        res = client.post(
            "/api/auth/change-password",
            json={"current_password": "original-pass", "new_password": "original-pass"},
            headers=headers,
        )
        if res.status_code != 400:
            failures.append(f"password reuse accepted: {res.status_code} {res.text}")

        # --- the real change works, and swaps which password authenticates ------------
        res = client.post(
            "/api/auth/change-password",
            json={"current_password": "original-pass", "new_password": "brand-new-pass"},
            headers=headers,
        )
        if res.status_code != 204:
            failures.append(f"password change failed: {res.status_code} {res.text}")

        if client.post(
            "/api/auth/token", data={"username": "acct-viewer", "password": "original-pass"}
        ).status_code != 401:
            failures.append("old password still authenticates after change")
        if client.post(
            "/api/auth/token", data={"username": "acct-viewer", "password": "brand-new-pass"}
        ).status_code != 200:
            failures.append("new password does not authenticate after change")

        # --- unauthenticated callers get nothing --------------------------------------
        if client.patch("/api/auth/me", json={"full_name": "nobody"}).status_code != 401:
            failures.append("PATCH /me is reachable without a token")
        if client.post(
            "/api/auth/change-password",
            json={"current_password": "x", "new_password": "yyyyyyyy"},
        ).status_code != 401:
            failures.append("change-password is reachable without a token")

    if failures:
        print("ACCOUNT PROFILE FAILURES:")
        for line in failures:
            print("  -", line)
        raise SystemExit(1)

    print(
        "Account profile test passed: /me exposes profile fields, self-edit works without "
        "privilege escalation, duplicate email rejected, password change verifies the "
        "current password."
    )


if __name__ == "__main__":
    run()
