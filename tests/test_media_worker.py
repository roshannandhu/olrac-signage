"""Test for media worker and ffmpeg pipeline"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient

TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-worker-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "worker.db"
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

test_db_name = f"olrac_test_worker_{os.getpid()}"
try:
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    conn.cursor().execute(f"CREATE DATABASE {test_db_name} OWNER olrac")
    conn.close()
except Exception as e:
    pass

# We must force a new engine for this test so it doesn't share state with other tests
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{test_db_name}"

from backend import database, models
from backend.main import app
from backend.worker import process_media_sync

def setup_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create a fresh engine for this specific test script
    engine = create_engine(os.environ["DATABASE_URL"])
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    database.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    org = db.query(models.Organization).filter(models.Organization.slug == "test-org-worker-unique").first()
    if not org:
        org = models.Organization(name="Test Org Worker", slug="test-org-worker-unique")
        db.add(org)
        db.commit()
    user = db.query(models.User).filter(models.User.username == "test-worker-user-unique").first()
    if not user:
        user = models.User(
            organization_id=org.id,
            username="test-worker-user-unique",
            hashed_password="fake",
            role="owner"
        )
        db.add(user)
        db.commit()
    db.refresh(org)
    db.refresh(user)
    return user, db, engine, SessionLocal

def synthesize_video(filepath: Path, width=640, height=360):
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        f"-i", f"testsrc=duration=2:size={width}x{height}:rate=30",
        "-c:v", "libx264",
        str(filepath)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@pytest.fixture(scope="module", autouse=True)
def cleanup_tempdir():
    yield
    TEMP_DIR.cleanup()

@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is required for pipeline test")
def test_media_pipeline():
    user, db, test_engine, test_session_local = setup_db()
    client = TestClient(app)
    
    # Authenticate via dependency overrides
    import backend.tenancy
    def override_get_tenant_scope():
        return backend.tenancy.TenantScope(db=db, user=user)
        
    def override_require_tenant_roles(*roles):
        def requirement():
            return override_get_tenant_scope()
        return requirement
        
    app.dependency_overrides[backend.tenancy.get_tenant_scope] = override_get_tenant_scope
    app.dependency_overrides[backend.tenancy.require_tenant_roles] = override_require_tenant_roles
    
    # 1. Synthesize a dummy portrait video (400x800 - odd aspect ratio) to test the padding fix
    video_path = Path(TEMP_DIR.name) / "dummy_portrait.mp4"
    synthesize_video(video_path, width=400, height=800)
    
    # 2. Upload it via API
    with open(video_path, "rb") as f:
        resp = client.post("/api/content/upload", files={"file": ("dummy_portrait.mp4", f)}, data={"name": "Test Video"})
    assert resp.status_code == 201, resp.text
    content_payload = resp.json()
    assert content_payload["status"] == "processing"
    
    content_id = content_payload["id"]
    
    # 3. Inject test DB into worker and run the worker process synchronously
    import backend.worker
    original_session_local = backend.worker.SessionLocal
    backend.worker.SessionLocal = test_session_local
    try:
        process_media_sync(content_id)
    finally:
        backend.worker.SessionLocal = original_session_local
    
    # 4. Verify the database state
    # The worker committed through its own session; without expiring, this session can
    # hand back its cached copy and the status still reads "processing".
    db.expire_all()
    c = db.query(models.Content).filter(models.Content.id == content_id).first()
    assert c.status == "ready"
    assert c.failed_reason is None
    
    # It should have generated 4 renditions
    assert len(c.renditions) == 4
    
    # The thumbnail should be generated
    assert c.thumbnail is not None
    
    
    # Clean up
    app.dependency_overrides.clear()
    db.close()
    test_engine.dispose()
