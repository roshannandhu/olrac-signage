"""Test for media worker and ffmpeg pipeline"""

import os
import shutil
import socket
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

# `backend.main` runs Base.metadata.create_all at import time, so importing the app needs
# a live database. Without this probe an unreachable Postgres raised OperationalError
# during *collection*, which aborted the entire run -- every other test in the suite went
# unreported because this one file could not be imported. Skipping at module level keeps
# the failure local and honest: this file is skipped, the rest still run.
_probe = socket.socket()
_probe.settimeout(3)
try:
    _probe.connect(("127.0.0.1", 5432))
except OSError:
    pytest.skip(
        "PostgreSQL is not reachable on localhost:5432; the media pipeline tests need it",
        allow_module_level=True,
    )
finally:
    _probe.close()

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


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is required for pipeline test")
def test_media_pipeline_on_object_storage():
    """The same pipeline, with the media in a bucket rather than on local disk.

    This is the path that did not exist. `process_media_sync` raised
    NotImplementedError on any `s3://` URL, so with R2 configured -- the deployment the
    README documents -- every video upload finished `status="failed"` with no renditions,
    and capability-based rendition selection had nothing to choose from.
    """
    moto = pytest.importorskip("moto", reason="moto is required for the object-storage pipeline test")
    import boto3

    from backend import media_storage

    user, db, test_engine, test_session_local = setup_db()
    bucket = "olrac-worker-test"

    source = Path(TEMP_DIR.name) / "cloud_source.mp4"
    synthesize_video(source, width=400, height=800)

    previous_key = os.environ.get("AWS_ACCESS_KEY_ID")
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["S3_ENDPOINT_URL"] = ""
    os.environ["S3_BUCKET_NAME"] = bucket
    media_storage.S3_BUCKET = bucket

    import backend.worker
    original_session_local = backend.worker.SessionLocal
    backend.worker.SessionLocal = test_session_local
    try:
        with moto.mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket=bucket)
            key = f"{user.organization_id}/cloud_source.mp4"
            s3.upload_file(str(source), bucket, key)

            content = models.Content(
                organization_id=user.organization_id,
                name="Cloud Video",
                type="video",
                status="processing",
                file_url=f"s3://{key}",
                file_size_bytes=source.stat().st_size,
            )
            db.add(content)
            db.commit()
            db.refresh(content)
            content_id = content.id

            process_media_sync(content_id)

            db.expire_all()
            c = db.query(models.Content).filter(models.Content.id == content_id).first()
            assert c.status == "ready", f"transcode failed: {c.failed_reason}"
            assert c.failed_reason is None
            assert len(c.renditions) == 4, "every rendition must be produced from a bucket source"

            stored = {o["Key"] for o in s3.list_objects_v2(Bucket=bucket).get("Contents", [])}
            for rendition in c.renditions:
                assert rendition.file_url.startswith("s3://"), (
                    "a rendition of an s3 original must be stored back in the bucket, or "
                    "the player is handed a path that does not exist on this host"
                )
                assert media_storage.storage_key_for(rendition.file_url) in stored
                assert rendition.sha256 and rendition.file_size_bytes > 0, (
                    "the player verifies the file it downloads against these"
                )

            assert c.thumbnail and c.thumbnail.startswith("s3://")
            assert media_storage.storage_key_for(c.thumbnail) in stored
    finally:
        backend.worker.SessionLocal = original_session_local
        if previous_key is None:
            os.environ.pop("AWS_ACCESS_KEY_ID", None)
        else:
            os.environ["AWS_ACCESS_KEY_ID"] = previous_key
        db.close()
        test_engine.dispose()
