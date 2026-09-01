"""Clients and tenant-sold plans belong to one tenant, and a plan's terms are copied not linked.

Two properties are under test, and both silently corrupt a business rather than raising:

* Isolation. A tenant's client list is their customer list -- names, addresses and phone
  numbers -- and their plans are their pricing. Neither may be readable, bookable against,
  or editable by another tenant.
* Copy-on-sale. A booking takes its price and duration from a plan at the moment it is
  made. If it read through instead, repricing a package next quarter would restate every
  invoice already issued under the old one.

Throwaway Postgres database. Run directly:  python tests/test_tenant_plans.py
"""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_tenantplans_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "tenant-plans-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')

db = None
try:
    from fastapi.testclient import TestClient  # noqa: E402
    from backend import models  # noqa: E402
    from backend.database import SessionLocal, engine  # noqa: E402
    from backend.main import app  # noqa: E402
    from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    acme = models.Organization(name="Acme", slug="acme")
    rival = models.Organization(name="Rival", slug="rival")
    db.add_all([acme, rival]); db.commit()
    owner = models.User(organization_id=acme.id, username="owner@acme.test",
                        hashed_password=get_password_hash("x"), role="owner", is_active=True)
    intruder = models.User(organization_id=rival.id, username="owner@rival.test",
                           hashed_password=get_password_hash("x"), role="owner", is_active=True)
    db.add_all([owner, intruder]); db.commit()

    ad = models.Content(organization_id=acme.id, type="video", file_url="/uploads/1/a.mp4",
                        name="Summer Sale", status="ready", duration_ms=30_000)
    db.add(ad); db.commit()
    screen = models.Screen(organization_id=acme.id, name="Lobby", status="online")
    db.add(screen); db.commit()

    http = TestClient(app)
    auth = {"Authorization": f"Bearer {create_access_token(data={'sub': owner.username})}"}
    rival_auth = {"Authorization": f"Bearer {create_access_token(data={'sub': intruder.username})}"}
    now = models.utcnow()

    # --- client codes are per tenant, and issued without being asked for ---------------
    first = http.post("/api/clients/", headers=auth, json={"name": "BrightMart"})
    assert first.status_code == 201, first.text
    assert first.json()["client_code"] == "CLT00001", first.json()
    second = http.post("/api/clients/", headers=auth, json={"name": "Phoenix Retail"})
    assert second.json()["client_code"] == "CLT00002", second.json()

    # The rival starts at CLT00001 too. The uniqueness is per organisation on purpose --
    # a global sequence would leak how many clients other tenants have.
    theirs = http.post("/api/clients/", headers=rival_auth, json={"name": "Someone Else"})
    assert theirs.status_code == 201, theirs.text
    assert theirs.json()["client_code"] == "CLT00001", theirs.json()
    print("  ok  client codes are issued per tenant and restart for each one")

    # A new code must never collide with one still in use. Derived from the highest code
    # issued rather than from a count, because a count reissues CLT00002 the moment the
    # first client is deleted -- straight into the unique constraint.
    #
    # A code freed by a deletion IS reused, which is a deliberate limit: the alternative is
    # a persistent per-tenant counter, and the risk it accepts is an old invoice naming a
    # code now held by a different client.
    third = http.post("/api/clients/", headers=auth, json={"name": "Temp"})
    assert third.json()["client_code"] == "CLT00003", third.json()
    http.delete(f"/api/clients/{third.json()['id']}", headers=auth)
    fourth = http.post("/api/clients/", headers=auth, json={"name": "After The Gap"})
    assert fourth.status_code == 201, fourth.text
    live = [c["client_code"] for c in http.get("/api/clients/", headers=auth).json()]
    assert len(live) == len(set(live)), live
    print("  ok  a new client code never collides with a live one")

    # --- isolation --------------------------------------------------------------------
    acme_client_id = first.json()["id"]
    assert [c["name"] for c in http.get("/api/clients/", headers=rival_auth).json()] == ["Someone Else"]
    assert http.get(f"/api/clients/{acme_client_id}", headers=rival_auth).status_code == 404
    assert http.put(f"/api/clients/{acme_client_id}", headers=rival_auth,
                    json={"name": "Hijacked"}).status_code == 404
    assert http.delete(f"/api/clients/{acme_client_id}", headers=rival_auth).status_code == 404
    print("  ok  one tenant cannot read, edit or delete another's clients")

    plan = http.post("/api/tenant-plans/", headers=auth, json={
        "name": "Standard Plan", "duration_days": 31, "max_locations": 5,
        "ad_slots": 1, "price_paise": 2500000, "support_tier": "Basic Support",
    })
    assert plan.status_code == 201, plan.text
    plan_id = plan.json()["id"]
    assert http.get("/api/tenant-plans/", headers=rival_auth).json() == []
    assert http.get(f"/api/tenant-plans/{plan_id}", headers=rival_auth).status_code == 404
    print("  ok  one tenant cannot see or fetch another's plans")

    # --- a plan fills in price and end date, by copying them ---------------------------
    booked = http.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "client_id": acme_client_id, "plan_id": plan_id,
        "starts_at": now.isoformat(), "targets": [{"screen_id": screen.id}],
    })
    assert booked.status_code == 201, booked.text
    body = booked.json()
    assert body["price_paise"] == 2500000, body
    assert body["advertiser"] == "BrightMart", body
    assert body["client"]["client_code"] == "CLT00001", body
    # duration_days drove the end date, which is the point of selling by package.
    assert body["effective_ends_at"][:10] == (now + timedelta(days=31)).date().isoformat(), body
    print("  ok  booking on a plan takes its price and its duration")

    # Repricing the plan must not restate the sold booking.
    http.put(f"/api/tenant-plans/{plan_id}", headers=auth, json={"price_paise": 9900000})
    after = http.get("/api/placements/", headers=auth).json()[0]
    assert after["price_paise"] == 2500000, after
    print("  ok  repricing a plan leaves an already-sold booking billed as agreed")

    # A plan with bookings is retired, not deleted: the report still prints its name.
    retired = http.delete(f"/api/tenant-plans/{plan_id}", headers=auth)
    assert retired.json()["status"] == "retired", retired.json()
    assert http.get(f"/api/tenant-plans/{plan_id}", headers=auth).json()["is_active"] is False
    print("  ok  a plan that has been sold is retired rather than destroyed")

    # A rival cannot book against Acme's client or plan even with real ids.
    stolen = http.post("/api/placements/", headers=rival_auth, json={
        "content_id": ad.id, "client_id": acme_client_id, "plan_id": plan_id,
        "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=5)).isoformat(),
        "targets": [],
    })
    assert stolen.status_code == 404, stolen.text
    print("  ok  a rival cannot book against another tenant's client or plan")

    # Deleting a client leaves the booking standing; billing history is not theirs to erase.
    assert http.delete(f"/api/clients/{acme_client_id}", headers=auth).status_code == 200
    survivor = http.get("/api/placements/", headers=auth).json()[0]
    assert survivor["client"] is None, survivor
    assert survivor["advertiser"] == "BrightMart", survivor
    print("  ok  deleting a client keeps the booking, still named by advertiser")

    # --- branding: a tenant uploads their own logo -------------------------------------
    # This is a commercial product: the report is a document a tenant hands to a paying
    # advertiser, so the masthead has to be theirs, not the workspace name someone typed at
    # signup. Exercised through the real endpoint rather than by setting the column.
    import base64

    # Smallest valid PNG. The endpoint checks the extension and the size, not the pixels.
    PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )

    before = http.get("/api/branding/", headers=auth).json()
    # No branding set: falls back to the workspace name, so a tenant that configures nothing
    # loses nothing.
    assert before["effective_name"] == "Acme", before
    assert before["logo_url"] is None, before

    up = http.post("/api/branding/logo", headers=auth, files={"file": ("logo.png", PNG, "image/png")})
    assert up.status_code == 200, up.text
    assert up.json()["logo_url"], up.json()
    print("  ok  a tenant can upload their own logo")

    # It must land in THAT tenant's own storage folder, beside their media -- not in a
    # shared bucket root where two tenants' marks could collide.
    db.expire_all()
    acme_row = db.query(models.Organization).filter(models.Organization.slug == "acme").one()
    from backend.media_urls import storage_prefix

    assert f"{storage_prefix(acme_row)}/branding/" in acme_row.logo_url, acme_row.logo_url
    print("  ok  the logo is stored under that tenant's own prefix")

    named = http.put("/api/branding/", headers=auth,
                     json={"brand_name": "AdVision Digital Signage", "brand_color": "#0b1437"})
    assert named.status_code == 200, named.text
    assert named.json()["effective_name"] == "AdVision Digital Signage", named.json()

    # A colour that is not one must be refused at the edge: it is written into a PDF colour
    # and into inline style on the dashboard.
    assert http.put("/api/branding/", headers=auth, json={"brand_color": "red; drop"}).status_code == 422
    print("  ok  brand name is applied and a malformed colour is refused")

    # Only images, and no SVG: /uploads is served from the API's own origin and an SVG can
    # carry a script.
    assert http.post("/api/branding/logo", headers=auth,
                     files={"file": ("mark.svg", b"<svg/>", "image/svg+xml")}).status_code == 415
    assert http.post("/api/branding/logo", headers=auth,
                     files={"file": ("big.png", b"x" * (3 * 1024 * 1024), "image/png")}).status_code == 413
    print("  ok  an SVG and an oversized file are both refused")

    # One tenant's branding is not another's.
    theirs = http.get("/api/branding/", headers=rival_auth).json()
    assert theirs["effective_name"] == "Rival", theirs
    assert theirs["logo_url"] is None, theirs
    print("  ok  branding is per tenant, not shared")

    gone = http.delete("/api/branding/logo", headers=auth)
    assert gone.status_code == 200 and gone.json()["logo_url"] is None, gone.text
    # The name survives removing the logo -- they are separate settings.
    assert gone.json()["effective_name"] == "AdVision Digital Signage", gone.json()
    print("  ok  removing the logo keeps the brand name")

    # --- a plan's screen count actually binds ------------------------------------------
    # "5 TVs / 30 days" was decoration: the 30 days were enforced by the player, the 5 TVs
    # were not, so a plan could be oversold without anything objecting.
    small_plan = http.post("/api/tenant-plans/", headers=auth, json={
        "name": "Basic", "duration_days": 30, "max_locations": 2,
        "ad_slots": 1, "price_paise": 500000, "support_tier": "Basic Support",
    }).json()

    fleet = [models.Screen(organization_id=acme.id, name=f"TV {n}", status="online") for n in range(4)]
    db.add_all(fleet); db.commit()

    within = http.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "client_id": second.json()["id"], "plan_id": small_plan["id"],
        "starts_at": now.isoformat(),
        "targets": [{"screen_id": fleet[0].id}, {"screen_id": fleet[1].id}],
    })
    assert within.status_code == 201, within.text

    # The third screen is one past what the client paid for.
    third = http.post(f"/api/placements/{within.json()['id']}/targets", headers=auth,
                      json={"screen_id": fleet[2].id})
    assert third.status_code == 409, third.text
    assert "Basic" in third.json()["detail"] and "2 screens" in third.json()["detail"], third.json()
    print("  ok  a screen past the plan's count is refused, naming the plan and the limit")

    # Booking straight past the limit in one request is refused whole, not half-created.
    over = http.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "plan_id": small_plan["id"], "advertiser": "Too Big",
        "starts_at": now.isoformat(),
        "targets": [{"screen_id": s.id} for s in fleet],
    })
    assert over.status_code == 409, over.text
    assert not [p for p in http.get("/api/placements/", headers=auth).json() if p["advertiser"] == "Too Big"]
    print("  ok  a booking that breaches its plan is refused whole")

    # THE case that makes counting targets useless: one group target carries four screens.
    # Counting target rows would see "1" and wave it past a two-screen plan.
    big_group = models.ScreenGroup(organization_id=acme.id, name="Mall Wing")
    db.add(big_group); db.commit()
    for screen_row in fleet:
        screen_row.group_id = big_group.id
    db.commit()

    by_group = http.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "plan_id": small_plan["id"], "advertiser": "Group Sneak",
        "starts_at": now.isoformat(), "targets": [{"group_id": big_group.id}],
    })
    assert by_group.status_code == 409, (
        "a group of four screens was accepted on a two-screen plan -- the limit is being "
        "counted on target rows rather than on the screens they expand to"
    )
    print("  ok  a group is counted by the screens it expands to, not as one target")

    # A plan of 0 means unlimited, matching how max_ad_slots already reads elsewhere.
    unlimited = http.post("/api/tenant-plans/", headers=auth, json={
        "name": "Unlimited", "duration_days": 30, "max_locations": 0,
        "ad_slots": 1, "price_paise": 100, "support_tier": "Basic",
    })
    assert unlimited.status_code == 422, "max_locations must be at least 1 in the schema"
    print("  ok  a plan cannot be created with a meaningless zero screen count")

    print("tenant plans: all checks passed")
finally:
    try:
        if db: db.close()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass
    cur = admin.cursor()
    cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{SCRATCH}'")
    cur.execute(f'DROP DATABASE IF EXISTS "{SCRATCH}"')
    admin.close()
