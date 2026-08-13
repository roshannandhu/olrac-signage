"""Adversarial cross-tenant probe: python tests/test_tenant_isolation.py

Two organisations, two owners. Every admin endpoint is called by org A's owner
against org B's resource ids. A leak here means one customer can read or mutate
another customer's screens, media, playlists, or users — the worst failure mode
this product has — so the probe covers every mutating route, not a sample.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ignore_cleanup_errors: Windows keeps the SQLite handle open past interpreter exit.
TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-tenant-test-", ignore_cleanup_errors=True)
DB_PATH = Path(TEMP_DIR.name) / "tenant.db"
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
test_db_name = f"olrac_test_{DB_PATH.stem.replace('-', '_')}"
try:
    conn = psycopg2.connect("postgresql://postgres:postgres@localhost:5432/postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    conn.cursor().execute(f"DROP DATABASE IF EXISTS {test_db_name}")
    conn.cursor().execute(f"CREATE DATABASE {test_db_name} OWNER olrac")
    conn.close()
except Exception as e:
    pass
os.environ["DATABASE_URL"] = f"postgresql://olrac:olrac_password@localhost:5432/{test_db_name}"
os.environ["SECRET_KEY"] = "tenant-test-secret-key-not-for-production"
os.environ["INITIAL_ADMIN_USERNAME"] = "owner-a"
os.environ["INITIAL_ADMIN_PASSWORD"] = "password-a-123"
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"
os.environ["PAYMENT_PROVIDER"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from backend import database, models  # noqa: E402
from backend.main import app  # noqa: E402
from backend.routers.auth import get_password_hash  # noqa: E402

DENIED = {401, 403, 404}


def auth_header(client, username, password):
    response = client.post("/api/auth/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"login failed for {username}: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def build_org_b(db):
    org = models.Organization(name="Org B", slug="org-b")
    db.add(org)
    db.commit()
    db.refresh(org)
    user = models.User(username="owner-b", hashed_password=get_password_hash("password-b-123"),
                       role="owner", is_active=True, organization_id=org.id)
    content = models.Content(organization_id=org.id, name="B secret asset", type="image",
                             file_url="http://localhost:8000/uploads/b-secret.png")
    playlist = models.Playlist(organization_id=org.id, name="B private loop")
    group = models.ScreenGroup(organization_id=org.id, name="B group")
    screen = models.Screen(organization_id=org.id, device_id="device-b-1", status="offline")
    db.add_all([user, content, playlist, group, screen])
    db.commit()
    for row in (user, content, playlist, group, screen):
        db.refresh(row)
    item = models.PlaylistItem(playlist_id=playlist.id, content_id=content.id, duration=10, order=0)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"org": org.id, "user": user.id, "content": content.id,
            "playlist": playlist.id, "group": group.id, "screen": screen.id, "item": item.id}


def run():
    failures = []

    with TestClient(app) as client:
        db = database.SessionLocal()
        try:
            b = build_org_b(db)
        finally:
            db.close()

        a = auth_header(client, "owner-a", "password-a-123")
        b_hdr = auth_header(client, "owner-b", "password-b-123")
        own = client.get(f"/api/playlists/{b['playlist']}", headers=b_hdr)
        assert own.status_code == 200, f"org B cannot read its own playlist: {own.text}"

        # 1. Listing must not disclose org B rows
        listings = [("/api/content/", b["content"]), ("/api/playlists/", b["playlist"]),
                    ("/api/groups/", b["group"]), ("/api/screens/", b["screen"]),
                    ("/api/users/", b["user"])]
        for path, leaked_id in listings:
            response = client.get(path, headers=a)
            if response.status_code != 200:
                failures.append(f"GET {path} as A returned {response.status_code}")
                continue
            ids = {row.get("id") for row in response.json()}
            if leaked_id in ids:
                failures.append(f"LEAK: GET {path} exposed org B id={leaked_id}")

        # 2. Direct-id probes across every admin route
        probes = [
            ("PUT", f"/api/content/{b['content']}", {"json": {"name": "hijacked", "tags": None}}),
            ("DELETE", f"/api/content/{b['content']}", {}),
            ("GET", f"/api/playlists/{b['playlist']}", {}),
            ("PUT", f"/api/playlists/{b['playlist']}", {"json": {"name": "hijacked"}}),
            ("DELETE", f"/api/playlists/{b['playlist']}", {}),
            ("POST", f"/api/playlists/{b['playlist']}/items",
             {"json": {"content_id": b["content"], "duration": 5, "order": 0}}),
            ("PUT", f"/api/playlists/{b['playlist']}/items/reorder", {"json": [b["item"]]}),
            ("PUT", f"/api/playlists/{b['playlist']}/items/{b['item']}", {"json": {"duration": 99}}),
            ("DELETE", f"/api/playlists/{b['playlist']}/items/{b['item']}", {}),
            ("PUT", f"/api/playlists/{b['playlist']}/transitions",
             {"json": {"transition": "fade", "transition_ms": 500, "apply_to_all": True}}),
            ("PUT", f"/api/groups/{b['group']}", {"json": {"name": "hijacked"}}),
            ("DELETE", f"/api/groups/{b['group']}", {}),
            ("POST", f"/api/groups/{b['group']}/assign/{b['playlist']}", {}),
            ("PUT", f"/api/groups/{b['group']}/screens", {"json": {"screen_ids": [b["screen"]]}}),
            ("PUT", f"/api/screens/{b['screen']}", {"json": {"name": "hijacked", "orientation": 0}}),
            ("POST", f"/api/screens/{b['screen']}/assign/{b['playlist']}", {}),
            ("DELETE", f"/api/screens/{b['screen']}/assign", {}),
            ("PUT", f"/api/users/{b['user']}", {"json": {"role": "viewer"}}),
            ("DELETE", f"/api/users/{b['user']}", {}),
        ]
        for method, path, kwargs in probes:
            response = client.request(method, path, headers=a, **kwargs)
            if response.status_code == 422:
                failures.append(f"INVALID PROBE: {method} {path} returned 422 body={response.text[:120]}")
            elif response.status_code not in DENIED:
                failures.append(f"LEAK: {method} {path} as org A returned {response.status_code} body={response.text[:120]}")

        # 3. Cross-tenant media reuse
        own_playlist = client.post("/api/playlists/", headers=a, json={"name": "A loop"})
        assert own_playlist.status_code == 201, own_playlist.text
        a_playlist = own_playlist.json()["id"]
        borrow = client.post(f"/api/playlists/{a_playlist}/items", headers=a,
                             json={"content_id": b["content"], "duration": 5, "order": 0})
        if borrow.status_code not in DENIED:
            failures.append(f"LEAK: org A attached org B content ({borrow.status_code})")

        # 4. TV must not sync foreign playlist
        db = database.SessionLocal()
        try:
            screen_b = db.query(models.Screen).filter(models.Screen.id == b["screen"]).one()
            screen_b.playlist_id = b["playlist"]
            db.commit()
            device_b = screen_b.device_id
        finally:
            db.close()
        sync = client.get(f"/api/screens/{device_b}/sync")
        if sync.status_code == 200 and sync.json().get("playlist"):
            name = sync.json()["playlist"]["name"]
            if name != "B private loop":
                failures.append(f"LEAK: device B synced foreign playlist {name!r}")

        # 5. Enrollment must not re-home another org device
        db = database.SessionLocal()
        try:
            org_a_id = db.query(models.User).filter(
                models.User.username == "owner-a").one().organization_id
            db.add_all([
                models.EnrollmentToken(organization_id=org_a_id, token="isolation-token-a", is_active=True),
                models.EnrollmentToken(organization_id=b["org"], token="isolation-token-b", is_active=True),
            ])
            db.commit()
        finally:
            db.close()

        enrolled = client.post("/api/screens/enroll", json={
            "device_id": "isolation-victim-tv", "enrollment_token": "isolation-token-a",
            "installation_id": "site-a"})
        if enrolled.status_code != 200:
            failures.append(f"setup: org A enrol failed ({enrolled.status_code})")
        else:
            victim_secret = enrolled.json()["device_secret"]
            hijack = client.post("/api/screens/enroll", json={
                "device_id": "isolation-victim-tv", "enrollment_token": "isolation-token-b",
                "installation_id": "attacker"})
            if hijack.status_code == 200:
                failures.append("LEAK: org B re-enrolled org A's device — cross-tenant screen hijack")
            db = database.SessionLocal()
            try:
                victim = db.query(models.Screen).filter(
                    models.Screen.device_id == "isolation-victim-tv").one()
                if victim.organization_id != org_a_id:
                    failures.append(f"LEAK: device moved to org {victim.organization_id}")
            finally:
                db.close()
            still_valid = client.post("/api/screens/auth", json={
                "device_id": "isolation-victim-tv", "device_secret": victim_secret})
            if still_valid.status_code != 200:
                failures.append("DoS: org A's device secret was invalidated by foreign enrollment")

        # 6. Device JWT cross-tenant: JWT for tv-a must not authorize sync for tv-b (enrolled)
        enroll_a = client.post("/api/screens/enroll", json={
            "device_id": "cross-tenant-tv-a", "enrollment_token": "isolation-token-a"})
        if enroll_a.status_code != 200:
            failures.append(f"setup: enrol cross-tenant-tv-a failed ({enroll_a.status_code})")
        else:
            auth_a = client.post("/api/screens/auth", json={
                "device_id": "cross-tenant-tv-a",
                "device_secret": enroll_a.json()["device_secret"]})
            jwt_a = {"Authorization": f"Bearer {auth_a.json()['access_token']}"}
            enroll_b2 = client.post("/api/screens/enroll", json={
                "device_id": "cross-tenant-tv-b", "enrollment_token": "isolation-token-b"})
            if enroll_b2.status_code == 200:
                b2_sync = client.get("/api/screens/cross-tenant-tv-b/sync", headers=jwt_a)
                if b2_sync.status_code == 200:
                    failures.append(
                        "LEAK: org A JWT (sub=cross-tenant-tv-a) authorised sync for cross-tenant-tv-b")

        # 7. Revoked device: /auth must 401 once secret_hash is cleared
        enroll_r = client.post("/api/screens/enroll", json={
            "device_id": "revoke-test-tv", "enrollment_token": "isolation-token-a"})
        if enroll_r.status_code != 200:
            failures.append(f"setup: enrol revoke-test-tv failed ({enroll_r.status_code})")
        else:
            revoke_secret = enroll_r.json()["device_secret"]
            db = database.SessionLocal()
            try:
                s = db.query(models.Screen).filter(models.Screen.device_id == "revoke-test-tv").one()
                s.device_secret_hash = None
                db.commit()
            finally:
                db.close()
            post_revoke = client.post("/api/screens/auth", json={
                "device_id": "revoke-test-tv", "device_secret": revoke_secret})
            if post_revoke.status_code == 200:
                failures.append("SECURITY: /auth succeeded after device_secret_hash cleared")

        # 8. Expired token must be denied
        db = database.SessionLocal()
        try:
            from datetime import timedelta
            db.add(models.EnrollmentToken(
                organization_id=org_a_id, token="expired-token-a", is_active=True,
                expires_at=models.utcnow() - timedelta(hours=1)))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        if client.post("/api/screens/enroll", json={
                "device_id": "expired-token-tv", "enrollment_token": "expired-token-a"
        }).status_code == 200:
            failures.append("SECURITY: enrollment succeeded with an expired token")

        # 9. Revoked token (is_active=False) must be denied
        db = database.SessionLocal()
        try:
            db.add(models.EnrollmentToken(
                organization_id=org_a_id, token="revoked-token-a", is_active=False))
            db.commit()
        finally:
            db.close()
        if client.post("/api/screens/enroll", json={
                "device_id": "revoked-token-tv", "enrollment_token": "revoked-token-a"
        }).status_code == 200:
            failures.append("SECURITY: enrollment succeeded with a revoked token")

        # 10. Over-quota org must be denied
        db = database.SessionLocal()
        try:
            zero_plan = db.query(models.Plan).filter_by(slug="zero-screen-plan").first()
            if not zero_plan:
                zero_plan = models.Plan(name="Zero Screen", slug="zero-screen-plan",
                                        max_screens=0, max_storage_bytes=1 << 30)
                db.add(zero_plan)
                db.flush()
            quota_org = db.query(models.Organization).filter_by(slug="quota-org").first()
            if not quota_org:
                quota_org = models.Organization(
                    name="Quota Org", slug="quota-org", plan_id=zero_plan.id)
                db.add(quota_org)
                db.flush()
            db.add(models.EnrollmentToken(
                organization_id=quota_org.id, token="quota-token", is_active=True))
            db.commit()
        except Exception as exc:
            db.rollback()
            failures.append(f"setup: over-quota fixture failed: {exc}")
        finally:
            db.close()
        if client.post("/api/screens/enroll", json={
                "device_id": "quota-test-tv", "enrollment_token": "quota-token"
        }).status_code == 200:
            failures.append("SECURITY: enrollment succeeded for an over-quota organization")

        # 11. Cross-org device_id steal (explicit named probe)
        if client.post("/api/screens/enroll", json={
                "device_id": "isolation-victim-tv", "enrollment_token": "isolation-token-b"
        }).status_code == 200:
            failures.append("SECURITY: cross-org device_id steal succeeded (probe 11)")

        # 12. Max-uses exhausted token must be denied
        db = database.SessionLocal()
        try:
            db.add(models.EnrollmentToken(
                organization_id=org_a_id, token="maxed-token-a",
                is_active=True, max_uses=2, use_count=2))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        if client.post("/api/screens/enroll", json={
                "device_id": "maxed-token-tv", "enrollment_token": "maxed-token-a"
        }).status_code == 200:
            failures.append("SECURITY: enrollment succeeded with a max-uses-exhausted token")

        # 13. PlayLog Batch cross-tenant injection
        # TV A (jwt_a) tries to post logs for TV B (b["screen"]) and Org B (b["org"])
        if 'jwt_a' in locals():
            batch_payload = {
                "screen_id": b["screen"],
                "organization_id": b["org"],
                "events": [{
                    "event_id": "malicious-event-1",
                    "device_started_at": "2026-08-01T00:00:00Z",
                    "device_finished_at": "2026-08-01T00:00:10Z",
                    "corrected_started_at": "2026-08-01T00:00:00Z",
                    "corrected_finished_at": "2026-08-01T00:00:10Z",
                    "duration_ms": 10000,
                    "status": "completed"
                }]
            }
            batch_resp = client.post("/api/screens/play-logs/batch", json=batch_payload, headers=jwt_a)
            if batch_resp.status_code == 200:
                failures.append("SECURITY: TV A successfully injected a play log batch for TV B / Org B")

        # 14-18. Sign-in on the TV binds a screen using account credentials, so it is a
        # publicly reachable authentication endpoint with none of require_tenant_roles'
        # protection. Every guard has to hold here or it is a way into any workspace.
        signin = lambda body: client.post("/api/screens/sign-in", json=body)  # noqa: E731

        # 14. Wrong password must not bind anything.
        if signin({"username": "owner-a", "password": "wrong-password",
                   "device_id": "signin-probe-tv"}).status_code == 200:
            failures.append("SECURITY: TV sign-in succeeded with a wrong password")

        # 15. Unknown user must not bind anything.
        if signin({"username": "does-not-exist", "password": "password-a-123",
                   "device_id": "signin-probe-tv"}).status_code == 200:
            failures.append("SECURITY: TV sign-in succeeded for a non-existent user")

        # 16. A viewer can read the dashboard but must not add screens.
        db = database.SessionLocal()
        try:
            from backend.routers.auth import get_password_hash
            db.add(models.User(username="viewer-a", hashed_password=get_password_hash("viewer-password-123"),
                               role="viewer", organization_id=org_a_id, is_active=True))
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        if signin({"username": "viewer-a", "password": "viewer-password-123",
                   "device_id": "signin-viewer-tv"}).status_code == 200:
            failures.append("SECURITY: a viewer signed a screen into the workspace")

        # 17. Org B's owner must not re-home a device already owned by org A.
        if signin({"username": "owner-b", "password": "password-b-123",
                   "device_id": "isolation-victim-tv"}).status_code == 200:
            failures.append("SECURITY: TV sign-in re-homed another organisation's device")
        db = database.SessionLocal()
        try:
            victim = db.query(models.Screen).filter(
                models.Screen.device_id == "isolation-victim-tv").first()
            if victim and victim.organization_id != org_a_id:
                failures.append(f"LEAK: sign-in moved org A's device to org {victim.organization_id}")
        finally:
            db.close()

        # 18. A successful sign-in must invalidate the pairing code it was issued, so a
        # code shown on screen earlier cannot later be redeemed by somebody else.
        registered = client.post("/api/screens/register", json={"device_id": "signin-claims-tv"})
        stale_code = registered.json().get("pair_code") if registered.status_code == 200 else None
        claimed = signin({"username": "owner-a", "password": "password-a-123",
                          "device_id": "signin-claims-tv", "name": "Reception TV"})
        if claimed.status_code != 200:
            failures.append(f"setup: owner sign-in failed ({claimed.status_code}) body={claimed.text[:120]}")
        elif claimed.json().get("name") != "Reception TV":
            failures.append(f"sign-in ignored the submitted screen name: {claimed.json().get('name')!r}")
        if stale_code and client.post("/api/screens/pair", headers=b_hdr,
                                      json={"pair_code": stale_code}).status_code == 200:
            failures.append("SECURITY: a pairing code stayed redeemable after the device signed in")

        # 19. A 422 must never echo the submitted credential back. FastAPI's default
        # validation body includes the offending input, so a mistyped sign-in returned the
        # operator's plaintext password to the caller and into any log of that response.
        secret = "do-not-echo-this-password"
        malformed = client.post("/api/screens/sign-in",
                                json={"username": "owner-a", "password": secret})  # no device_id
        if malformed.status_code != 422:
            failures.append(f"expected 422 for a malformed sign-in, got {malformed.status_code}")
        if secret in malformed.text:
            failures.append("SECURITY: a validation error echoed the submitted password back to the caller")
        for path, body in (
            ("/api/users/", {"username": "x", "password": secret}),
            ("/api/provisioning/qr", {"wifi_ssid": "x", "wifi_password": secret, "max_uses": "not-a-number"}),
        ):
            response = client.post(path, headers=a, json=body)
            if secret in response.text:
                failures.append(f"SECURITY: {path} echoed a submitted secret back ({response.status_code})")

    if failures:
        print("TENANT ISOLATION FAILURES:")
        for line in failures:
            print("  -", line)
        raise SystemExit(1)
    print("Tenant isolation probe passed: no cross-organisation access on any admin route")


if __name__ == "__main__":
    run()

