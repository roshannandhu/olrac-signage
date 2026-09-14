"""A screen that comes back must come back as itself, however it was claimed.

Reinstalling the player wipes SharedPreferences: the device id, the device credential, the
cached playlist. The hardware identity survives, and that is what the server matches on --
otherwise the TV returns as a brand new screen, which costs a duplicate row, another slot of
the plan's screen quota, and strands the playlist and play history on a screen that no longer
exists.

What this pins:
  * a reinstalled panel is recognised and handed its screen back, with its credential re-issued
  * it works the same whether the screen was first claimed by pairing code or by Google,
    because recovery keys on hardware, never on how it was claimed
  * a caller holding only a device id CANNOT get a credential issued to it
  * removing the screen from the dashboard is the one thing that does wipe it, and the panel
    then comes back as a fresh one asking to be paired
  * identity strength is recorded, so an operator can see which screens survive a wipe
"""
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-reconnect-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-screen-reconnect")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "mock")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mock")
# The re-issue guard has a legacy branch for screens with no recorded hardware identity.
# Off, so this file exercises the posture the product is migrating TO.
os.environ["ALLOW_LEGACY_DEVICE_AUTH"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.billing import ensure_billing_catalog  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []
HARDWARE = "sn_ABC123DEF456"


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
        organization_id=org.id, username="owner", email="o@v.test",
        hashed_password=get_password_hash("x"), role="owner", is_active=True,
    ))
    db.commit()
    org_id = org.id
    db.close()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'owner'})}"}
    return client, headers, org_id


def register(client, device_id, *, installation_id=HARDWARE, identity="serial", model="TB-8505F"):
    return client.post("/api/screens/register", json={
        "device_id": device_id,
        "installation_id": installation_id,
        "identity_source": identity,
        "device_model": model,
        "manufacturer": "Lenovo",
    })


def run() -> None:
    client, headers, org_id = setup()

    # --- claimed by pairing code -------------------------------------------------------
    first = register(client, "tv-boot-1")
    check(first.status_code == 200, f"register failed: {first.text}")
    check(first.json()["status"] == "waiting_pairing", "a new TV should wait to be paired")

    db = database.SessionLocal()
    fresh = db.query(models.Screen).filter(models.Screen.device_id == "tv-boot-1").one()
    check(fresh.model == "TB-8505F",
          "a waiting panel must already report its model, or the operator redeeming a code "
          "cannot tell which TV it is")
    check(fresh.identity_source == "serial", f"identity source not recorded: {fresh.identity_source}")
    db.close()

    paired = client.post("/api/screens/pair", headers=headers,
                         json={"pair_code": first.json()["pair_code"]})
    check(paired.status_code == 200, f"pairing failed: {paired.text}")
    screen_id = paired.json()["id"]
    check(paired.json().get("device_secret"), "pairing must hand the TV a credential")

    # --- reinstall: new device id, same hardware ---------------------------------------
    # Reinstalling regenerates the stored device id while the hardware identity is unchanged.
    again = register(client, "tv-boot-1-reinstalled")
    check(again.status_code == 200, f"re-register failed: {again.text}")
    check(again.json()["status"] != "waiting_pairing",
          "a reinstalled panel was asked to pair again instead of being recognised")
    check(bool(again.json().get("device_secret")),
          "a recognised panel must be re-issued a credential, or it cannot authenticate")

    db = database.SessionLocal()
    rows = db.query(models.Screen).filter(
        models.Screen.installation_id == HARDWARE, models.Screen.deleted_at.is_(None)
    ).all()
    check(len(rows) == 1, f"reinstalling created a duplicate screen ({len(rows)} rows)")
    check(rows[0].id == screen_id, "the panel came back as a different screen")
    check(rows[0].device_id == "tv-boot-1-reinstalled", "the reclaimed row kept the old device id")
    db.close()

    # --- a stranger holding only a device id gets nothing -------------------------------
    impostor = client.post("/api/screens/register", json={"device_id": "tv-boot-1-reinstalled"})
    check(impostor.status_code == 200, "register should still answer")
    check(not impostor.json().get("device_secret"),
          "SECURITY: a caller with only a device id was issued the screen's credential")

    wrong_hardware = register(client, "tv-boot-1-reinstalled", installation_id="sn_SOMEONE_ELSE")
    check(not wrong_hardware.json().get("device_secret"),
          "SECURITY: a mismatched hardware identity was issued a credential")

    # --- removing the screen is the one thing that wipes it -----------------------------
    removed = client.delete(f"/api/screens/{screen_id}", headers=headers)
    check(removed.status_code in (200, 204), f"removing the screen failed: {removed.status_code}")

    after_removal = register(client, "tv-boot-1-reinstalled")
    check(after_removal.json()["status"] == "waiting_pairing",
          "a removed screen must come back as a fresh panel asking to pair")
    check(bool(after_removal.json().get("pair_code")),
          "a removed screen must be offered a new pairing code")

    db = database.SessionLocal()
    archived = db.query(models.Screen).filter(models.Screen.id == screen_id).one()
    check(archived.deleted_at is not None, "removal should archive the screen, not delete it")
    check(archived.device_secret_hash is None, "removal must revoke the credential")
    live = db.query(models.Screen).filter(
        models.Screen.installation_id == HARDWARE, models.Screen.deleted_at.is_(None)
    ).count()
    check(live == 1, f"expected exactly one fresh row after removal, found {live}")
    db.close()

    # --- claimed by Google recovers identically ------------------------------------------
    # The route differs; the recovery does not, because it keys on hardware.
    google_hw = "hw_9f8e7d6c"
    started = register(client, "tv-google-1", installation_id=google_hw, identity="android_id")
    check(started.status_code == 200, "google-path register failed")
    db = database.SessionLocal()
    row = db.query(models.Screen).filter(models.Screen.device_id == "tv-google-1").one()
    # Bind it the way the Google callback does: straight onto the workspace.
    row.organization_id = org_id
    row.status = "offline"
    row.pair_code = None
    db.commit()
    db.close()

    back = register(client, "tv-google-1-reinstalled", installation_id=google_hw, identity="android_id")
    check(back.json()["status"] != "waiting_pairing",
          "a Google-claimed panel was not recognised after reinstall")
    db = database.SessionLocal()
    count = db.query(models.Screen).filter(
        models.Screen.installation_id == google_hw, models.Screen.deleted_at.is_(None)
    ).count()
    check(count == 1, f"the Google-claimed panel duplicated on reinstall ({count} rows)")
    db.close()


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("SCREEN RECONNECT FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - a reinstalled screen comes back as itself, and only removal wipes it")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
