"""Selling an advert places it; un-selling one place removes exactly that one.

Throwaway Postgres database — never the live one.
Run directly:  python tests/test_ad_placements.py
"""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_placements_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "placement-test-secret"
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

    org = models.Organization(name="Acme", slug="acme")
    rival = models.Organization(name="Rival", slug="rival")
    db.add_all([org, rival]); db.commit()
    owner = models.User(organization_id=org.id, username="owner@acme.test",
                        hashed_password=get_password_hash("x"), role="owner", is_active=True)
    intruder = models.User(organization_id=rival.id, username="owner@rival.test",
                           hashed_password=get_password_hash("x"), role="owner", is_active=True)
    db.add_all([owner, intruder]); db.commit()

    ad = models.Content(organization_id=org.id, type="video", file_url="/uploads/1/a.mp4",
                        name="Summer Sale", status="ready", duration_ms=30_000)
    db.add(ad); db.commit()

    group = models.ScreenGroup(organization_id=org.id, name="Mall")
    db.add(group); db.commit()
    a = models.Screen(organization_id=org.id, name="Lobby", status="online")
    b = models.Screen(organization_id=org.id, name="Cafe", status="online")
    m1 = models.Screen(organization_id=org.id, name="Mall North", group_id=group.id, status="online")
    m2 = models.Screen(organization_id=org.id, name="Mall South", group_id=group.id, status="online")
    db.add_all([a, b, m1, m2]); db.commit()

    # A hand-made item that must survive every booking operation.
    manual_list = models.Playlist(organization_id=org.id, name="Lobby loop")
    db.add(manual_list); db.commit()
    a.playlist_id = manual_list.id; db.commit()
    manual_item = models.PlaylistItem(playlist_id=manual_list.id, content_id=ad.id, duration=7, order=0)
    db.add(manual_item); db.commit()
    manual_id = manual_item.id

    client = TestClient(app)
    auth = {"Authorization": f"Bearer {create_access_token(data={'sub': owner.username})}"}
    now = models.utcnow()

    def playlist_marker():
        """What sync_tv actually gates the player on. Read fresh: the API wrote it."""
        db.expire_all()
        return db.query(models.Playlist).filter(models.Playlist.id == manual_list.id).one().updated_at

    marker_before_booking = playlist_marker()

    body = {
        "content_id": ad.id, "advertiser": "Pittappillil", "price_paise": 5000000,
        "is_paid": True,
        "starts_at": now.isoformat(), "ends_at": (now + timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": a.id}, {"screen_id": b.id}, {"group_id": group.id}],
    }
    created = client.post("/api/placements/", json=body, headers=auth)
    assert created.status_code == 201, created.text
    placement = created.json()
    assert len(placement["targets"]) == 3, placement["targets"]

    def items():
        db.expire_all()
        return db.query(models.PlaylistItem).filter(models.PlaylistItem.content_id == ad.id).all()

    booked = [i for i in items() if i.id != manual_id]
    assert len(booked) == 3, f"expected one item per place, got {len(booked)}"
    # A video takes its own length, and every item carries the paid window.
    assert all(i.duration == 30 for i in booked), [i.duration for i in booked]
    assert all(i.start_at is not None and i.end_at is not None for i in booked)
    print("  ok  booking on 2 screens + 1 group placed 3 items, each 30s with the paid window")

    # The items above are only half of "the advert runs". sync_tv answers 204 unless one of
    # its markers is newer than the player's `since`, and appending a playlist_items row
    # moves none of them by itself -- so a booking was stored, shown correctly on every
    # dashboard, and silently never sent to any screen that already had its playlist.
    assert playlist_marker() > marker_before_booking, (
        "placing an advert must mark the playlist edited, or the player keeps getting 204 "
        "and the advert never reaches the screen"
    )
    print("  ok  booking marked the playlist edited, so the screen fetches it")

    # Removing one place removes exactly one item.
    target_b = next(t for t in placement["targets"] if t["screen_id"] == b.id)
    removed = client.delete(f"/api/placements/{placement['id']}/targets/{target_b['id']}", headers=auth)
    assert removed.status_code == 200, removed.text
    booked = [i for i in items() if i.id != manual_id]
    assert len(booked) == 2, f"expected 2 remaining, got {len(booked)}"
    assert db.query(models.PlaylistItem).filter(models.PlaylistItem.id == manual_id).first(), "manual item was destroyed"
    print("  ok  removing one place removed exactly one item; the hand-made item survived")

    # Splitting a group booking drops one member and keeps the rest.
    target_group = next(t for t in removed.json()["targets"] if t["kind"] == "group")
    split = client.post(
        f"/api/placements/{placement['id']}/targets/{target_group['id']}/split",
        json={"exclude_screen_ids": [m2.id]}, headers=auth,
    )
    assert split.status_code == 200, split.text
    kinds = [t["kind"] for t in split.json()["targets"]]
    assert "group" not in kinds, kinds
    names = sorted(t["name"] for t in split.json()["targets"])
    assert names == ["Lobby", "Mall North"], names
    print("  ok  splitting a group booking kept Mall North and dropped Mall South")

    # Moving the dates moves every placed item.
    later_dt = now + timedelta(days=60)
    moved = client.put(f"/api/placements/{placement['id']}", json={"ends_at": later_dt.isoformat()}, headers=auth)
    assert moved.status_code == 200, moved.text
    booked = [i for i in items() if i.id != manual_id]
    # Compare instants, not strings: Postgres hands these back in the server's offset.
    assert all(abs((i.end_at - later_dt).total_seconds()) < 1 for i in booked), [str(i.end_at) for i in booked]
    print("  ok  changing the run window updated every placed item")

    # Deleting the booking clears its items and only its items.
    marker_before_delete = playlist_marker()
    gone = client.delete(f"/api/placements/{placement['id']}", headers=auth)
    assert gone.status_code == 200, gone.text
    remaining = items()
    assert len(remaining) == 1 and remaining[0].id == manual_id, [i.id for i in remaining]
    print("  ok  deleting the booking removed only what it had placed")

    # Same gate on the way out: an advert whose booking ended has to stop playing, and the
    # screen only learns that when the playlist is marked edited. Left unmarked it keeps
    # running the loop it last fetched -- billing the wrong advertiser for the airtime.
    assert playlist_marker() > marker_before_delete, (
        "removing an advert must mark the playlist edited, or the screen keeps playing it"
    )
    print("  ok  removing marked the playlist edited, so the screen drops it")

    # Another tenant cannot see or touch it.
    rival_auth = {"Authorization": f"Bearer {create_access_token(data={'sub': intruder.username})}"}
    assert client.get("/api/placements/", headers=rival_auth).json() == []
    assert client.post("/api/placements/", json=body, headers=rival_auth).status_code == 404
    print("  ok  another organisation sees nothing and cannot book against this advert")

    # --- a finished campaign is actually taken off the screen --------------------------
    # The player already refused to PLAY an expired item, so nothing looked wrong -- but it
    # stayed in every sync payload and each panel went on caching the video for a campaign
    # that had ended. The sweep is what makes the file go away.
    import asyncio
    from backend.worker import prune_finished_bookings

    long_over = client.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "advertiser": "Last Winter", "price_paise": 1000, "is_paid": True,
        "starts_at": (now - timedelta(days=60)).isoformat(),
        "ends_at": (now - timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": a.id}],
    })
    assert long_over.status_code == 201, long_over.text
    over_id = long_over.json()["id"]

    db.expire_all()
    over_target = db.query(models.AdPlacementTarget).filter(
        models.AdPlacementTarget.placement_id == over_id
    ).one()
    over_item_id = over_target.playlist_item_id
    assert over_item_id, "the finished booking should have placed an item to begin with"

    asyncio.run(prune_finished_bookings({}))

    db.expire_all()
    assert db.query(models.PlaylistItem).filter(
        models.PlaylistItem.id == over_item_id
    ).first() is None, "a finished campaign's playlist item was left on the screen"

    # The hand-made item on that same playlist must be untouched. The sweep reaches items
    # only through AdPlacementTarget, so an operator's own item is invisible to it -- and
    # deleting one would take content off a screen nobody sold.
    assert db.query(models.PlaylistItem).filter(
        models.PlaylistItem.id == manual_id
    ).first(), "the sweep destroyed a hand-made playlist item"

    # The booking survives: it is the record of a sale, and its report has to keep
    # answering for it long after the advert came down.
    assert client.get(f"/api/placements/{over_id}/report", headers=auth).status_code == 200
    print("  ok  a finished campaign's item is swept, the hand-made item and the sale survive")

    # A campaign that only just ended is inside the grace period, because an extension sold
    # an hour late must not find the advert already torn down.
    just_over = client.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "advertiser": "Yesterday", "price_paise": 1000, "is_paid": True,
        "starts_at": (now - timedelta(days=10)).isoformat(),
        "ends_at": (now - timedelta(hours=6)).isoformat(),
        "targets": [{"screen_id": b.id}],
    })
    assert just_over.status_code == 201, just_over.text
    db.expire_all()
    fresh_target = db.query(models.AdPlacementTarget).filter(
        models.AdPlacementTarget.placement_id == just_over.json()["id"]
    ).one()
    asyncio.run(prune_finished_bookings({}))
    db.expire_all()
    assert db.query(models.PlaylistItem).filter(
        models.PlaylistItem.id == fresh_target.playlist_item_id
    ).first(), "a campaign that ended hours ago was swept inside its grace period"
    print("  ok  a campaign that just ended is left alone during the grace period")

    print("ad placements: all checks passed")
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
