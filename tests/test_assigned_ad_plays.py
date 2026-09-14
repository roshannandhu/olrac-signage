"""An advert booked onto a screen has to reach that screen and be playable.

Selling a campaign is the product. Every step between the booking dialog and a pixel on the
wall is load-bearing, and each one has failed at least once:

  * the booking has to write a playlist item (it provisions the playlist if the TV has none)
  * the playlist's marker has to move, or /sync answers 204 and the TV learns nothing
  * the item has to survive the sync filter that drops finished campaigns
  * the window the TV is given has to be OPEN NOW, not at midnight, not in five hours

That last one is the quiet one. The player decides what to show from `start_at`/`end_at`
alone, so an item delivered with a start in the future is downloaded, cached, and not
played -- which looks exactly like "I assigned the ad and nothing happened".
"""
import os
import pathlib
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-assign-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-assigned-ad")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def setup():
    db = database.SessionLocal()
    org = models.Organization(name="Venue", slug=f"v-{uuid.uuid4().hex[:8]}", status="active")
    db.add(org)
    db.flush()
    db.add(models.User(organization_id=org.id, username="owner", email="ow@x.t",
                       hashed_password=get_password_hash("x"), role="owner", is_active=True))
    # A freshly paired TV: no playlist of its own, no group. The booking has to provision one,
    # which is the path the dashboard relies on and the one most likely to be wrong.
    screen = models.Screen(organization_id=org.id, device_id="tv-assign", status="online")
    content = models.Content(organization_id=org.id, name="Advert",
                             file_url="/uploads/ad.mp4", type="video", status="ready")
    db.add_all([screen, content])
    db.flush()
    from backend.services import issue_device_secret
    secret = issue_device_secret(screen)
    ids = (screen.id, content.id)
    db.commit()
    db.close()
    return ids, secret


def playlist_from_sync(client, secret):
    auth = client.post("/api/screens/auth",
                       json={"device_id": "tv-assign", "device_secret": secret})
    assert auth.status_code == 200, f"device auth failed: {auth.text}"
    token = auth.json()["access_token"]
    response = client.get("/api/screens/tv-assign/sync",
                          headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, f"sync failed: {response.status_code} {response.text}"
    return response.json()


def run() -> None:
    (screen_id, content_id), secret = setup()
    client = TestClient(app)
    owner = {"Authorization": f"Bearer {create_access_token({'sub': 'owner'})}"}

    # What the dashboard actually sends: the booking starts at LOCAL midnight today, which
    # is how a date input serialises. Depending on the timezone that instant is up to a day
    # either side of "now" -- both sides have to work.
    today_local_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    starts_at = today_local_midnight.astimezone().astimezone(timezone.utc)

    created = client.post("/api/placements/", headers=owner, json={
        "content_id": content_id,
        "advertiser": "Acme",
        "price_paise": 10000,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": screen_id}],
    })
    check(created.status_code == 201, f"booking the advert failed: {created.status_code} {created.text}")
    if created.status_code != 201:
        return

    body = playlist_from_sync(client, secret)
    playlist = body.get("playlist")
    check(playlist is not None, "the screen was sent no playlist at all after a booking")
    if not playlist:
        return

    items = playlist.get("items") or []
    check(any(i["content"]["id"] == content_id for i in items),
          f"the booked advert never reached the screen; got {[i['content']['id'] for i in items]}")
    if not items:
        return

    item = next(i for i in items if i["content"]["id"] == content_id)

    # The whole point. The player plays from these two fields and nothing else, so a window
    # that opens later means a screen that shows nothing now.
    now = models.utcnow()
    start = datetime.fromisoformat(item["start_at"]) if item.get("start_at") else None
    end = datetime.fromisoformat(item["end_at"]) if item.get("end_at") else None
    check(start is None or start <= now,
          f"the advert is not due to start until {start} -- the screen will sit idle until then")
    check(end is None or end > now, f"the advert was delivered already finished: ends {end}")

    # An offset, always. The player falls back to parsing a bare timestamp as LOCAL wall
    # time, so a naive one is read 5h30m off in IST and the campaign starts a working day
    # late. Serialising aware is what keeps that fallback from ever being reached.
    for field in ("start_at", "end_at"):
        value = item.get(field)
        check(value is None or value.endswith("Z") or "+" in value[10:] or "-" in value[10:],
              f"{field} was sent without a timezone ({value!r}); the player reads it as local time")

    # Nothing to play with: an item whose media has no URL renders a black screen.
    check(bool(item["content"].get("file_url")), "the advert reached the screen with no media URL")

    # --- and it has to KEEP arriving -----------------------------------------------------
    # The screen asks "anything since X?" on every sync. If the booking did not move the
    # playlist's marker the answer is 204 forever and a second booking never lands.
    second = client.post("/api/placements/", headers=owner, json={
        "content_id": content_id,
        "advertiser": "Acme Two",
        "price_paise": 10000,
        "starts_at": starts_at.isoformat(),
        "ends_at": (starts_at + timedelta(days=30)).isoformat(),
        "targets": [{"screen_id": screen_id}],
    })
    check(second.status_code == 201, f"second booking failed: {second.text}")

    auth = client.post("/api/screens/auth",
                       json={"device_id": "tv-assign", "device_secret": secret})
    token = auth.json()["access_token"]
    since = body["playlist_updated_at"]
    refreshed = client.get(f"/api/screens/tv-assign/sync?since={since}",
                           headers={"Authorization": f"Bearer {token}"})
    check(refreshed.status_code == 200,
          f"a screen that had already synced was told nothing changed ({refreshed.status_code}) "
          "after a new advert was booked onto it")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("ASSIGNED AD FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - a booked advert reaches the screen inside an open window")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
