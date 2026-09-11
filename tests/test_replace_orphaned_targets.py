"""A booking that has fallen off its screens can be put back.

The failure this covers, seen in production: four paid bookings all reading "Running" on
screen 52, and the screen playing nothing.

    PlaylistItem.content_id          is ON DELETE CASCADE
    AdPlacementTarget.playlist_item_id is ON DELETE SET NULL

So deleting or re-uploading a creative takes every playlist item with it and quietly nulls
the link on every booking that used it. The bookings survive -- still Running, still Paid --
placed on nothing. Before this endpoint the only way back was to delete the target and
re-add it, which resets assigned_at and with it the per-location figures on the client's
report.

Throwaway Postgres database. Run directly:  python tests/test_replace_orphaned_targets.py
"""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_replace_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "replace-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

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
    db.add(org); db.commit()
    owner = models.User(organization_id=org.id, username="owner@acme.test",
                        hashed_password=get_password_hash("x"), role="owner", is_active=True)
    db.add(owner); db.commit()

    ad = models.Content(organization_id=org.id, type="video", file_url="/uploads/1/a.mp4",
                        name="Summer Sale", status="ready", duration_ms=30_000)
    db.add(ad); db.commit()
    ad_id = ad.id

    near = models.Screen(organization_id=org.id, name="Lobby", status="online")
    far = models.Screen(organization_id=org.id, name="Cafe", status="online")
    db.add_all([near, far]); db.commit()

    http = TestClient(app)
    auth = {"Authorization": f"Bearer {create_access_token(data={'sub': owner.username})}"}
    now = models.utcnow()

    created = http.post("/api/placements/", headers=auth, json={
        "content_id": ad_id, "advertiser": "Brightmart", "price_paise": 500000,
        "is_paid": True,
        "starts_at": (now - timedelta(days=10)).isoformat(),
        "ends_at": (now + timedelta(days=20)).isoformat(),
        # One location sold its own shorter run, so the restore has a window to preserve.
        "targets": [{"screen_id": near.id}, {"screen_id": far.id, "days": 10}],
    })
    assert created.status_code == 201, created.text
    booking = created.json()
    booking_id = booking["id"]
    assert all(t["is_placed"] for t in booking["targets"]), booking["targets"]
    # assigned_at is not on the API response, so read it where it lives.
    assigned_before = {
        t.screen_id: t.assigned_at
        for t in db.query(models.AdPlacementTarget).filter(
            models.AdPlacementTarget.placement_id == booking_id).all()
    }
    far_days_before = next(t["days"] for t in booking["targets"] if t["screen_id"] == far.id)
    print("  ok  a fresh booking is placed on both screens")

    # The production failure, exactly: every playlist is gone while the creative and the
    # bookings remain. Deleting a Playlist cascades its items away (PlaylistItem.playlist_id
    # is ON DELETE CASCADE), which nulls every target's link (SET NULL) and nulls the
    # screen's own playlist_id (SET NULL) -- leaving screens with no loop, bookings still
    # Running and Paid, and nothing playing anywhere.
    db.expire_all()
    db.query(models.Playlist).delete()
    db.commit()

    listed = http.get("/api/placements/", headers=auth)
    assert listed.status_code == 200, listed.text
    broken = next(p for p in listed.json() if p["id"] == booking_id)
    assert broken["targets"], "the targets vanished; the booking lost its places entirely"
    assert not any(t["is_placed"] for t in broken["targets"]), (
        f"expected every target unplaced after the playlists went: {broken['targets']}"
    )
    db.expire_all()
    assert db.query(models.PlaylistItem).count() == 0, "playlist items survived the cascade"
    for screen in (near, far):
        row = db.query(models.Screen).filter(models.Screen.id == screen.id).one()
        assert row.playlist_id is None, "the screen kept a pointer to a deleted playlist"
    print("  ok  losing the playlists leaves the booking Running but placed on nothing")

    fixed = http.post(f"/api/placements/{booking_id}/replace", headers=auth)
    assert fixed.status_code == 200, fixed.text
    restored = fixed.json()
    assert len(restored["targets"]) == 2, (
        f"re-placing must not duplicate or drop a location: {restored['targets']}"
    )
    assert all(t["is_placed"] for t in restored["targets"]), (
        f"a target was left unplaced by the repair: {restored['targets']}"
    )
    db.expire_all()
    assert db.query(models.PlaylistItem).count() == 2, "expected one item per screen"
    print("  ok  re-placing puts the booking back on every screen it was sold to")

    # assigned_at must survive: the client's report divides each location's plays by the
    # days it really ran, so restarting that clock reports a location that has run all
    # month as a late addition.
    db.expire_all()
    assigned_after = {
        t.screen_id: t.assigned_at
        for t in db.query(models.AdPlacementTarget).filter(
            models.AdPlacementTarget.placement_id == booking_id).all()
    }
    assert assigned_after == assigned_before, (
        f"re-placing reset the assignment dates: {assigned_after} was {assigned_before}"
    )
    far_days_after = next(t["days"] for t in restored["targets"] if t["screen_id"] == far.id)
    assert far_days_after == far_days_before, (
        f"the 10-day location came back with {far_days_after} days, not {far_days_before} -- "
        "it silently inherited the booking's window"
    )
    print("  ok  the original assignment date and each location's own window are preserved")

    # Idempotent: nothing left to repair, and a second call must not stack a duplicate copy
    # of the advert into the loop.
    again = http.post(f"/api/placements/{booking_id}/replace", headers=auth)
    assert again.status_code == 200, again.text
    assert len(again.json()["targets"]) == 2, again.json()["targets"]
    db.expire_all()
    assert db.query(models.PlaylistItem).count() == 2, (
        "a second repair duplicated the advert into the playlist"
    )
    print("  ok  repairing an already-healthy booking changes nothing")

    assert http.post("/api/placements/999999/replace", headers=auth).status_code == 404
    print("  ok  an unknown booking is a 404")

    print("replace orphaned targets: all checks passed")
finally:
    try:
        if db: db.close()
    except Exception:
        pass
    try:
        engine.dispose()
    except Exception:
        pass
    try:
        admin.cursor().execute(f'DROP DATABASE IF EXISTS "{SCRATCH}" WITH (FORCE)')
    except Exception:
        pass
    admin.close()
