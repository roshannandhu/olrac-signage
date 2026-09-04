"""The client-ad editor must obey the same rules as the bookings tab.

    python tests/test_client_ad_editor.py

`PUT /content/{id}/client-ad` is the modal behind "Edit client & ad details". It reaches
_place and _unplace directly, and it used to be a second implementation of the booking
logic rather than a caller of it -- so every guard that surrounds those two helpers
everywhere else had been missed on this one path.

What this pins down:

  1. Correcting a location's run length moves the PLAYLIST ITEM, not just the target row.
     The player enforces PlaylistItem.start_at/end_at; nothing here pushed the change onto
     it, so shortening a booking from 30 days to 10 updated the dashboard and the invoice
     while the TV kept playing for the full 30. The playlist must also be bumped, or /sync
     answers 204 and the screen never hears about it.
  2. The plan's location cap counts screens reached through a GROUP target. Passing an
     empty "existing" set counted a ten-screen group as nothing.
  3. "Campaign Notes" belongs to the booking. Writing it to the client as well meant a
     per-campaign reference replaced the client's permanent note.
  4. An explicit null clears the plan. Testing the resolved object meant it could be moved
     but never removed.
  5. Blank names and out-of-range day counts are refused here exactly as they are on the
     placements routes.
  6. Booking a screen that inherits its loop from a group keeps that loop AND does not
     hand the advert to the rest of the group.
"""

import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

TEST_DB = f"olrac_test_adeditor_{uuid.uuid4().hex[:8]}"
admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin.cursor().execute(f'CREATE DATABASE "{TEST_DB}" OWNER olrac')

os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{TEST_DB}"
os.environ["SECRET_KEY"] = "adeditor-test-secret-not-for-production"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

failures: list[str] = []
_marked = 0


def check(condition: bool, message: str) -> None:
    if condition:
        return
    failures.append(message)
    print(f"  FAIL  {message}")


def ok(message: str) -> None:
    """Report a passing block. Silent if a check in it already failed, so the output
    cannot read 'FAIL x / ok x' for the same thing."""
    global _marked
    if len(failures) > _marked:
        _marked = len(failures)
        return
    print(f"  ok    {message}")


def days_between(start, end) -> int:
    return round((end - start).total_seconds() / 86400)


