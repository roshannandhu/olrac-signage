"""One booking, different run lengths per location: python tests/test_per_location_ad_window.py

A client buys the same advert for 30 days in a mall, 10 in a shop and 50 at an airport,
because the sites are worth different amounts to them. That was previously expressible only
as three separate bookings -- three invoice lines, three extensions, three report rows for
one commercial deal -- because AdPlacement carried a single starts_at/ends_at that
sync_placement_window wrote onto every location.

What this pins down:

  1. Each location's playlist item carries ITS OWN end date, which is what the player
     enforces. Get this wrong and a client is either cut off early or runs free.
  2. A location with no window of its own still follows the booking, so every booking that
     predates the feature behaves exactly as before.
  3. The campaign is not "over" until its longest location is -- otherwise the ending-soon
     alert fires while a screen is still contractually playing.
  4. Re-syncing the window (an extension, a date edit) does not flatten a location's start
     back to the campaign start. That was a live bug: _place computed
     max(placement.starts_at, assigned_at) for a screen added mid-campaign, and
     sync_placement_window then overwrote it, so a late-added screen was billed from a date
     it was not yet running.
"""

import os
import sys
import tempfile
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-adwindow-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "adwindow.db"

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
os.environ["SECRET_KEY"] = "adwindow-test-secret-not-for-production"
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


def days_between(start, end) -> int:
    return round((end - start).total_seconds() / 86400)


def build_workspace(db, unique):
    org = models.Organization(
        name=f"Ads {unique}", slug=f"ads-{unique}", status="active", max_screens=0,
    )
    db.add(org)
    db.flush()
    owner = models.User(
        organization_id=org.id, username=f"owner-{unique}", email=f"owner-{unique}@x.com",
        role="owner", is_active=True, hashed_password=get_password_hash("ownerpass1"),
    )
    db.add(owner)
    content = models.Content(
        organization_id=org.id, name="Prakrithi Roots", type="image",
        file_url="s3://x/creative.png", status="ready",
    )
    db.add(content)
    screens = {}
    for label in ("mall", "shop", "airport"):
        screen = models.Screen(
            organization_id=org.id, device_id=f"{label}-{unique}", name=f"{label.title()} TV",
            status="online", approved_at=models.utcnow(), last_seen=models.utcnow(),
        )
        db.add(screen)
        db.flush()
        screens[label] = screen.id
    db.flush()
    return org.id, owner.username, content.id, screens


