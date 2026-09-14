"""Storage credentials set from the admin console, overriding the server's environment.

The environment is not always reachable by the person who needs to change it. This product
ran for days with `AWS_ACCESS_KEY_ID=mock` -- a value indistinguishable from an unconfigured
one -- while its operator edited that variable on a second Render service and watched nothing
change. The console is a place they can always reach.

What this pins:
  * a key typed into the console beats a placeholder in the environment, with no restart
  * the secret is never readable back out, from any route
  * clearing a setting falls back to the environment rather than leaving a blank
  * only a platform operator can see or set any of it
"""
import os
import pathlib
import sys
import tempfile
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_db_file = pathlib.Path(tempfile.gettempdir()) / f"olrac-stset-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ.setdefault("SECRET_KEY", "pytest-storage-settings")
# Exactly the production state this exists to rescue: set, non-blank, and meaning nothing.
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.media_urls import apply_storage_overrides, is_s3_enabled  # noqa: E402
from backend.routers.auth import create_access_token, get_password_hash  # noqa: E402

models.Base.metadata.create_all(bind=database.engine)

FAILURES: list[str] = []
# Shaped like a real key and belonging to nobody. An actual one was used here at first,
# which is precisely the mistake tests/test_no_embedded_credentials.py exists to catch --
# and it did not, because the guard looks for assignments to credential NAMES and this was
# assigned to FAKE_KEY.
FAKE_KEY = "0" * 32
FAKE_SECRET = "s" * 64


def check(condition: bool, message: str) -> None:
    if not condition:
        FAILURES.append(message)


def setup():
    db = database.SessionLocal()
    op = models.Organization(name="OLRAC", slug=f"o-{uuid.uuid4().hex[:8]}", status="active")
    tenant = models.Organization(name="T", slug=f"t-{uuid.uuid4().hex[:8]}", status="active")
    db.add_all([op, tenant])
    db.flush()
    db.add(models.User(organization_id=op.id, username="operator", email="op@x.t",
                       hashed_password=get_password_hash("x"), role="super_admin", is_active=True))
    db.add(models.User(organization_id=tenant.id, username="tenant-owner", email="t@x.t",
                       hashed_password=get_password_hash("x"), role="owner", is_active=True))
    db.commit()
    db.close()
    return (
        TestClient(app),
        {"Authorization": f"Bearer {create_access_token({'sub': 'operator'})}"},
        {"Authorization": f"Bearer {create_access_token({'sub': 'tenant-owner'})}"},
    )


def run() -> None:
    client, admin, owner = setup()
    apply_storage_overrides({})  # start from the environment alone

    check(not is_s3_enabled(), "precondition: a 'mock' environment must read as unconfigured")

    before = client.get("/api/admin/storage/settings", headers=admin)
    check(before.status_code == 200, f"reading settings failed: {before.text}")
    check(before.json()["storage_enabled"] is False, "storage should not be enabled yet")

    saved = client.put("/api/admin/storage/settings", headers=admin, json={
        "access_key_id": FAKE_KEY,
        "secret_access_key": FAKE_SECRET,
        "bucket": "olrac",
    })
    check(saved.status_code == 200, f"saving settings failed: {saved.text}")
    body = saved.json()

    # The whole point: live immediately, no restart, over a placeholder environment.
    check(is_s3_enabled(), "a key set from the console did not take effect")
    check(body["storage_enabled"] is True, "the response did not report storage as enabled")
    check("AWS_ACCESS_KEY_ID" in body["from_console"],
          f"the console should own the key now: {body['from_console']}")
    check(body["bucket"] == "olrac", f"bucket not applied: {body['bucket']}")

    # The secret must not come back, from this route or any other.
    check(body["secret_is_set"] is True, "the secret should be reported as set")
    check(FAKE_SECRET not in saved.text, "SECURITY: the secret was returned by the save route")
    fetched = client.get("/api/admin/storage/settings", headers=admin)
    check(FAKE_SECRET not in fetched.text, "SECURITY: the secret was returned by the read route")
    check(FAKE_KEY not in fetched.text,
          "the full key id should be masked; only the last characters are useful")
    check(fetched.json()["access_key_id"].endswith(FAKE_KEY[-4:]),
          "the mask should still identify WHICH key is in use")

    # Health is public. It must never grow a value, only names.
    health = client.get("/api/health")
    check(FAKE_SECRET not in health.text and FAKE_KEY not in health.text,
          "SECURITY: a storage credential reached the public health endpoint")

    # Clearing falls back to the environment rather than leaving a hole.
    cleared = client.put("/api/admin/storage/settings", headers=admin, json={
        "access_key_id": "", "secret_access_key": "", "bucket": "",
    })
    check(cleared.status_code == 200, f"clearing failed: {cleared.text}")
    check(cleared.json()["storage_enabled"] is False,
          "clearing should fall back to the environment, which is still 'mock'")
    check(cleared.json()["from_console"] == [],
          f"nothing should be owned by the console now: {cleared.json()['from_console']}")

    # Only a platform operator.
    for method, path in (("get", "/api/admin/storage/settings"),
                         ("put", "/api/admin/storage/settings"),
                         ("post", "/api/admin/storage/settings/test")):
        call = getattr(client, method)
        extra = {} if method == "get" else {"json": {}}
        refused = call(path, headers=owner, **extra)
        check(refused.status_code == 403,
              f"a tenant owner reached {method.upper()} {path}: {refused.status_code}")
        anonymous = call(path, **extra)
        check(anonymous.status_code in (401, 403),
              f"an anonymous caller reached {method.upper()} {path}: {anonymous.status_code}")


if __name__ == "__main__":
    try:
        run()
        if FAILURES:
            print("STORAGE SETTINGS FAILURES:")
            for failure in FAILURES:
                print("  -", failure)
            raise SystemExit(1)
        print("OK - the console can set storage credentials, and never hands them back")
    finally:
        database.engine.dispose()
        _db_file.unlink(missing_ok=True)
