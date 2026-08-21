"""A reinstalled player must reclaim its screen, not create a duplicate.

Throwaway Postgres database. Run directly:  python tests/test_reinstall_dedup.py
"""
import os, sys, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCRATCH = f"olrac_dedup_{uuid.uuid4().hex[:8]}"
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{SCRATCH}"
os.environ["SECRET_KEY"] = "dedup-test-secret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"

import psycopg2  # noqa: E402
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT  # noqa: E402

admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
admin.cursor().execute(f'CREATE DATABASE "{SCRATCH}" OWNER olrac')

try:
    from fastapi.testclient import TestClient  # noqa: E402
    from backend import models  # noqa: E402
    from backend.database import SessionLocal, engine  # noqa: E402
    from backend.main import app  # noqa: E402

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    org = models.Organization(name="Acme", slug="acme")
    db.add(org); db.commit()
    tok = models.EnrollmentToken(
        organization_id=org.id, token="enroll-me", description="fleet", use_count=0, is_active=True
    )
    db.add(tok); db.commit()

    client = TestClient(app)
    INSTALL = "android-id-abc123"

    first = client.post("/api/screens/enroll", json={
        "device_id": "uuid-generated-on-first-install",
        "enrollment_token": "enroll-me",
        "installation_id": INSTALL,
    })
    assert first.status_code == 200, first.text
    count_after_first = db.query(models.Screen).count()
    assert count_after_first == 1, count_after_first
    screen_id = db.query(models.Screen).one().id
    print(f"  ok  first enrollment created screen {screen_id}")

    # The app is reinstalled: prefs are wiped, so a brand new device_id is generated,
    # but Settings.Secure.ANDROID_ID — the installation id — is unchanged.
    second = client.post("/api/screens/enroll", json={
        "device_id": "uuid-generated-after-reinstall",
        "enrollment_token": "enroll-me",
        "installation_id": INSTALL,
    })
    assert second.status_code == 200, second.text

    db.expire_all()
    screens = db.query(models.Screen).all()
    assert len(screens) == 1, f"reinstall created a duplicate: {[(s.id, s.device_id) for s in screens]}"
    assert screens[0].id == screen_id, "reclaimed the wrong row"
    assert screens[0].device_id == "uuid-generated-after-reinstall", screens[0].device_id
    print(f"  ok  reinstall reclaimed screen {screen_id} instead of duplicating")

    # A genuinely different TV must still get its own screen.
    third = client.post("/api/screens/enroll", json={
        "device_id": "uuid-of-a-second-tv",
        "enrollment_token": "enroll-me",
        "installation_id": "android-id-different",
    })
    assert third.status_code == 200, third.text
    db.expire_all()
    assert db.query(models.Screen).count() == 2, "a different device should create its own screen"
    print("  ok  a different TV still gets its own screen")

    print("reinstall dedup: all checks passed")
finally:
    try:
        db.close()
    except Exception:
        pass
    engine.dispose()
    cur = admin.cursor()
    cur.execute(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{SCRATCH}'")
    cur.execute(f'DROP DATABASE IF EXISTS "{SCRATCH}"')
    admin.close()
