"""A TV that comes back after a FACTORY RESET must reconnect, not duplicate.

A reinstall keeps the hardware identity (installation_id survives, so `test_screen_reconnect`
matches on it). A factory reset does not: on a TV that hides its serial, installation_id is
derived from ANDROID_ID, and a reset changes ANDROID_ID -- so the same panel returns with a
brand new identity and, before this, a brand new screen row, stranding its ads and history.

The only signal left is the hardware model. So at pairing, if the workspace has exactly one
non-live screen of the same model, that is treated as this TV coming back and reconnected.

What this pins:
  * a factory-reset TV (new device_id AND new installation_id) reclaims the one offline
    same-model screen instead of creating a duplicate, and keeps its id and playlist
  * two offline look-alikes are ambiguous -> a fresh screen, never a wrong merge
  * a same-model screen that is still ONLINE is never merged into (it is a different, live TV)
"""
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-freset-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-factory-reset")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.billing import ensure_billing_catalog  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402
from backend.main import app  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []
MODEL = "2K D5STV"


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def setup():
    db = database.SessionLocal()
    ensure_billing_catalog(db)
    org = models.Organization(name="Venue Co", slug=f"v-{uuid.uuid4().hex[:8]}", status="active")
    db.add(org)
    db.flush()
    db.add(models.User(
        organization_id=org.id, username="owner", email=f"o-{uuid.uuid4().hex[:6]}@v.test",
        hashed_password=get_password_hash("x"), role="owner", is_active=True,
    ))
    db.commit()
    org_id = org.id
    db.close()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'owner'})}"}
    return client, headers, org_id


def register(client, device_id, installation_id, model=MODEL):
    return client.post("/api/screens/register", json={
        "device_id": device_id,
        "installation_id": installation_id,
        "identity_source": "android_id",  # a TV whose serial is hidden -> ANDROID_ID
        "device_model": model,
        "manufacturer": "KONKA",
    })


def pair(client, headers, pair_code):
    return client.post("/api/screens/pair", headers=headers, json={"pair_code": pair_code})


def set_status(screen_id, status):
    db = database.SessionLocal()
    db.query(models.Screen).filter(models.Screen.id == screen_id).update({"status": status})
    db.commit()
    db.close()


def pair_new(client, headers, device_id, installation_id, model=MODEL):
    """Register a fresh identity and pair it, returning the pair response json."""
    reg = register(client, device_id, installation_id, model)
    check(reg.status_code == 200, f"register failed: {reg.text}")
    return pair(client, headers, reg.json()["pair_code"])


def run() -> None:
    client, headers, org_id = setup()

    # --- first pairing of the KONKA -----------------------------------------------------
    paired = pair_new(client, headers, "dev-old", "hw_OLD")
    check(paired.status_code == 200, f"first pairing failed: {paired.text}")
    screen_id = paired.json()["id"]
    playlist_id = paired.json().get("playlist_id")

    # Factory reset: the panel stops checking in and goes offline.
    set_status(screen_id, "offline")

    # --- factory reset: NEW device_id AND NEW installation_id, same model ---------------
    back = pair_new(client, headers, "dev-new", "hw_NEW")
    check(back.status_code == 200, f"reconnect pairing failed: {back.text}")
    check(back.json()["id"] == screen_id,
          f"factory-reset TV came back as a different screen ({back.json()['id']} != {screen_id})")
    check(back.json().get("playlist_id") == playlist_id,
          "reconnected screen must keep its playlist (and the ads on it)")

    db = database.SessionLocal()
    live = db.query(models.Screen).filter(
        models.Screen.model == MODEL, models.Screen.deleted_at.is_(None)
    ).all()
    check(len(live) == 1, f"factory reset created a duplicate ({len(live)} same-model screens)")
    check(live[0].device_id == "dev-new", "reclaimed screen must adopt the new device id")
    check(bool(back.json().get("device_secret")), "reconnected screen must be handed a credential")
    db.close()

    # --- ambiguity: two offline look-alikes -> a fresh screen, never a wrong merge ------
    # Add a second offline KONKA, then factory-reset-pair a third. Two candidates => new screen.
    second = pair_new(client, headers, "dev-second", "hw_SECOND")
    check(second.status_code == 200, f"second KONKA pairing failed: {second.text}")
    set_status(screen_id, "offline")
    set_status(second.json()["id"], "offline")

    third = pair_new(client, headers, "dev-third", "hw_THIRD")
    check(third.status_code == 200, f"third pairing failed: {third.text}")
    check(third.json()["id"] not in (screen_id, second.json()["id"]),
          "with two offline look-alikes the TV must NOT be merged into one of them")

    # --- never merge into a screen that is still online ---------------------------------
    # Reset both existing to a clean state: one online, and pair a same-model TV.
    set_status(screen_id, "online")
    set_status(second.json()["id"], "online")
    set_status(third.json()["id"], "online")
    online_only = pair_new(client, headers, "dev-fourth", "hw_FOURTH")
    check(online_only.json()["id"] not in (screen_id, second.json()["id"], third.json()["id"]),
          "a same-model screen that is still ONLINE must never be merged into")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("FACTORY RESET RECONNECT FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - a factory-reset TV reconnects to its one same-model screen, and never merges ambiguously")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