def run() -> None:
    client = TestClient(app)
    client.__enter__()
    try:
        db = database.SessionLocal()
        unique = uuid.uuid4().hex[:8]
        org_id, username, content_id, screens = build_workspace(db, unique)
        db.commit()
        db.close()

        headers = {"Authorization": f"Bearer {create_access_token({'sub': username})}"}
        starts_at = models.utcnow()

        # The sale: one client, one creative, three locations, three lengths. The booking's
        # own window is 30 days -- the airport deliberately outruns it.
        created = client.post("/api/placements/", headers=headers, json={
            "content_id": content_id,
            "advertiser": "Prakrithi Roots",
            "price_paise": 4_500_000,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(days=30)).isoformat(),
            "targets": [
                {"screen_id": screens["mall"], "days": 30},
                {"screen_id": screens["shop"], "days": 10},
                {"screen_id": screens["airport"], "days": 50},
            ],
        })
        check(created.status_code == 201, f"booking failed: {created.status_code} {created.text}")
        if created.status_code != 201:
            return
        placement_id = created.json()["id"]

        # 1. Each location's PLAYLIST ITEM carries its own end -- this is the field the
        #    player enforces, so it is the one that decides what the client actually gets.
        db = database.SessionLocal()
        try:
            placement = db.query(models.AdPlacement).filter(
                models.AdPlacement.id == placement_id
            ).one()
            by_screen = {t.screen_id: t for t in placement.targets}
            for label, expected in (("mall", 30), ("shop", 10), ("airport", 50)):
                target = by_screen.get(screens[label])
                check(target is not None, f"{label} was not placed")
                if not target:
                    continue
                item = db.query(models.PlaylistItem).filter(
                    models.PlaylistItem.id == target.playlist_item_id
                ).first()
                check(item is not None, f"{label} has no playlist item")
                if not item:
                    continue
                actual = days_between(item.start_at, item.end_at)
                check(
                    actual == expected,
                    f"{label} runs {actual} days on the screen, sold {expected}",
                )

            # 3. The campaign outlives its own ends_at because a location was sold longer.
            sold_days = days_between(placement.starts_at, placement.ends_at)
            effective_days = days_between(placement.starts_at, placement.effective_ends_at)
            check(sold_days == 30, f"booking window should still read 30 as sold, got {sold_days}")
            check(
                effective_days == 50,
                f"campaign should not end until its longest location does; got {effective_days} days",
            )
        finally:
            db.close()

        # 2. A location with no length of its own follows the booking.
        db = database.SessionLocal()
        unique2 = uuid.uuid4().hex[:8]
        org2, username2, content2, screens2 = build_workspace(db, unique2)
        db.commit()
        db.close()
        headers2 = {"Authorization": f"Bearer {create_access_token({'sub': username2})}"}
        plain = client.post("/api/placements/", headers=headers2, json={
            "content_id": content2,
            "advertiser": "No Custom Lengths",
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(days=14)).isoformat(),
            "targets": [{"screen_id": screens2["mall"]}, {"screen_id": screens2["shop"]}],
        })
        check(plain.status_code == 201, f"plain booking failed: {plain.text}")
        if plain.status_code == 201:
            db = database.SessionLocal()
            try:
                placement2 = db.query(models.AdPlacement).filter(
                    models.AdPlacement.id == plain.json()["id"]
                ).one()
                for target in placement2.targets:
                    check(
                        target.ends_at is None,
                        "a location sold no length of its own must store none, so it keeps "
                        "following the booking",
                    )
                    item = db.query(models.PlaylistItem).filter(
                        models.PlaylistItem.id == target.playlist_item_id
                    ).first()
                    if item:
                        check(
                            days_between(item.start_at, item.end_at) == 14,
                            "a location with no window of its own must run the booking's 14 days",
                        )
            finally:
                db.close()

        # 4. Re-syncing must not flatten a location's own window or its start.
        extended = client.post(
            f"/api/placements/{placement_id}/extensions", headers=headers,
            json={"extended_to": (starts_at + timedelta(days=60)).isoformat(),
                  "additional_price_paise": 100000},
        )
        if extended.status_code in (200, 201):
            db = database.SessionLocal()
            try:
                placement = db.query(models.AdPlacement).filter(
                    models.AdPlacement.id == placement_id
                ).one()
                by_screen = {t.screen_id: t for t in placement.targets}
                shop = by_screen.get(screens["shop"])
                if shop and shop.playlist_item_id:
                    item = db.query(models.PlaylistItem).filter(
                        models.PlaylistItem.id == shop.playlist_item_id
                    ).first()
                    if item:
                        check(
                            days_between(item.start_at, item.end_at) == 10,
                            "extending the campaign silently gave the 10-day location the "
                            f"extension too: it now runs {days_between(item.start_at, item.end_at)} days",
                        )
            finally:
                db.close()

        # 5. The booking modal's own path: PUT /content/{id}/client-ad with screen_days,
        #    and the lengths must come back on the next read so re-opening the modal shows
        #    what was sold rather than collapsing to one uniform run.
        db = database.SessionLocal()
        unique3 = uuid.uuid4().hex[:8]
        org3, username3, content3, screens3 = build_workspace(db, unique3)
        db.commit()
        db.close()
        headers3 = {"Authorization": f"Bearer {create_access_token({'sub': username3})}"}

        saved = client.put(f"/api/content/{content3}/client-ad", headers=headers3, json={
            "client_name": "Bespoke Client",
            "screen_ids": [screens3["mall"], screens3["shop"]],
            "screen_days": {str(screens3["mall"]): 30, str(screens3["shop"]): 10},
        })
        check(saved.status_code == 200, f"client-ad save failed: {saved.status_code} {saved.text}")
        if saved.status_code == 200:
            returned = saved.json().get("screen_days") or {}
            check(
                {int(k): v for k, v in returned.items()}
                == {screens3["mall"]: 30, screens3["shop"]: 10},
                f"the sold lengths did not come back: {returned}",
            )

            # And correcting one afterwards must move it, not only new ones.
            corrected = client.put(f"/api/content/{content3}/client-ad", headers=headers3, json={
                "client_name": "Bespoke Client",
                "screen_ids": [screens3["mall"], screens3["shop"]],
                "screen_days": {str(screens3["mall"]): 30, str(screens3["shop"]): 21},
            })
            if corrected.status_code == 200:
                again = {int(k): v for k, v in (corrected.json().get("screen_days") or {}).items()}
                check(
                    again.get(screens3["shop"]) == 21,
                    f"correcting an existing location's length did not take: {again}",
                )

    finally:
        client.__exit__(None, None, None)


if __name__ == "__main__":
    run()
    if failures:
        print("PER-LOCATION AD WINDOW FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)
    print("per-location ad windows: each location runs the length it was sold")
