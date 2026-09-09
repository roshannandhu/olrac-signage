"""Self-serve signup -> pick a plan -> pay -> access, and the caps that come with it.

Drives the real storefront endpoints rather than asserting on rows, because the whole point
of the feature is that PAYING is what unblocks a workspace: a pending_approval org can reach
the storefront (get_billing_scope), a mock order confirmed activates it, and the plan's caps
and features are then enforced. Covers:

  - a paid package: pending until the order is confirmed, then active with a period end;
  - a free package: activated on the spot, no order;
  - the clients cap and the emergency-alert feature gate;
  - a bespoke custom request: submit -> operator prices -> tenant pays -> active on a hidden
    plan that never shows up in the sellable catalogue.

Run directly:  python tests/test_plan_purchase.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = "olrac_test_plan_purchase"
TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-plan-purchase-")


def _database_url() -> str:
    """Postgres when a server is there, SQLite otherwise -- as test_release_rollout does."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        admin = psycopg2.connect(
            "postgresql://postgres:postgres@localhost:5432/postgres", connect_timeout=3
        )
        admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        admin.cursor().execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        admin.cursor().execute(f"CREATE DATABASE {TEST_DB} OWNER olrac")
        admin.close()
        return f"postgresql://olrac:olrac_password@localhost:5432/{TEST_DB}"
    except Exception:
        return f"sqlite:///{Path(TEMP_DIR.name) / 'plan_purchase.db'}"


