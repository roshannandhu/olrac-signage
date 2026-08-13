"""Test script for P4 Proof of Play deduplication and insertion."""
import os
import sys
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ignore_cleanup_errors: Windows keeps the SQLite handle open past interpreter exit.
TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-test-p4-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "p4.db"

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
os.environ["SECRET_KEY"] = "p4-test-secret-key"

from fastapi.testclient import TestClient
from backend import database, models
from backend.main import app

def run():
    failures = []
    
    with TestClient(app) as client:
        db = database.SessionLocal()
        try:
            # Setup DB models
            models.Base.metadata.create_all(bind=db.get_bind())
            
            org = models.Organization(name="P4 Org", slug="p4-org")
            db.add(org)
            db.commit()
            db.refresh(org)
            
            screen = models.Screen(organization_id=org.id, device_id="p4-device", status="offline")
            db.add(screen)
            db.commit()
            db.refresh(screen)
            
            # Enroll to get token
            db.add(models.EnrollmentToken(organization_id=org.id, token="p4-token", is_active=True))
            db.commit()
            
            screen_id = screen.id
            org_id = org.id
            
        finally:
            db.close()
            
        # Enroll and authenticate
        enroll = client.post("/api/screens/enroll", json={"device_id": "p4-device", "enrollment_token": "p4-token"})
        assert enroll.status_code == 200, f"Enrollment failed: {enroll.text}"
        device_secret = enroll.json()["device_secret"]
        
        auth = client.post("/api/screens/auth", json={"device_id": "p4-device", "device_secret": device_secret})
        assert auth.status_code == 200, f"Auth failed: {auth.text}"
        jwt = {"Authorization": f"Bearer {auth.json()['access_token']}"}
        
        # Test 1: 3x replay (Deduplication)
        # Create a batch of 5 events
        base_time = datetime.now(timezone.utc)
        batch1_events = []
        for i in range(5):
            batch1_events.append({
                "event_id": str(uuid.uuid4()),
                "device_started_at": (base_time + timedelta(seconds=i*10)).isoformat(),
                "device_finished_at": (base_time + timedelta(seconds=i*10 + 10)).isoformat(),
                "corrected_started_at": (base_time + timedelta(seconds=i*10)).isoformat(),
                "corrected_finished_at": (base_time + timedelta(seconds=i*10 + 10)).isoformat(),
                "duration_ms": 10000,
                "status": "completed"
            })
            
        payload = {
            "screen_id": screen_id,
            "organization_id": org_id,
            "events": batch1_events
        }
        
        r1 = client.post("/api/screens/play-logs/batch", json=payload, headers=jwt)
        assert r1.status_code == 200, f"Failed initial insert: {r1.text}"
        assert r1.json()["inserted"] == 5, f"Expected 5, got {r1.json()['inserted']}"
            
        # Replay 1
        r2 = client.post("/api/screens/play-logs/batch", json=payload, headers=jwt)
        if r2.status_code != 200 or r2.json()["inserted"] != 0:
            failures.append(f"Failed replay 1 deduplication: inserted {r2.json().get('inserted')}")
            
        # Replay 2
        r3 = client.post("/api/screens/play-logs/batch", json=payload, headers=jwt)
        if r3.status_code != 200 or r3.json()["inserted"] != 0:
            failures.append(f"Failed replay 2 deduplication")

        db = database.SessionLocal()
        try:
            count = db.query(models.PlayLog).count()
            if count != 5:
                failures.append(f"Deduplication failed in DB: expected 5, got {count}")
        finally:
            db.close()
            
        # Test 2: 3-hour clock skew alignment
        real_time = datetime.now(timezone.utc)
        device_time = real_time - timedelta(hours=3)
        skewed_event = {
            "event_id": str(uuid.uuid4()),
            "device_started_at": device_time.isoformat(),
            "device_finished_at": (device_time + timedelta(seconds=15)).isoformat(),
            "corrected_started_at": real_time.isoformat(),
            "corrected_finished_at": (real_time + timedelta(seconds=15)).isoformat(),
            "duration_ms": 15000,
            "status": "partial"
        }
        r_skew = client.post("/api/screens/play-logs/batch", json={
            "screen_id": screen_id,
            "organization_id": org_id,
            "events": [skewed_event]
        }, headers=jwt)
        assert r_skew.status_code == 200, f"Failed 3-hour skew insert: {r_skew.text}"
        assert r_skew.json()["inserted"] == 1, f"Expected 1, got {r_skew.json()['inserted']}"
            
        db = database.SessionLocal()
        try:
            ev = db.query(models.PlayLog).filter_by(event_id=skewed_event["event_id"]).one()
            diff = abs((ev.corrected_started_at - ev.device_started_at).total_seconds())
            if diff < 10799 or diff > 10801:
                failures.append(f"Skew difference incorrect, expected 10800s, got {diff}s")
        finally:
            db.close()
            
        # Test 3: 24h offline accumulation (simulate a batch of 500 events)
        accumulation_events = []
        for i in range(500):
            accumulation_events.append({
                "event_id": str(uuid.uuid4()),
                "device_started_at": (base_time + timedelta(seconds=i*10)).isoformat(),
                "device_finished_at": (base_time + timedelta(seconds=i*10 + 10)).isoformat(),
                "corrected_started_at": (base_time + timedelta(seconds=i*10)).isoformat(),
                "corrected_finished_at": (base_time + timedelta(seconds=i*10 + 10)).isoformat(),
                "duration_ms": 10000,
                "status": "completed"
            })
            
        r_accum = client.post("/api/screens/play-logs/batch", json={
            "screen_id": screen_id,
            "organization_id": org_id,
            "events": accumulation_events
        }, headers=jwt)
        
        if r_accum.status_code != 200 or r_accum.json()["inserted"] != 500:
            failures.append(f"Failed 24h accumulation batch: {r_accum.text}")
            
        # Test 4: Exceed 500 cap
        overflow_events = accumulation_events + [skewed_event]
        r_over = client.post("/api/screens/play-logs/batch", json={
            "screen_id": screen_id,
            "organization_id": org_id,
            "events": overflow_events
        }, headers=jwt)
        
        if r_over.status_code != 422:
            failures.append(f"Did not reject batch > 500 (got {r_over.status_code})")

    if failures:
        print("PROOF OF PLAY FAILURES:")
        for line in failures:
            print("  -", line)
        raise SystemExit(1)
        
    print("Proof of Play test passed: 3x replay deduplicated, 3h skew preserved, 24h accumulated batch processed, cap enforced.")

if __name__ == "__main__":
    run()
