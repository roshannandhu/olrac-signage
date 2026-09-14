"""Publishing a player build must reach screens whose content has not changed.

`/sync` answers 204 with an empty body when nothing is new, and the player reads the update
offer out of that body. The freshness marker was built only from playlist, group and
assignment timestamps, so a screen with settled content was told "nothing new" for ever and
never learned a newer APK existed. Publishing a release moved no television at all -- which
is why `app_releases` was found empty in production with a fleet running hand-installed
builds, and why nobody had noticed the over-the-air path had never worked end to end.

The screens most likely to be left behind were the healthiest ones: a panel playing a stable
loop is exactly the one whose marker never moves.
"""
import os
import pathlib
import sys
import tempfile
import uuid
from datetime import timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-ota-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-ota")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def run() -> None:
    client = TestClient(app)
    db = database.SessionLocal()

    org = models.Organization(name="Venue", slug=f"v-{uuid.uuid4().hex[:8]}", status="active")
    db.add(org)
    db.flush()
    playlist = models.Playlist(organization_id=org.id, name="Loop")
    db.add(playlist)
    db.flush()
    settled = models.utcnow() - timedelta(days=3)
    screen = models.Screen(
        organization_id=org.id, device_id="ota-tv", status="online",
        playlist_id=playlist.id, assignment_updated_at=settled, last_seen=settled,
    )
    db.add(screen)
    db.commit()
    # A screen whose content has not moved in days -- the ordinary healthy case.
    playlist.updated_at = settled
    db.commit()
    db.close()

    since = (models.utcnow() - timedelta(hours=1)).isoformat()

    quiet = client.get("/api/screens/ota-tv/sync", params={"since": since})
    check(quiet.status_code == 204,
          f"a settled screen should be told nothing changed, got {quiet.status_code}")

    # Publish a build, the way the release flow does.
    db = database.SessionLocal()
    db.add(models.AppRelease(
        version_code=99, version_name="9.9.9",
        apk_url="https://example.test/player.apk",
        sha256="a" * 64, mandatory=True, rollout_state="released",
    ))
    db.commit()
    db.close()

    offered = client.get("/api/screens/ota-tv/sync", params={"since": since})
    check(offered.status_code == 200,
          f"publishing a build must make the next sync fresh, got {offered.status_code} -- "
          "on 204 the body is empty and the player never sees the update")
    if offered.status_code == 200:
        version = offered.json().get("app_version")
        check(version is not None, "the sync body carried no app_version")
        check(version and version.get("version_code") == 99,
              f"wrong build offered: {version}")
        check(version and version.get("sha256") == "a" * 64,
              "the digest must travel with the offer, or the player refuses to install")

    # And it settles again: once the screen has taken the new marker, it is back on 204
    # rather than being handed a full playlist on every sync for ever.
    if offered.status_code == 200:
        new_marker = offered.json().get("playlist_updated_at") or models.utcnow().isoformat()
        again = client.get("/api/screens/ota-tv/sync", params={"since": new_marker})
        check(again.status_code == 204,
              f"after taking the offer the screen should settle back to 204, got {again.status_code}")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("OTA DELIVERY FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - publishing a build reaches a screen whose content never changes")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