def build_workspace(db, unique):
    org = models.Organization(
        name=f"Ads {unique}", slug=f"ads-{unique}", status="active",
        max_screens=0, max_ad_slots=0,
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
    plan = models.TenantPlan(
        organization_id=org.id, name="Standard", duration_days=30,
        max_locations=2, ad_slots=5, price_paise=2_500_000,
    )
    db.add(plan)
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
    return org.id, owner.username, content.id, plan.id, screens


def run() -> None:
    client = TestClient(app)
    client.__enter__()
    try:
        db = database.SessionLocal()
        unique = uuid.uuid4().hex[:8]
        org_id, username, content_id, plan_id, screens = build_workspace(db, unique)
        db.commit()
        db.close()
        headers = {"Authorization": f"Bearer {create_access_token({'sub': username})}"}

        # Sell it through the editor: two locations, 30 days each.
        first = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "client_email": "buyer@prakrithi.example",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"], screens["shop"]],
            "screen_days": {str(screens["mall"]): 30, str(screens["shop"]): 30},
            "notes": "PO-4471, agreed over the phone",
        })
        check(first.status_code == 200, f"initial sale failed: {first.status_code} {first.text}")
        if first.status_code != 200:
            return
        ok("the editor sells a booking across two locations")

        # 1. THE BUG. Correct the shop from 30 days to 10 and the playlist item must move.
        db = database.SessionLocal()
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        shop_target = next(t for t in placement.targets if t.screen_id == screens["shop"])
        item_id = shop_target.playlist_item_id
        playlist_id = db.query(models.PlaylistItem).filter(
            models.PlaylistItem.id == item_id).one().playlist_id
        before_bump = db.query(models.Playlist).filter(
            models.Playlist.id == playlist_id).one().updated_at
        db.close()

        corrected = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"], screens["shop"]],
            "screen_days": {str(screens["mall"]): 30, str(screens["shop"]): 10},
        })
        check(corrected.status_code == 200, f"correction failed: {corrected.text}")

        db = database.SessionLocal()
        item = db.query(models.PlaylistItem).filter(models.PlaylistItem.id == item_id).one()
        target = db.query(models.AdPlacementTarget).filter(
            models.AdPlacementTarget.playlist_item_id == item_id).one()
        after_bump = db.query(models.Playlist).filter(
            models.Playlist.id == playlist_id).one().updated_at
        sold = days_between(target.starts_at, target.ends_at)
        delivered = days_between(item.start_at, item.end_at)
        check(sold == 10, f"the booking records {sold} days, expected 10")
        check(delivered == 10,
              f"the TV would play for {delivered} days after selling 10 -- the playlist "
              "item never moved")
        check(after_bump > before_bump,
              "the playlist was not bumped, so /sync answers 204 and the screen never "
              "learns the window changed")
        db.close()
        ok("correcting a location's days moves the playlist item and bumps the playlist")

        # 1b. A client that does not send screen_days must not wipe the ones on file.
        #     The dashboard's campaigns page was exactly such a client: it built its
        #     payload from a placement, had no screen_days to include, and so cleared every
        #     location's window -- through to the playlist items the players enforce.
        db = database.SessionLocal()
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        windows_before = {
            t.screen_id: (t.starts_at, t.ends_at) for t in placement.targets if t.screen_id
        }
        items_before = {
            t.screen_id: db.query(models.PlaylistItem).filter(
                models.PlaylistItem.id == t.playlist_item_id).one()
            for t in placement.targets if t.playlist_item_id
        }
        items_before = {k: (v.start_at, v.end_at) for k, v in items_before.items()}
        db.close()

        unaware = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "screen_ids": [screens["mall"], screens["shop"]],
            "screen_days": {},
        })
        check(unaware.status_code == 200, f"unaware save failed: {unaware.text}")

        db = database.SessionLocal()
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        windows_after = {
            t.screen_id: (t.starts_at, t.ends_at) for t in placement.targets if t.screen_id
        }
        items_after = {
            t.screen_id: db.query(models.PlaylistItem).filter(
                models.PlaylistItem.id == t.playlist_item_id).one()
            for t in placement.targets if t.playlist_item_id
        }
        items_after = {k: (v.start_at, v.end_at) for k, v in items_after.items()}
        db.close()
        check(windows_after == windows_before,
              "an empty screen_days map wiped the per-location windows on the booking")
        check(items_after == items_before,
              "an empty screen_days map rewrote the playlist items the players enforce")
        ok("a client that omits screen_days leaves the sold windows alone")

        # 1c. Clearing is still possible, but has to be asked for.
        cleared = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "screen_ids": [screens["mall"], screens["shop"]],
            "clear_screen_days": True,
        })
        check(cleared.status_code == 200, f"explicit clear failed: {cleared.text}")
        db = database.SessionLocal()
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        still_set = [t.screen_id for t in placement.targets if t.screen_id and t.ends_at]
        db.close()
        check(not still_set,
              f"clear_screen_days left windows on screens {still_set}")
        ok("clear_screen_days still resets every location to the booking window")

        # 2. Campaign notes must not touch the client's own record.
        db = database.SessionLocal()
        client_row = db.query(models.Client).filter(
            models.Client.organization_id == org_id).one()
        check(client_row.notes is None,
              f"the campaign note leaked onto the client record: {client_row.notes!r}")
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        check(placement.notes == "PO-4471, agreed over the phone",
              f"the booking lost its note: {placement.notes!r}")
        db.close()
        ok("a campaign note stays on the booking and off the client")

        # 3. An explicit null clears the plan; omitting the key leaves it alone.
        kept = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
        })
        check(kept.json().get("plan_id") == plan_id,
              "omitting plan_id wrongly cleared the plan")
        cleared = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots", "plan_id": None,
        })
        check(cleared.json().get("plan_id") is None,
              f"plan_id null did not clear the plan: {cleared.json().get('plan_id')}")
        ok("the plan can be cleared, and is not cleared by accident")

        # 4. Validation parity with the placements routes.
        blank = client.put(f"/api/content/{content_id}/client-ad", headers=headers,
                           json={"client_name": "   "})
        check(blank.status_code == 422, f"a blank client name was accepted: {blank.status_code}")
        huge = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "screen_ids": [screens["mall"]],
            "screen_days": {str(screens["mall"]): 9999},
        })
        check(huge.status_code == 422, f"9999 days was accepted: {huge.status_code}")
        zero = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "screen_ids": [screens["mall"]],
            "screen_days": {str(screens["mall"]): 0},
        })
        check(zero.status_code == 422, f"0 days was accepted: {zero.status_code}")
        ok("blank names and out-of-range day counts are refused")

        # 5. The plan cap counts screens reached through a group target.
        db = database.SessionLocal()
        group = models.ScreenGroup(organization_id=org_id, name="Airport concourse")
        db.add(group)
        db.flush()
        group_id = group.id
        airport = db.query(models.Screen).filter(
            models.Screen.id == screens["airport"]).one()
        airport.group_id = group_id
        placement = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == content_id).one()
        placement_id = placement.id
        for target in list(placement.targets):
            db.delete(target)
        db.commit()
        db.close()

        added = client.post(f"/api/placements/{placement_id}/targets", headers=headers,
                            json={"group_id": group_id})
        check(added.status_code == 201, f"group target failed: {added.status_code} {added.text}")

        # The plan allows 2 locations. The group already contributes 1 (the airport), so
        # asking for both remaining screens is 3 and must be refused.
        over = client.put(f"/api/content/{content_id}/client-ad", headers=headers, json={
            "client_name": "Prakrithi Roots",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"], screens["shop"]],
        })
        check(over.status_code == 409,
              f"the plan cap ignored the group's screen: {over.status_code} {over.text}")
        ok("the plan's location cap counts screens inside a group target")

        # 6. Booking a screen that inherits its loop from a group keeps that loop, and the
        #    rest of the group does not get the advert.
        db = database.SessionLocal()
        venue_loop = models.Playlist(organization_id=org_id, name="Venue loop")
        db.add(venue_loop)
        db.flush()
        house_ad = models.Content(
            organization_id=org_id, name="House promo", type="image",
            file_url="s3://x/house.png", status="ready",
        )
        db.add(house_ad)
        db.flush()
        for order in range(3):
            db.add(models.PlaylistItem(
                playlist_id=venue_loop.id, content_id=house_ad.id, duration=10, order=order))
        venue_group = models.ScreenGroup(
            organization_id=org_id, name="Venue", playlist_id=venue_loop.id)
        db.add(venue_group)
        db.flush()
        venue_group_id, venue_loop_id = venue_group.id, venue_loop.id
        inheritors = {}
        for label in ("booked", "sibling"):
            screen = models.Screen(
                organization_id=org_id, device_id=f"{label}-{unique}", name=f"{label} TV",
                status="online", group_id=venue_group_id,
                approved_at=models.utcnow(), last_seen=models.utcnow(),
            )
            db.add(screen)
            db.flush()
            inheritors[label] = screen.id
        db.commit()
        booked_id, sibling_id = inheritors["booked"], inheritors["sibling"]
        check(db.query(models.Screen).filter(models.Screen.id == booked_id).one()
              .resolve_playlist_id() == venue_loop_id,
              "fixture is wrong: the screen does not inherit the venue loop")
        db.close()

        solo = models.utcnow()
        booking = client.post("/api/placements/", headers=headers, json={
            "content_id": content_id, "advertiser": "Prakrithi Roots", "price_paise": 100_000,
            "starts_at": solo.isoformat(), "ends_at": (solo + timedelta(days=7)).isoformat(),
            "targets": [{"screen_id": booked_id}],
        })
        check(booking.status_code == 201, f"solo booking failed: {booking.text}")

        db = database.SessionLocal()
        booked = db.query(models.Screen).filter(models.Screen.id == booked_id).one()
        sibling = db.query(models.Screen).filter(models.Screen.id == sibling_id).one()
        own_items = db.query(models.PlaylistItem).filter(
            models.PlaylistItem.playlist_id == booked.playlist_id).all()
        venue_items = db.query(models.PlaylistItem).filter(
            models.PlaylistItem.playlist_id == venue_loop_id).all()

        check(booked.playlist_id is not None and booked.playlist_id != venue_loop_id,
              "the booked screen was not given its own playlist")
        check(len(own_items) == 4,
              f"the booked screen plays {len(own_items)} items, expected the venue's 3 "
              "plus the advert")
        check(any(i.content_id == content_id for i in own_items),
              "the advert never reached the booked screen")
        check(len(venue_items) == 3 and all(i.content_id != content_id for i in venue_items),
              "the advert leaked into the venue loop, so every screen in the group plays it")
        check(sibling.resolve_playlist_id() == venue_loop_id,
              "a sibling screen lost its inherited loop")
        db.close()
        ok("booking one inheriting screen keeps its loop and spares the rest of the group")

        # 7. THE BUG. A client who does not want a package. The editor offered plans and
        # nothing else: no plan meant no price, because a price was only ever COPIED from a
        # plan. The sale was recorded at zero and the ad's own page read "Contract value
        # Rs.0 -- Unpaid", with no field anywhere to correct it.
        db = database.SessionLocal()
        custom_content = models.Content(
            organization_id=org_id, name="Custom Deal", type="image",
            file_url="s3://x/custom.png", status="ready",
        )
        db.add(custom_content)
        db.commit()
        custom_id = custom_content.id
        db.close()

        sold_custom = client.put(f"/api/content/{custom_id}/client-ad", headers=headers, json={
            "client_name": "Moolans Textiles",
            "price_paise": 4_000_000,
            "screen_ids": [screens["airport"]],
        })
        check(sold_custom.status_code == 200, f"custom sale failed: {sold_custom.text}")

        db = database.SessionLocal()
        custom = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == custom_id).one()
        check(custom.price_paise == 4_000_000,
              f"a booking sold on no plan is billed {custom.price_paise}, expected "
              "4000000 -- the agreed figure was thrown away and the sale recorded free")
        check(custom.plan_id is None, "a custom sale was silently attached to a plan")
        db.close()
        ok("a booking sold on no plan keeps the price the operator agreed")

        # The plan is still the default when no figure is typed, so selling a package is
        # unchanged -- the new field adds a way to state a price, it does not require one.
        db = database.SessionLocal()
        package_content = models.Content(
            organization_id=org_id, name="Package Deal", type="image",
            file_url="s3://x/package.png", status="ready",
        )
        db.add(package_content)
        db.commit()
        package_id = package_content.id
        db.close()

        client.put(f"/api/content/{package_id}/client-ad", headers=headers, json={
            "client_name": "Package Buyer",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"]],
        })
        db = database.SessionLocal()
        from_plan = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == package_id).one()
        check(from_plan.price_paise == 2_500_000,
              f"a plan sale is billed {from_plan.price_paise}, expected the plan's 2500000")
        db.close()
        ok("a plan still fills the price in when the operator types none")

        # The guard that makes the field safe. An ordinary edit -- a corrected name, a phone
        # number -- sends no price, and the agreed figure has to survive it. Without this,
        # an editable price is just the silent rebill the plan-copy rule already forbids.
        client.put(f"/api/content/{custom_id}/client-ad", headers=headers, json={
            "client_name": "Moolans Textiles Pvt Ltd",
            "screen_ids": [screens["airport"]],
        })
        db = database.SessionLocal()
        untouched = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == custom_id).one()
        check(untouched.price_paise == 4_000_000,
              f"renaming the client rebilled the booking to {untouched.price_paise}")
        db.close()

        client.put(f"/api/content/{custom_id}/client-ad", headers=headers, json={
            "client_name": "Moolans Textiles Pvt Ltd",
            "price_paise": 3_500_000,
            "screen_ids": [screens["airport"]],
        })
        db = database.SessionLocal()
        recorrected = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == custom_id).one()
        check(recorrected.price_paise == 3_500_000,
              f"an explicitly corrected price did not stick: {recorrected.price_paise}")
        db.close()
        ok("only an explicit figure changes a price; an ordinary edit leaves it alone")

        # 8. Going custom is what lifts the location cap, and the cap is real until it is.
        # Both halves matter together: a third screen must be refused while the booking is
        # on a two-location plan, and allowed the moment it is moved off one. Checking only
        # the second would pass just as well if the cap had been switched off altogether.
        #
        # Its own asset, because `content_id` above now carries more than one booking and
        # the editor always edits the latest.
        db = database.SessionLocal()
        freed_content = models.Content(
            organization_id=org_id, name="Outgrew The Plan", type="image",
            file_url="s3://x/outgrew.png", status="ready",
        )
        db.add(freed_content)
        db.commit()
        freed_id = freed_content.id
        db.close()

        # Sold on the plan, filling both of its two locations.
        on_plan = client.put(f"/api/content/{freed_id}/client-ad", headers=headers, json={
            "client_name": "Outgrew Ltd",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"], screens["shop"]],
        })
        check(on_plan.status_code == 200, f"plan sale failed: {on_plan.text}")

        # A third screen while still ON the plan is a real breach and must stay refused --
        # otherwise the check below proves only that the cap was switched off.
        breach = client.put(f"/api/content/{freed_id}/client-ad", headers=headers, json={
            "client_name": "Outgrew Ltd",
            "plan_id": plan_id,
            "screen_ids": [screens["mall"], screens["shop"], screens["airport"]],
        })
        check(breach.status_code == 409,
              f"a third screen on a two-location plan was allowed: {breach.status_code}")

        # The same third screen, off the plan and on an agreed figure, is the sale the
        # operator is actually making.
        off_plan = client.put(f"/api/content/{freed_id}/client-ad", headers=headers, json={
            "client_name": "Outgrew Ltd",
            "plan_id": None,
            "price_paise": 6_000_000,
            "screen_ids": [screens["mall"], screens["shop"], screens["airport"]],
        })
        check(off_plan.status_code == 200,
              f"going custom was refused by the cap of the plan it left: {off_plan.text}")

        db = database.SessionLocal()
        freed = db.query(models.AdPlacement).filter(
            models.AdPlacement.content_id == freed_id).order_by(
            models.AdPlacement.id.desc()).first()
        reached = {t.screen_id for t in freed.targets if t.screen_id}
        check(freed.plan_id is None, "the plan was not cleared")
        check(freed.price_paise == 6_000_000,
              f"the freed booking is billed {freed.price_paise}, expected 6000000")
        check(len(reached) == 3,
              f"the custom booking reaches {len(reached)} screens, expected all 3")
        db.close()
        ok("a booking taken off a plan is no longer bound by that plan's location cap")

    finally:
        client.__exit__(None, None, None)


if __name__ == "__main__":
    try:
        run()
    finally:
        try:
            database.engine.dispose()
        except Exception:
            pass
        cur = admin.cursor()
        cur.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
            (TEST_DB,),
        )
        cur.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
        admin.close()

    if failures:
        print(f"\nclient-ad editor: {len(failures)} check(s) failed")
        sys.exit(1)
    print("\nclient-ad editor: all checks passed")