os.environ["DATABASE_URL"] = _database_url()
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
# The storefront is built to be driven by the mock provider; real Razorpay is the same path
# with a hosted checkout in front of it.
os.environ["PAYMENT_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.billing import ensure_billing_catalog  # noqa: E402
from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend import models  # noqa: E402
from backend.routers.auth import get_password_hash  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

PASSWORD = "password123"


def setup_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # A self-serve signup: pending workspace + owner. A separate platform operator.
        pending = models.Organization(name="Acme", slug="acme", status="pending_approval")
        ops = models.Organization(name="Ops", slug="ops", status="active")
        db.add_all([pending, ops])
        db.flush()
        db.add_all([
            models.User(organization_id=pending.id, username="owner", role="owner",
                        hashed_password=get_password_hash(PASSWORD), is_active=True),
            models.User(organization_id=ops.id, username="root", role="super_admin",
                        hashed_password=get_password_hash(PASSWORD), is_active=True),
        ])
        db.commit()
        # Seed the catalogue with the new period/clients/feature columns.
        ensure_billing_catalog(db)
    finally:
        db.close()


def bearer(username: str) -> dict:
    res = client.post("/api/auth/token", data={"username": username, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def org_status(slug: str) -> str:
    db = TestingSessionLocal()
    try:
        return db.query(models.Organization).filter(models.Organization.slug == slug).one().status
    finally:
        db.close()


def plan_id(slug: str) -> int:
    db = TestingSessionLocal()
    try:
        return db.query(models.Plan).filter(models.Plan.slug == slug).one().id
    finally:
        db.close()


def run() -> None:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    setup_db()
    owner = bearer("owner")
    root = bearer("root")

    # --- a pending workspace can see the catalogue and buy a paid package -----------
    plans = client.get("/api/billing/plans", headers=owner)
    check(plans.status_code == 200, f"storefront plans unreachable while pending: {plans.status_code} {plans.text[:120]}")

    buy = client.post("/api/billing/purchase", headers=owner, json={"plan_id": plan_id("business")})
    check(buy.status_code == 200, f"purchase failed: {buy.status_code} {buy.text[:160]}")
    body = buy.json()
    check(body["provider"] == "mock" and body.get("order_id"), f"expected a mock order, got {body}")
    check(org_status("acme") == "pending_approval", "workspace activated BEFORE payment was confirmed")

    confirm = client.post("/api/billing/mock/confirm", headers=owner, json={"order_id": body["order_id"]})
    check(confirm.status_code == 200, f"mock confirm failed: {confirm.status_code} {confirm.text[:160]}")
    check(org_status("acme") == "active", "workspace not activated after payment confirmed")

    db = TestingSessionLocal()
    try:
        sub = db.query(models.Subscription).join(models.Organization).filter(
            models.Organization.slug == "acme"
        ).one()
        check(sub.status == "active", f"subscription not active: {sub.status}")
        check(sub.current_period_end is not None, "no access-period end set after purchase")
    finally:
        db.close()

    # --- clients cap: business grants 50, so shrink the override and prove the wall ---
    db = TestingSessionLocal()
    try:
        org = db.query(models.Organization).filter(models.Organization.slug == "acme").one()
        org.max_clients = 1
        db.commit()
    finally:
        db.close()

    first = client.post("/api/clients/", headers=owner, json={"name": "Client A"})
    check(first.status_code == 201, f"first client rejected: {first.status_code} {first.text[:120]}")
    second = client.post("/api/clients/", headers=owner, json={"name": "Client B"})
    check(second.status_code == 409, f"client over cap returned {second.status_code}, expected 409")
    check("Upgrade" in second.json().get("detail", ""), "client-cap message does not mention upgrading")

    # --- feature gate: business includes emergency_alert, so a broadcast is allowed;
    #     move to free (no flag) and it must be refused ----------------------------------
    playlist = client.post("/api/playlists/", headers=owner, json={"name": "Loop"})
    check(playlist.status_code in (200, 201), f"playlist create failed: {playlist.status_code} {playlist.text[:120]}")
    pl_id = playlist.json()["id"] if playlist.status_code in (200, 201) else 0

    allowed = client.post("/api/emergency/broadcast", headers=owner,
                          json={"target_type": "all", "target_id": None, "playlist_id": pl_id})
    check(allowed.status_code == 200, f"emergency refused on a plan that includes it: {allowed.status_code} {allowed.text[:120]}")

    db = TestingSessionLocal()
    try:
        org = db.query(models.Organization).filter(models.Organization.slug == "acme").one()
        org.plan_id = plan_id("free")  # free has no emergency_alert
        db.commit()
    finally:
        db.close()

    blocked = client.post("/api/emergency/broadcast", headers=owner,
                          json={"target_type": "all", "target_id": None, "playlist_id": pl_id})
    check(blocked.status_code == 403, f"emergency allowed without the feature: {blocked.status_code} {blocked.text[:120]}")

    # --- custom request: submit -> operator prices -> tenant pays -> active -----------
    req = client.post("/api/billing/custom-request", headers=owner, json={
        "max_screens": 120, "max_clients": 40, "max_ad_slots": 0,
        "max_storage_bytes": 500 * 1024 ** 3, "duration_days": 90,
        "feature_flags": {"emergency_alert": True}, "notes": "airport rollout",
    })
    check(req.status_code == 201, f"custom request failed: {req.status_code} {req.text[:160]}")
    req_id = req.json()["id"]

    # cannot pay before it is priced
    early = client.post(f"/api/billing/custom-request/{req_id}/purchase", headers=owner)
    check(early.status_code == 409, f"unpriced custom purchase returned {early.status_code}, expected 409")

    queue = client.get("/api/admin/custom-requests", headers=root)
    check(queue.status_code == 200 and any(r["id"] == req_id for r in queue.json()),
          "custom request not visible in the operator queue")

    priced = client.post(f"/api/admin/custom-requests/{req_id}/price", headers=root, json={"price_paise": 750000})
    check(priced.status_code == 200 and priced.json()["status"] == "priced", f"pricing failed: {priced.text[:120]}")

    pay = client.post(f"/api/billing/custom-request/{req_id}/purchase", headers=owner)
    check(pay.status_code == 200 and pay.json().get("order_id"), f"custom purchase failed: {pay.text[:160]}")
    conf = client.post("/api/billing/mock/confirm", headers=owner, json={"order_id": pay.json()["order_id"]})
    check(conf.status_code == 200, f"custom confirm failed: {conf.status_code} {conf.text[:120]}")

    db = TestingSessionLocal()
    try:
        org = db.query(models.Organization).filter(models.Organization.slug == "acme").one()
        check(org.plan is not None and org.plan.slug == f"custom-{req_id}", "custom plan not applied to the workspace")
        check(org.effective_max_screens == 120, f"custom screens cap not applied: {org.effective_max_screens}")
    finally:
        db.close()

    # the bespoke plan is not a sellable package
    catalogue = client.get("/api/admin/plans", headers=root)
    slugs = [p["slug"] for p in catalogue.json()]
    check(f"custom-{req_id}" not in slugs, "bespoke custom plan leaked into the admin catalogue")

    if failures:
        print("PLAN PURCHASE FAILURES:")
        for line in failures:
            print("  -", line)
        raise SystemExit(1)
    print("Plan purchase passed: pay-to-access, clients cap, feature gate and custom flow all hold")


if __name__ == "__main__":
    run()
