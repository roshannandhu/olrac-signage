import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-datetime-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "datetime.db"
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
test_db_name = f"olrac_test_{DB_PATH.stem.replace('-', '_')}"
try:
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    conn.cursor().execute(f"CREATE DATABASE {test_db_name} OWNER olrac")
    conn.close()
except Exception as e:
    pass
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{test_db_name}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INITIAL_ADMIN_USERNAME"] = "datetime-owner"
os.environ["INITIAL_ADMIN_PASSWORD"] = "datetime-password"

from fastapi.testclient import TestClient
from backend import database, models
import alembic.config
alembic_args = ['-c', 'backend/alembic.ini', 'upgrade', 'head']
alembic.config.main(argv=alembic_args)
from backend.main import app

# Build the schema explicitly. backend.main used to do this as an import side effect,
# so importing the app silently wrote to whatever DATABASE_URL pointed at; it now runs
# in the lifespan, which a bare TestClient(app) never starts. Each isolated script owns
# its own database anyway, so creating it here is the honest version of what was
# happening implicitly before.
from backend import database as _bootstrap_db, models as _bootstrap_models
_bootstrap_models.Base.metadata.create_all(bind=_bootstrap_db.engine)

def run():
    with TestClient(app) as client:
        # 1. Login
        resp = client.post("/api/auth/token", data={"username": "datetime-owner", "password": "datetime-password"})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Pair a screen (relies on pairing-code expiry using aware datetimes)
        # First register
        reg = client.post("/api/screens/register", json={"device_id": "datetime-device"})
        assert reg.status_code == 200, reg.text
        code = reg.json()["pair_code"]

        # 3. Simulate passing some time or just test pairing directly
        pair = client.post("/api/screens/pair", headers=headers, json={"pair_code": code})
        assert pair.status_code == 200, pair.text
        screen_id = pair.json()["id"]

        # 4. Create a playlist and check updated_at sync comparison
        pl_resp = client.post("/api/playlists/", headers=headers, json={"name": "Aware Playlist"})
        assert pl_resp.status_code in (200, 201), pl_resp.text
        playlist_id = pl_resp.json()["id"]

        assign_resp = client.post(f"/api/screens/{screen_id}/assign/{playlist_id}", headers=headers)
        assert assign_resp.status_code == 200, assign_resp.text

        # 5. Sync TV and verify 204 or 200 works fine with aware datetimes
        sync1 = client.get(f"/api/screens/datetime-device/sync")
        assert sync1.status_code == 200, sync1.text

        # Wait a bit logically (use marker)
        updated_at_str = sync1.json()["playlist_updated_at"]
        
        sync2 = client.get(f"/api/screens/datetime-device/sync", params={"since": updated_at_str})
        assert sync2.status_code == 204, sync2.text

    print("Datetime aware tests passed successfully")

if __name__ == "__main__":
    run()
