"""P8 Media Selection checks: python tests/test_media_selection.py"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

TEST_DB = "olrac_test_media_selection"
try:
    _admin = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
    _admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    _admin.cursor().execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
    _admin.cursor().execute(f"CREATE DATABASE {TEST_DB} OWNER olrac")
    _admin.close()
except Exception:
    pass

os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{TEST_DB}"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.models import User, Organization, Screen, Playlist, PlaylistItem, Content, MediaRendition, utcnow
from backend.routers.auth import get_password_hash
from backend.routers.screens import verify_device_auth

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    org = Organization(name="Test Org", slug="test-org")
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Create test content
    content = Content(
        organization_id=org.id,
        name="test video",
        type="video",
        status="ready",
        file_url="http://original/vid.mp4",
        sha256="original-hash",
        file_size_bytes=1000000
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    
    # Rendition 1080p
    rend_1080 = MediaRendition(
        content_id=content.id,
        resolution="1080p",
        width=1920, height=1080,
        codec="hevc",
        file_url="http://rendition/1080.mp4",
        sha256="1080-hash",
        file_size_bytes=500000
    )
    # Rendition 720p
    rend_720 = MediaRendition(
        content_id=content.id,
        resolution="720p",
        width=1280, height=720,
        codec="h264",
        file_url="http://rendition/720.mp4",
        sha256="720-hash",
        file_size_bytes=250000
    )
    # Rendition Portrait (e.g. 720x1280)
    rend_portrait = MediaRendition(
        content_id=content.id,
        resolution="720p_portrait",
        width=720, height=1280,
        codec="h264",
        file_url="http://rendition/720_portrait.mp4",
        sha256="portrait-hash",
        file_size_bytes=200000
    )
    db.add_all([rend_1080, rend_720, rend_portrait])
    
    playlist = Playlist(name="Main PL", organization_id=org.id)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    
    p_item = PlaylistItem(playlist_id=playlist.id, content_id=content.id, duration=10, order=0)
    db.add(p_item)
    db.commit()
    
    # Create a screen
    # approved_at: a fixture stands for a screen already live in the field. Screens
    # default to pending, so without this the sync gate correctly returns no playlist.
    screen = Screen(name="Test Screen", organization_id=org.id, playlist_id=playlist.id, device_id="testdev", device_secret_hash="hash", approved_at=utcnow())
    db.add(screen)
    db.commit()
    db.refresh(screen)
    
    screen_id = screen.id
    org_id = org.id
    db.close()
    return screen_id, org_id

def mock_auth(screen_id: int):
    # Instead of bypassing everything, we can just mock the dependency if we want, or mock the token.
    # Actually, we can just insert a valid screen, or just override verify_device_auth.
    pass

def test_media_selection():
    screen_id, org_id = setup_db()
    
    from jose import jwt
    device_token = jwt.encode({"sub": f"device:testdev"}, os.getenv("SECRET_KEY"), algorithm="HS256")
    headers = {"Authorization": f"Bearer {device_token}"}

    # 1. No capabilities -> 720p
    res = client.get("/api/screens/testdev/sync", headers=headers)
    if res.status_code != 200:
        print("Failed sync:", res.status_code, res.text)
    assert res.status_code == 200
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    assert item["content"]["file_url"] == "http://rendition/720.mp4"
    assert item["content"]["sha256"] == "720-hash"
    assert item["content"]["file_size_bytes"] == 250000
    
    # 2. HEVC excluded when unsupported
    db = TestingSessionLocal()
    s = db.query(Screen).filter(Screen.id == screen_id).first()
    s.screen_width = 1920
    s.screen_height = 1080
    s.supported_video_codecs = ["video/avc"]  # h264 only, no HEVC
    s.total_ram_mb = 2048
    s.max_decode_width = 1920
    s.max_decode_height = 1080
    db.commit()
    db.close()
    
    res = client.get("/api/screens/testdev/sync", headers=headers)
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    # Should fall back to 720p because 1080p is HEVC which is unsupported
    assert item["content"]["file_url"] == "http://rendition/720.mp4"

    # 3. HEVC supported -> 1080p
    db = TestingSessionLocal()
    s = db.query(Screen).filter(Screen.id == screen_id).first()
    s.supported_video_codecs = ["video/avc", "video/hevc"]
    db.commit()
    db.close()
    
    res = client.get("/api/screens/testdev/sync", headers=headers)
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    assert item["content"]["file_url"] == "http://rendition/1080.mp4"
    
    # 4. 1 GB RAM capped at 720p
    db = TestingSessionLocal()
    s = db.query(Screen).filter(Screen.id == screen_id).first()
    s.total_ram_mb = 1024
    db.commit()
    db.close()
    
    res = client.get("/api/screens/testdev/sync", headers=headers)
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    assert item["content"]["file_url"] == "http://rendition/720.mp4"
    
    # 5. Portrait preserved (screen is 720x1280)
    db = TestingSessionLocal()
    s = db.query(Screen).filter(Screen.id == screen_id).first()
    s.screen_width = 720
    s.screen_height = 1280
    s.total_ram_mb = 2048
    s.max_decode_width = 1920
    s.max_decode_height = 1920
    db.commit()
    db.close()
    
    res = client.get("/api/screens/testdev/sync", headers=headers)
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    assert item["content"]["file_url"] == "http://rendition/720_portrait.mp4"
    
    # 6. No renditions -> original
    db = TestingSessionLocal()
    s = db.query(Screen).filter(Screen.id == screen_id).first()
    s.screen_width = 1920
    s.screen_height = 1080
    
    c = db.query(Content).first()
    # Delete renditions
    db.query(MediaRendition).filter(MediaRendition.content_id == c.id).delete()
    db.commit()
    db.close()
    
    res = client.get("/api/screens/testdev/sync", headers=headers)
    playlist = res.json()["playlist"]
    item = playlist["items"][0]
    assert item["content"]["file_url"] == "http://original/vid.mp4"
    assert item["content"]["sha256"] == "original-hash"
    assert item["content"]["file_size_bytes"] == 1000000

    print("All media selection tests passed.")

def test_a_constrained_panel_is_never_handed_the_master():
    """Filtering everything out must not fall through to the biggest file we own.

    When every rendition was ruled out, select_rendition returned None and the caller in
    sync_tv then left content.file_url alone -- which is the ORIGINAL MASTER, the single
    largest and heaviest asset in the library. So the panels least able to decode anything
    were handed the hardest file, while one capable TV played the same advert fine. That is
    the "it only plays on one television" report.

    Four ordinary set-ups empty the list, none of them exotic.
    """
    from types import SimpleNamespace
    from backend.media_selection import select_rendition

    def rendition(width, height, codec="h264"):
        return SimpleNamespace(width=width, height=height, codec=codec,
                               file_size_bytes=width * height, sha256=f"{width}x{height}",
                               file_url=f"s3://r-{width}x{height}.mp4")

    def panel(**overrides):
        base = dict(screen_width=1920, screen_height=1080, supported_video_codecs=["video/avc"],
                    max_decode_width=1920, max_decode_height=1080, total_ram_mb=2048)
        base.update(overrides)
        return SimpleNamespace(**base)

    cases = [
        ("a 720p panel offered only 1080p and above",
         [rendition(1920, 1080), rendition(2560, 1440)],
         panel(screen_width=1280, screen_height=720, total_ram_mb=1024)),
        ("a portrait panel offered only landscape renditions",
         [rendition(1280, 720), rendition(1920, 1080)],
         panel(screen_width=1080, screen_height=1920)),
        ("a portrait advert taller than a landscape panel",
         [rendition(1080, 1920)],
         panel()),
        ("a panel whose codec list matches nothing we hold",
         [rendition(1280, 720), rendition(1920, 1080)],
         panel(supported_video_codecs=["video/hevc"])),
    ]
    for label, renditions, screen in cases:
        chosen = select_rendition(SimpleNamespace(renditions=renditions), screen)
        assert chosen is not None, f"{label}: fell through to the full-size master"
        # The smallest on offer: closer to playable than the master, which is larger still.
        assert chosen.file_url == min(
            renditions, key=lambda r: r.width * r.height
        ).file_url, f"{label}: expected the smallest rendition, got {chosen.file_url}"

    # A content with no renditions at all still has nothing to choose, and the caller's
    # fallback to the original is correct there -- case 6 of the suite above depends on it.
    assert select_rendition(SimpleNamespace(renditions=[]), panel()) is None
    print("  ok  a constrained panel gets the smallest rendition, never the master")


if __name__ == "__main__":
    test_a_constrained_panel_is_never_handed_the_master()
    test_media_selection()
