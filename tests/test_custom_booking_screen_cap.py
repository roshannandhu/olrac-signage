"""A booking sold without a package can still be sold a number of screens.

Run directly:  python tests/test_custom_booking_screen_cap.py

A package caps locations (TenantPlan.max_locations) and ensure_plan_locations refuses the
screen that breaches it. A CUSTOM booking -- negotiated price, no package -- had no such
number anywhere, so "three screens for 40,000" was a deal nothing could hold the tenant to:
the fourth screen went on from the booking page, from Add places, or from the playlist
builder, and the client silently received more than they bought.

What this pins down:

  1. A custom booking created over its own cap is refused OUTRIGHT, not half-created.
  2. Adding a place later is refused by the same cap -- adding one at a time was the way
     straight past every limit this codebase has ever had.
  3. 0 still means unlimited, so every booking sold before this behaves exactly as it did.
  4. Change plan re-cuts the cap: raising it lets the screen on, and lowering it below the
     screens the booking already runs on is refused rather than leaving a booking in breach.
  5. A package overrides the custom figure, so moving onto a plan is judged on the plan.
"""

import os
import sys
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-screencap-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "screencap.db"

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
os.environ["SECRET_KEY"] = "screencap-test-secret-not-for-production"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def build_workspace(db, unique, screen_labels=("a", "b", "c", "d")):
    org = models.Organization(
        name=f"Caps {unique}", slug=f"caps-{unique}", status="active", max_screens=0,
    )
    db.add(org)
    db.flush()
    db.add(models.User(
        organization_id=org.id, username=f"owner-{unique}", email=f"owner-{unique}@x.com",
        role="owner", is_active=True, hashed_password=get_password_hash("ownerpass1"),
    ))
    content = models.Content(
        organization_id=org.id, name="Moolans Grand Store", type="image",
        file_url="s3://x/creative.png", status="ready",
    )
    db.add(content)
    screens = {}
    for label in screen_labels:
        screen = models.Screen(
            organization_id=org.id, device_id=f"{label}-{unique}", name=f"Screen {label.upper()}",
            status="online", approved_at=models.utcnow(), last_seen=models.utcnow(),
        )
        db.add(screen)
        db.flush()
        screens[label] = screen.id
    db.flush()
    return org.id, f"owner-{unique}", content.id, screens


def sell(client, headers, content_id, starts_at, *, targets, max_locations=0, plan_id=None):
    body = {
        "content_id": content_id,
        "advertiser": "Moolans Grand Store",
        "price_paise": 4_000_000,
        "max_locations": max_locations,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": screen_id} for screen_id in targets],
    }
    if plan_id is not None:
        body["plan_id"] = plan_id
    return client.post("/api/placements/", headers=headers, json=body)


