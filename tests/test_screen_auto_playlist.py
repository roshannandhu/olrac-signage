"""Every screen gets a dedicated playlist upon pairing/enrolling,
and the ensure-playlist endpoint provisions one on demand if missing.

Throwaway Postgres database. Run directly:  python tests/test_screen_auto_playlist.py
"""
import os, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_autoplaylist_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "autoplaylist-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')

try:
    from fastapi.testclient import TestClient  # noqa: E402
    from backend import models  # noqa: E402
    from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402
    from backend.database import SessionLocal, engine  # noqa: E402
    from backend.main import app  # noqa: E402

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    org = models.Organization(name="Auto Playlist Org", slug="auto-playlist-org", status="active")
    db.add(org)
    db.commit()

    user = models.User(
        organization_id=org.id,
        username="screen_owner",
        email="owner@autoplaylist.test",
        hashed_password=get_password_hash("pass123"),
        role="owner",
        is_active=True,
    )
    db.add(user)
    db.commit()

    token = create_access_token({"sub": user.username})
    auth_headers = {"Authorization": f"Bearer {token}"}

    client = TestClient(app)

    # 1. Pairing flow: /api/screens/register then /api/screens/pair
    reg = client.post("/api/screens/register", json={
        "device_id": "tv-auto-1",
        "installation_id": "install-auto-1",
        "device_model": "Sony Bravia 4K",
    })
    assert reg.status_code == 200, reg.text
    pair_code = reg.json()["pair_code"]
    assert pair_code is not None

    pair_res = client.post("/api/screens/pair", json={
        "pair_code": pair_code,
        "name": "Front Desk TV",
    }, headers=auth_headers)
    assert pair_res.status_code == 200, pair_res.text
    paired_data = pair_res.json()
    screen_id = paired_data["id"]

    # Verify playlist was created and assigned
    db.expire_all()
    screen = db.query(models.Screen).filter(models.Screen.id == screen_id).one()
    assert screen.playlist_id is not None, "Screen must have playlist_id set on pairing"
    playlist = db.query(models.Playlist).filter(models.Playlist.id == screen.playlist_id).one()
    assert playlist.name is not None
    assert "loop" in playlist.name.lower()
    print(f"  ok  pairing automatically provisioned playlist {playlist.id} ('{playlist.name}')")

    # 2. Enrollment flow: /api/screens/enroll
    tok = models.EnrollmentToken(
        organization_id=org.id, token="tok-auto-enroll", description="enroll test", use_count=0, is_active=True
    )
    db.add(tok)
    db.commit()

    enroll_res = client.post("/api/screens/enroll", json={
        "device_id": "tv-auto-2",
        "enrollment_token": "tok-auto-enroll",
        "installation_id": "install-auto-2",
        "device_model": "Samsung Smart Signage",
    })
    assert enroll_res.status_code == 200, enroll_res.text
    enroll_data = enroll_res.json()
    screen_id_2 = enroll_data["screen_id"]

    db.expire_all()
    screen_2 = db.query(models.Screen).filter(models.Screen.id == screen_id_2).one()
    assert screen_2.playlist_id is not None, "Enrolled screen must have playlist_id set"
    playlist_2 = db.query(models.Playlist).filter(models.Playlist.id == screen_2.playlist_id).one()
    assert playlist_2.organization_id == org.id
    print(f"  ok  enrollment automatically provisioned playlist {playlist_2.id} ('{playlist_2.name}')")

    # 3. Ensure-playlist safety endpoint on a screen that already has a playlist
    ensure_res = client.post(f"/api/screens/{screen_id}/ensure-playlist", headers=auth_headers)
    assert ensure_res.status_code == 200, ensure_res.text
    ensure_data = ensure_res.json()
    assert ensure_data["id"] == screen.playlist_id, "ensure-playlist returns existing playlist without duplicating"
    print(f"  ok  ensure-playlist returns existing playlist {ensure_data['id']}")

    # 4. Ensure-playlist safety endpoint on a pre-migration screen with NO playlist
    pre_mig_screen = models.Screen(
        organization_id=org.id,
        device_id="tv-legacy-3",
        name="Legacy Unassigned Screen",
        status="online",
        playlist_id=None,
    )
    db.add(pre_mig_screen)
    db.commit()
    db.refresh(pre_mig_screen)

    ensure_res_legacy = client.post(f"/api/screens/{pre_mig_screen.id}/ensure-playlist", headers=auth_headers)
    assert ensure_res_legacy.status_code == 200, ensure_res_legacy.text
    legacy_playlist_data = ensure_res_legacy.json()
    assert legacy_playlist_data["id"] is not None
    legacy_db_playlist = db.query(models.Playlist).filter(models.Playlist.id == legacy_playlist_data["id"]).one()
    assert legacy_db_playlist.organization_id == org.id

    db.expire_all()
    db.refresh(pre_mig_screen)
    assert pre_mig_screen.playlist_id == legacy_playlist_data["id"]
    print(f"  ok  ensure-playlist provisions playlist {legacy_playlist_data['id']} for pre-migration screen")

    # 5. Verify playlist resolution parity on the screen
    resolved_id = pre_mig_screen.resolve_playlist_id()
    assert resolved_id == legacy_playlist_data["id"]
    print(f"  ok  screen.resolve_playlist_id() resolves to {resolved_id}")

    print("screen auto playlist: all checks passed")

finally:
    try:
        admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
        admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        admin.cursor().execute(f'DROP DATABASE IF EXISTS "{SCRATCH}"')
        admin.close()
    except Exception:
        pass
