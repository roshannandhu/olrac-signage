"""Super Admin boundary and the auth holes it closed: python tests/test_platform_admin.py

Three things are asserted here, each of which was exploitable against the live deployment:

1. POST /api/auth/google accepted ANY string containing "@" as a verified Google identity
   and returned a seven-day token for that account -- with no credential, and even when
   Google was correctly configured. Total authentication bypass.
2. /api/approvals gated its platform-admin routes on `role in ("manager", "owner")`. Every
   Google signup is created with role="owner", so every customer could list all tenants,
   read their owners' addresses, approve their own workspace and suspend a competitor.
3. Suspending a tenant only changed a label. get_tenant_scope checked "pending_approval"
   and nothing else, so a suspended or rejected org kept full read and write access.

Plus the surface that replaces them: packages, quotas, and the read-only tenant drill-in.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-admin-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "admin.db"
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
os.environ["SECRET_KEY"] = "admin-test-secret-key-not-for-production"
os.environ["INITIAL_ADMIN_USERNAME"] = "platform-owner"
os.environ["INITIAL_ADMIN_PASSWORD"] = "platform-password-123"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.limiter import limiter  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import get_password_hash  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

limiter.enabled = False

client = TestClient(app)
client.__enter__()

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def token_for(username: str, password: str) -> str:
    response = client.post("/api/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def seed() -> dict:
    """One platform operator, and one ordinary tenant owner in a separate organisation."""
    db = database.SessionLocal()
    try:
        operator = db.query(models.User).filter(models.User.username == "platform-owner").one()
        operator.role = "super_admin"

        tenant_org = models.Organization(name="Acme Media", slug="acme-media", status="active")
        db.add(tenant_org)
        db.flush()

        tenant_owner = models.User(
            organization_id=tenant_org.id,
            username="acme-owner",
            email="owner@acme.example",
            hashed_password=get_password_hash("acme-password-123"),
            role="owner",
            is_active=True,
        )
        db.add(tenant_owner)

        pending_org = models.Organization(
            name="Beta Signage", slug="beta-signage", status="pending_approval"
        )
        db.add(pending_org)
        db.flush()
        db.add(
            models.User(
                organization_id=pending_org.id,
                username="beta-owner",
                email="owner@beta.example",
                hashed_password=get_password_hash("beta-password-123"),
                role="owner",
                is_active=True,
            )
        )
        db.commit()
        return {"tenant_org": tenant_org.id, "pending_org": pending_org.id}
    finally:
        db.close()


def run() -> None:
    ids = seed()
    admin = auth(token_for("platform-owner", "platform-password-123"))
    tenant = auth(token_for("acme-owner", "acme-password-123"))

    # --- 1. The Google authentication bypass -----------------------------------------
    # The exploit was a single unauthenticated request naming the victim's address.
    bypass = client.post(
        "/api/auth/google",
        json={"code": "owner@acme.example", "redirect_uri": "http://localhost:3000/login"},
    )
    check(
        bypass.status_code != 200,
        f"SECURITY: an email address was accepted as a Google identity ({bypass.status_code})",
    )
    check(
        "access_token" not in bypass.text,
        "SECURITY: /api/auth/google returned a token without a real authorization code",
    )

    # The route that rendered real users' names and emails to anonymous callers is gone.
    for path in ("/api/auth/google/oauth-page", "/api/screens/google/oauth-page"):
        check(
            client.get(path, params={"redirect_uri": "http://x", "state": "y"}).status_code == 404,
            f"SECURITY: {path} still exists and enumerates users",
        )

    # --- 2. A tenant owner is not a platform administrator ----------------------------
    for method, path in (
        ("get", "/api/admin/tenants"),
        ("get", f"/api/admin/tenants/{ids['tenant_org']}"),
        ("get", "/api/admin/plans"),
    ):
        response = getattr(client, method)(path, headers=tenant)
        check(
            response.status_code == 403,
            f"SECURITY: a tenant owner reached {path} ({response.status_code})",
        )

    for path in ("approve", "suspend", "reject", "reinstate"):
        response = client.post(f"/api/admin/tenants/{ids['pending_org']}/{path}", headers=tenant, json={})
        check(
            response.status_code == 403,
            f"SECURITY: a tenant owner could {path} an organisation ({response.status_code})",
        )

    # And the operator can.
    listed = client.get("/api/admin/tenants", headers=admin)
    check(listed.status_code == 200, f"super admin could not list tenants: {listed.text}")
    check(len(listed.json()) >= 3, "super admin sees fewer tenants than exist")

    # --- 3. Packages carry the limits -------------------------------------------------
    created = client.post(
        "/api/admin/plans",
        headers=admin,
        json={
            "name": "Test Starter", "slug": "test-starter",
            "monthly_price_paise": 99900, "yearly_price_paise": 999000,
            "max_screens": 3, "max_storage_bytes": 1024 ** 3, "max_ad_slots": 2,
            "is_active": True,
        },
    )
    check(created.status_code == 201, f"package creation failed: {created.text}")
    package_id = created.json()["id"] if created.status_code == 201 else None

    if package_id:
        duplicate = client.post(
            "/api/admin/plans",
            headers=admin,
            json={
                "name": "Clash", "slug": "test-starter", "monthly_price_paise": 0,
                "yearly_price_paise": 0, "max_screens": 1, "max_storage_bytes": 1,
                "max_ad_slots": 1, "is_active": True,
            },
        )
        check(duplicate.status_code == 409, "a duplicate package slug was accepted")

        edited = client.patch(f"/api/admin/plans/{package_id}", headers=admin, json={"max_screens": 7})
        check(
            edited.status_code == 200 and edited.json()["max_screens"] == 7,
            f"package edit failed: {edited.text}",
        )

    # --- 4. Approving onto a package applies its limits -------------------------------
    approved = client.post(
        f"/api/admin/tenants/{ids['pending_org']}/approve",
        headers=admin,
        json={"plan_id": package_id} if package_id else {},
    )
    check(approved.status_code == 200, f"approval failed: {approved.text}")
    if approved.status_code == 200 and package_id:
        body = approved.json()
        check(body["status"] == "active", "approved organisation is not active")
        check(body["max_screens"] == 7, f"package screen limit was not applied ({body['max_screens']})")
        check(body["max_ad_slots"] == 2, f"package ad limit was not applied ({body['max_ad_slots']})")

    # The tenant can now use the API.
    beta = auth(token_for("beta-owner", "beta-password-123"))
    check(client.get("/api/screens/", headers=beta).status_code == 200, "approved tenant cannot use the API")

    # --- 5. Suspension actually blocks --------------------------------------------------
    suspended = client.post(f"/api/admin/tenants/{ids['pending_org']}/suspend", headers=admin)
    check(suspended.status_code == 200, f"suspend failed: {suspended.text}")

    blocked = client.get("/api/screens/", headers=beta)
    check(
        blocked.status_code == 403,
        f"SECURITY: a suspended tenant still has API access ({blocked.status_code})",
    )
    write = client.post("/api/groups/", headers=beta, json={"name": "should not work"})
    check(
        write.status_code == 403,
        f"SECURITY: a suspended tenant can still write ({write.status_code})",
    )

    reinstated = client.post(f"/api/admin/tenants/{ids['pending_org']}/reinstate", headers=admin)
    check(reinstated.status_code == 200, f"reinstate failed: {reinstated.text}")
    check(
        client.get("/api/screens/", headers=beta).status_code == 200,
        "a reinstated tenant is still blocked",
    )

    # --- 6. The drill-in is read-only ---------------------------------------------------
    for suffix in ("screens", "content", "users"):
        response = client.get(f"/api/admin/tenants/{ids['tenant_org']}/{suffix}", headers=admin)
        check(response.status_code == 200, f"drill-in /{suffix} failed: {response.text}")
        check(isinstance(response.json(), list), f"drill-in /{suffix} did not return a list")

    check(
        client.get(f"/api/admin/tenants/{ids['tenant_org']}/screens", headers=tenant).status_code == 403,
        "SECURITY: a tenant owner can drill into another workspace",
    )

    # --- 7. A super admin still cannot be created over HTTP ------------------------------
    escalate = client.post(
        "/api/users/",
        headers=tenant,
        json={"username": "sneaky", "password": "password-123", "role": "super_admin"},
    )
    check(
        escalate.status_code in (403, 422),
        f"SECURITY: a tenant owner created a super_admin ({escalate.status_code})",
    )

    if failures:
        print("PLATFORM ADMIN FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("platform admin: all checks passed")


if __name__ == "__main__":
    try:
        run()
    finally:
        client.__exit__(None, None, None)
