"""A screen setting an operator changes must reach the player.

The player asks "anything new since X?" and the server answers 204 when nothing moved.
Orientation and fit_mode ride along in that same response but used to move nothing, so
turning a panel portrait in the dashboard changed the record and never the screen.

Run directly:  python tests/test_sync_invalidation.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-test-syncinv-", ignore_cleanup_errors=True)
test_db_name = "olrac_test_sync_invalidation"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
conn.cursor().execute(f"DROP DATABASE IF EXISTS {test_db_name}")
conn.cursor().execute(f"CREATE DATABASE {test_db_name} OWNER olrac")
conn.close()

os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{test_db_name}"
os.environ["SECRET_KEY"] = "sync-invalidation-test-key"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import get_password_hash  # noqa: E402


def seed():
    db = database.SessionLocal()
    try:
        models.Base.metadata.create_all(bind=db.get_bind())
        org = models.Organization(name="Sync Org", slug="sync-org")
        db.add(org)
        db.commit()
        db.refresh(org)

        db.add(models.User(
            username="sync_owner",
            hashed_password=get_password_hash("pwd"),
            role="owner",
            organization_id=org.id,
        ))
        content = models.Content(
            organization_id=org.id, name="Ad", type="image",
            file_url="/uploads/ad.png", status="ready",
        )
        playlist = models.Playlist(organization_id=org.id, name="Loop")
        db.add_all([content, playlist])
        db.commit()
        db.refresh(content)
        db.refresh(playlist)

        # rotation=None: this item follows whatever the screen is set to, which is the
        # value the operator is about to change.
        db.add(models.PlaylistItem(
            playlist_id=playlist.id, content_id=content.id,
            duration=10, order=0, rotation=None,
        ))
        screen = models.Screen(
            organization_id=org.id, device_id="sync-device", name="Panel",
            status="offline", playlist_id=playlist.id, orientation=0, fit_mode="contain",
        )
        db.add(screen)
        db.add(models.EnrollmentToken(organization_id=org.id, token="sync-token", is_active=True))
        db.commit()
        db.refresh(screen)
        return screen.id
    finally:
        db.close()


def run():
    screen_id = seed()
    with TestClient(app) as client:
        enroll = client.post("/api/screens/enroll", json={
            "device_id": "sync-device", "enrollment_token": "sync-token",
        })
        assert enroll.status_code == 200, enroll.text
        auth = client.post("/api/screens/auth", json={
            "device_id": "sync-device", "device_secret": enroll.json()["device_secret"],
        })
        assert auth.status_code == 200, auth.text
        device = {"Authorization": f"Bearer {auth.json()['access_token']}"}

        login = client.post("/api/auth/token", data={"username": "sync_owner", "password": "pwd"})
        owner = {"Authorization": f"Bearer {login.json()['access_token']}"}

        first = client.get("/api/screens/sync-device/sync", headers=device)
        assert first.status_code == 200, first.text
        marker = first.json()["playlist_updated_at"]
        assert first.json()["fit_mode"] == "contain"
        assert first.json()["playlist"]["items"][0]["rotation"] == 0

        quiet = client.get(f"/api/screens/sync-device/sync?since={marker}", headers=device)
        assert quiet.status_code == 204, "nothing changed, so the player should be told so"

        patched = client.patch(f"/api/screens/{screen_id}",
                               json={"orientation": 90, "fit_mode": "cover"}, headers=owner)
        assert patched.status_code == 200, patched.text

        after = client.get(f"/api/screens/sync-device/sync?since={marker}", headers=device)
        assert after.status_code == 200, (
            "the screen was re-oriented; a 204 here means the panel never finds out"
        )
        assert after.json()["fit_mode"] == "cover"
        assert after.json()["playlist"]["items"][0]["rotation"] == 90, (
            "an item with no override of its own must follow the screen's new orientation"
        )

        # PUT /screens/{id} is the other way orientation is set, and it has the same gate.
        marker = after.json()["playlist_updated_at"]
        assert client.get(f"/api/screens/sync-device/sync?since={marker}",
                          headers=device).status_code == 204
        put = client.put(f"/api/screens/{screen_id}",
                         json={"name": "Panel", "orientation": 270}, headers=owner)
        assert put.status_code == 200, put.text
        again = client.get(f"/api/screens/sync-device/sync?since={marker}", headers=device)
        assert again.status_code == 200, "PUT changed the orientation and told nobody"
        assert again.json()["playlist"]["items"][0]["rotation"] == 270


if __name__ == "__main__":
    run()
    print("sync invalidation: all checks passed")
