"""A client report must count that client's window and that client's screens. Only.

Two clients book the same creative with overlapping windows on different screens; each
report must see only its own. Throwaway Postgres database.

Run directly:  python tests/test_booking_report.py
"""
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_bookingreport_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "report-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["GOOGLE_MAPS_API_KEY"] = ""      # exercise the no-key path

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

    now = models.utcnow()

    mall = models.ScreenGroup(organization_id=org.id, name="Phoenix Mall")
    db.add(mall); db.commit()
    # Two mall screens reached through the group, plus one booked directly by the rival.
    m1 = models.Screen(organization_id=org.id, name="Food Court", group_id=mall.id,
                       location="Phoenix Mall", latitude=9.93, longitude=76.26,
                       status="online", last_seen=now)
    m2 = models.Screen(organization_id=org.id, name="Entrance", group_id=mall.id,
                       location="Phoenix Mall", latitude=9.93, longitude=76.27,
                       status="offline", last_seen=now - timedelta(days=40))
    airport = models.Screen(organization_id=org.id, name="Gate 4", location="City Airport",
                            latitude=10.15, longitude=76.39, status="online", last_seen=now)
    db.add_all([m1, m2, airport]); db.commit()

    client = TestClient(app)
    auth = {"Authorization": f"Bearer {create_access_token(data={'sub': owner.username})}"}

    # Client A: the mall group, this month.
    a = client.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "advertiser": "Client A", "price_paise": 100000, "is_paid": True,
        "starts_at": (now - timedelta(days=10)).isoformat(),
        "ends_at": (now + timedelta(days=10)).isoformat(),
        "targets": [{"group_id": mall.id}],
    })
    assert a.status_code == 201, a.text
    a_id = a.json()["id"]

    # Client B: the airport screen, an overlapping window.
    b = client.post("/api/placements/", headers=auth, json={
        "content_id": ad.id, "advertiser": "Client B", "price_paise": 50000, "is_paid": False,
        "starts_at": (now - timedelta(days=5)).isoformat(),
        "ends_at": (now + timedelta(days=5)).isoformat(),
        "targets": [{"screen_id": airport.id}],
    })
    assert b.status_code == 201, b.text
    b_id = b.json()["id"]

    def rollup(screen, hours_ago, plays, completed):
        db.add(models.PlayLogHourlyRollup(
            organization_id=org.id, screen_id=screen.id, media_id=ad.id,
            date_hour=now - timedelta(hours=hours_ago),
            total_plays=plays, completed_plays=completed, partial_plays=0, error_plays=0))

    rollup(m1, 24, 100, 95)          # inside A's window
    rollup(m2, 48, 60, 60)           # inside A's window
    rollup(airport, 24, 500, 480)    # inside B's window, NOT A's screens
    rollup(m1, 24 * 60, 999, 999)    # 60 days ago — outside A's window
    db.commit()

    ra = client.get(f"/api/placements/{a_id}/report", headers=auth)
    assert ra.status_code == 200, ra.text
    ra = ra.json()
    assert ra["totals"]["total_plays"] == 160, ra["totals"]
    names = sorted(s["screen_name"] for s in ra["per_screen"])
    assert names == ["Entrance", "Food Court"], names
    print("  ok  group target expanded to its members; airport plays and out-of-window plays excluded")

    rb = client.get(f"/api/placements/{b_id}/report", headers=auth).json()
    assert rb["totals"]["total_plays"] == 500, rb["totals"]
    assert [s["screen_name"] for s in rb["per_screen"]] == ["Gate 4"], rb["per_screen"]
    print("  ok  the other client's report sees only its own screen")

    # A screen silent since before the period ended must be flagged, not silently counted.
    assert "Entrance" in ra["stale_screens"], ra["stale_screens"]
    assert "Food Court" not in ra["stale_screens"], ra["stale_screens"]
    entrance = next(s for s in ra["per_screen"] if s["screen_name"] == "Entrance")
    assert entrance["counts_may_be_incomplete"] is True
    print("  ok  a screen that has not reported in is flagged as possibly incomplete")

    places = {p["location"]: p for p in ra["per_location"]}
    assert set(places) == {"Phoenix Mall"}, places
    assert places["Phoenix Mall"]["screens"] == 2
    print("  ok  plays roll up by real location, not by group")

    # The PDF must generate with no maps key configured.
    pdf = client.get(f"/api/placements/{a_id}/report.pdf", headers=auth)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content[:5] == b"%PDF-", pdf.content[:20]
    assert len(pdf.content) > 2000, len(pdf.content)
    assert "Client A" in pdf.headers.get("content-disposition", "")
    print(f"  ok  PDF generated without a maps key ({len(pdf.content):,} bytes)")

    print("booking report: all checks passed")
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