def run() -> None:
    client = TestClient(app)
    client.__enter__()
    try:
        starts_at = models.utcnow()

        # 1. Over its own cap at the point of sale: refused whole.
        db = database.SessionLocal()
        unique = uuid.uuid4().hex[:8]
        _, username, content_id, screens = build_workspace(db, unique)
        db.commit()
        db.close()
        headers = {"Authorization": f"Bearer {create_access_token({'sub': username})}"}

        over = sell(
            client, headers, content_id, starts_at,
            targets=[screens["a"], screens["b"], screens["c"]], max_locations=2,
        )
        check(over.status_code == 409, f"3 screens on a 2-screen deal should be 409, got {over.status_code} {over.text}")
        db = database.SessionLocal()
        try:
            left_behind = db.query(models.AdPlacement).filter(
                models.AdPlacement.content_id == content_id
            ).count()
            check(left_behind == 0, "a refused booking must not leave a half-created row behind")
        finally:
            db.close()

        # Within the cap: sold, and the cap is reported back.
        sold = sell(
            client, headers, content_id, starts_at,
            targets=[screens["a"], screens["b"]], max_locations=2,
        )
        check(sold.status_code == 201, f"2 screens on a 2-screen deal should sell: {sold.text}")
        if sold.status_code != 201:
            return
        placement = sold.json()
        placement_id = placement["id"]
        check(placement["max_locations"] == 2, f"booking should carry its cap, got {placement['max_locations']}")
        check(
            placement["plan_max_locations"] == 2,
            "the cap in force on a custom booking is its own, so the dashboard can show "
            f"'2 of 2'; got {placement['plan_max_locations']}",
        )
        check(placement["screens_used"] == 2, f"2 screens used, got {placement['screens_used']}")

        # 2. Adding one at a time is the way past every limit, so it is checked there too.
        third = client.post(
            f"/api/placements/{placement_id}/targets",
            headers=headers, json={"screen_id": screens["c"]},
        )
        check(third.status_code == 409, f"a 3rd screen on a 2-screen deal should be 409, got {third.status_code}")
        check(
            "Change plan" in third.text,
            f"the refusal should say where the cap is raised; got {third.text}",
        )

        # 4. Change plan raises it -- and the screen then goes on.
        raised = client.post(
            f"/api/placements/{placement_id}/change-plan",
            headers=headers, json={"plan_id": None, "max_locations": 3},
        )
        check(raised.status_code == 200, f"raising the cap should succeed: {raised.text}")
        check(
            raised.status_code != 200 or raised.json()["max_locations"] == 3,
            "the raised cap should be stored",
        )
        third_again = client.post(
            f"/api/placements/{placement_id}/targets",
            headers=headers, json={"screen_id": screens["c"]},
        )
        check(third_again.status_code == 201, f"the 3rd screen should now go on: {third_again.text}")

        # ...and cannot be cut below what the booking already delivers, which would leave it
        # in breach with nothing able to say so.
        cut = client.post(
            f"/api/placements/{placement_id}/change-plan",
            headers=headers, json={"plan_id": None, "max_locations": 2},
        )
        check(cut.status_code == 409, f"cutting the cap under the screens in use should be 409, got {cut.status_code}")
        still = client.get(f"/api/placements/?content_id={content_id}", headers=headers)
        check(
            still.status_code == 200 and still.json()[0]["max_locations"] == 3,
            "a refused cut must leave the cap as it was",
        )

        # 3. 0 is unlimited, exactly as every booking sold before this carried.
        db = database.SessionLocal()
        unique2 = uuid.uuid4().hex[:8]
        _, username2, content2, screens2 = build_workspace(db, unique2)
        db.commit()
        db.close()
        headers2 = {"Authorization": f"Bearer {create_access_token({'sub': username2})}"}
        uncapped = sell(
            client, headers2, content2, starts_at,
            targets=[screens2["a"], screens2["b"], screens2["c"], screens2["d"]],
        )
        check(uncapped.status_code == 201, f"an uncapped custom booking should sell any number: {uncapped.text}")
        if uncapped.status_code == 201:
            body = uncapped.json()
            check(body["plan_max_locations"] == 0, "0 means nothing caps it")
            check(body["screens_unused"] == 0, "an uncapped booking has no unused allowance")

        # 5. A package overrides the booking's own figure, in both directions.
        db = database.SessionLocal()
        unique3 = uuid.uuid4().hex[:8]
        org3, username3, content3, screens3 = build_workspace(db, unique3)
        plan = models.TenantPlan(
            organization_id=org3, name="Two Screens", price_paise=1_000_000,
            duration_days=30, max_locations=2, ad_slots=1, is_active=True,
        )
        db.add(plan)
        db.flush()
        plan_id = plan.id
        db.commit()
        db.close()
        headers3 = {"Authorization": f"Bearer {create_access_token({'sub': username3})}"}

        # The booking names a generous custom figure AND a two-screen package. The package
        # is what was sold, so the package is what binds.
        on_plan = sell(
            client, headers3, content3, starts_at,
            targets=[screens3["a"], screens3["b"], screens3["c"]],
            max_locations=99, plan_id=plan_id,
        )
        check(
            on_plan.status_code == 409,
            f"a package must override a laxer custom figure, got {on_plan.status_code} {on_plan.text}",
        )
        check(
            on_plan.status_code != 409 or "Two Screens" in on_plan.text,
            f"the refusal should name the plan that caused it; got {on_plan.text}",
        )
    finally:
        client.__exit__(None, None, None)


if __name__ == "__main__":
    run()
    if failures:
        print("CUSTOM BOOKING SCREEN CAP FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("custom booking screen cap: a negotiated deal is held to the screens it sold")
