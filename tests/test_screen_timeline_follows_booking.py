"""A screen's timeline follows the booking: add and remove freely, never twice, never past the plan.

What an operator does on the screen page:
  * an advert that is already booked goes onto another screen with no new sale -- it joins
    the booking it has, and takes that booking's window;
  * removing it from a screen stops it THERE, and it stays gone. The trash button used to
    delete only the playlist item, the booking's target was left with nothing, and the
    supervisor's repair loop put the advert straight back within a tick;
  * the booking itself, and every other screen it runs on, is untouched by that removal;
  * it can be put back while the booking runs, but never twice on one screen, and never onto
    more screens than the plan sold;
  * an ordinary (unbooked) item is still just deleted.
"""
import os
import pathlib
import sys
import tempfile
import uuid
from datetime import timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-follow-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-timeline-follows-booking")
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
    screens = [models.Screen(organization_id=org.id, device_id=f"tv-{n}", status="online") for n in range(3)]
    booked = models.Content(organization_id=org.id, name="Booked ad", file_url="/uploads/a.mp4", type="video", status="ready")
    ended = models.Content(organization_id=org.id, name="Ended ad", file_url="/uploads/b.mp4", type="video", status="ready")
    plain = models.Content(organization_id=org.id, name="House loop", file_url="/uploads/c.png", type="image", status="ready")
    # Two screens sold: the third add has to be refused.
    plan = models.TenantPlan(organization_id=org.id, name="Duo", duration_days=30, max_locations=2, price_paise=1000)
    db.add_all([*screens, booked, ended, plain, plan])
    db.commit()
    ids = {"screens": [s.id for s in screens], "booked": booked.id, "ended": ended.id, "plain": plain.id, "plan": plan.id}
    db.close()
    return ids


def items_on(client, headers, screen_id):
    screen = next(s for s in client.get("/api/screens/", headers=headers).json() if s["id"] == screen_id)
    playlist_id = screen.get("playlist_id") or screen.get("effective_playlist_id")
    if not playlist_id:
        return None, []
    playlist = client.get(f"/api/playlists/{playlist_id}", headers=headers).json()
    return playlist_id, playlist.get("items", [])


def run() -> None:
    ids = setup()
    s1, s2, s3 = ids["screens"]
    client = TestClient(app)
    owner = {"Authorization": f"Bearer {create_access_token({'sub': 'owner'})}"}
    now = models.utcnow()

    booking = client.post("/api/placements/", headers=owner, json={
        "content_id": ids["booked"], "advertiser": "Acme", "plan_id": ids["plan"],
        "starts_at": (now - timedelta(days=1)).isoformat(),
        "targets": [{"screen_id": s1}],
    })
    check(booking.status_code == 201, f"booking failed: {booking.status_code} {booking.text}")
    if booking.status_code != 201:
        return
    placement_id = booking.json()["id"]

    # --- a booked advert joins another screen with no new sale ---------------------------
    added = client.post(f"/api/placements/{placement_id}/targets", headers=owner, json={"screen_id": s2})
    check(added.status_code == 201, f"adding a booked advert to a second screen failed: {added.text}")
    bookings = client.get(f"/api/placements/?content_id={ids['booked']}", headers=owner).json()
    check(len(bookings) == 1, f"adding a screen created another booking: {len(bookings)} bookings")

    playlist_id, items = items_on(client, owner, s2)
    item = next((i for i in items if i["content"]["id"] == ids["booked"]), None)
    check(item is not None, "the booked advert did not reach the second screen's timeline")
    if item is None:
        return
    check(item.get("end_at") is not None, "the added screen did not take the booking's window")

    # --- removing it stops it on that screen, and it STAYS gone ---------------------------
    removed = client.delete(f"/api/playlists/{playlist_id}/items/{item['id']}", headers=owner)
    check(removed.status_code == 200, f"removing the advert failed: {removed.status_code} {removed.text}")

    db = database.SessionLocal()
    from backend.services import reconcile_unplaced_bookings
    reconcile_unplaced_bookings(db)
    db.close()

    _, items_after = items_on(client, owner, s2)
    check(all(i["content"]["id"] != ids["booked"] for i in items_after),
          "the supervisor put a removed advert back onto the screen")
    placement = client.get(f"/api/placements/?content_id={ids['booked']}", headers=owner).json()[0]
    check([t["screen_id"] for t in placement["targets"]] == [s1],
          f"removal did not end exactly that screen's run: targets {[t['screen_id'] for t in placement['targets']]}")

    # --- the booking and its other screen are untouched ----------------------------------
    _, items_s1 = items_on(client, owner, s1)
    check(any(i["content"]["id"] == ids["booked"] for i in items_s1),
          "removing from one screen took the advert off another")

    # --- it can come back, but never twice, and never past the plan -----------------------
    again = client.post(f"/api/placements/{placement_id}/targets", headers=owner, json={"screen_id": s2})
    check(again.status_code == 201, f"re-adding while the booking runs failed: {again.text}")
    twice = client.post(f"/api/placements/{placement_id}/targets", headers=owner, json={"screen_id": s2})
    check(twice.status_code == 409, f"the same advert went onto one screen twice: {twice.status_code}")
    over = client.post(f"/api/placements/{placement_id}/targets", headers=owner, json={"screen_id": s3})
    check(over.status_code == 409 and "plan" in over.json().get("detail", "").lower(),
          f"a third screen was allowed on a two-screen plan: {over.status_code} {over.text}")

    # --- an ordinary item is still simply deleted ----------------------------------------
    plain_pl, _ = items_on(client, owner, s1)
    plain_add = client.post(f"/api/playlists/{plain_pl}/items", headers=owner,
                            json={"content_id": ids["plain"], "duration": 10, "order": 99})
    if plain_add.status_code in (200, 201):
        plain_item = next(i for i in client.get(f"/api/playlists/{plain_pl}", headers=owner).json()["items"]
                          if i["content"]["id"] == ids["plain"])
        gone = client.delete(f"/api/playlists/{plain_pl}/items/{plain_item['id']}", headers=owner)
        check(gone.status_code == 200, f"an unbooked item could not be removed: {gone.text}")

    # --- a finished booking reads as finished, so the library offers it as Not booked -----
    past = client.post("/api/placements/", headers=owner, json={
        "content_id": ids["ended"], "advertiser": "Old",
        "starts_at": (now - timedelta(days=40)).isoformat(),
        "ends_at": (now - timedelta(days=10)).isoformat(),
        "targets": [],
    })
    if past.status_code == 201:
        content = next(c for c in client.get("/api/content/", headers=owner).json() if c["id"] == ids["ended"])
        ends = content.get("placement_ends_at")
        check(ends is not None and ends < now.isoformat(),
              f"an ended booking did not report a past end, so it would still show as Booked: {ends}")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("TIMELINE / BOOKING FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - a screen's timeline follows its booking: add, remove, never twice, never past the plan")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
