import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from backend.database import SessionLocal
from backend import models

def main():
    db = SessionLocal()
    org = db.query(models.Organization).filter(models.Organization.id == 19).first()
    if not org:
        org = models.Organization(id=19, name="Roshan Nandhu's Workspace", slug="org-7d0fcab0", status="active")
        db.add(org)
        db.commit()

    # Clear old screen 1 if exists under wrong org
    s_old = db.query(models.Screen).filter(models.Screen.id == 1).first()
    if s_old:
        s_old.device_id = "71f564d8-8391-45a5-9e69-c99cf84803ce"
        s_old.organization_id = 19
        s_old.status = "online"
        s_old.last_seen = models.utcnow()
        screen = s_old
    else:
        screen = models.Screen(
            id=1,
            organization_id=19,
            device_id="71f564d8-8391-45a5-9e69-c99cf84803ce",
            installation_id="hw_b27e091bace1ab5a_Lenovo_TB-8505F",
            name="Lenovo TB-8505F Tablet",
            status="online",
            last_seen=models.utcnow(),
            approved_at=models.utcnow(),
        )
        db.add(screen)
    db.flush()

    content = models.Content(
        organization_id=19,
        name="Real Proof Video Ad",
        type="video/mp4",
        file_url="/uploads/demo/demo_reel_a0222a14.mp4",
        duration_ms=10000,
        status="ready",
        file_size_bytes=2965649,
    )
    db.add(content)
    db.flush()

    playlist = models.Playlist(organization_id=19, name="Tablet Live Playlist")
    db.add(playlist)
    db.flush()

    item = models.PlaylistItem(playlist_id=playlist.id, content_id=content.id, order=0, duration=10)
    db.add(item)
    db.flush()

    screen.playlist_id = playlist.id
    screen.assignment_updated_at = models.utcnow()
    db.commit()

    print(f"Setup complete! Screen ID: {screen.id}, Playlist ID: {playlist.id}, Content ID: {content.id}")
    db.close()

if __name__ == "__main__":
    main()
