"""End-to-end smoke test for Olrac Signage backend.

Tests the full loop:
  register/login → upload content → request-code → pair → playlist →
  /screens/me → heartbeat → playback log → report

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --base-url http://localhost:8000

Exit code: 0 if all PASS, 1 if any fail.
"""
import argparse
import io
import os
import struct
import time
import zlib

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = f"smoke+{int(time.time())}@olrac.com"
ADMIN_PASSWORD = "smoketest123"
ADMIN_NAME = "Smoke Tester"
PNG_BYTES = None
STEP = 1


def _make_png() -> bytes:
    """Generate a tiny valid PNG in memory."""
    global PNG_BYTES
    if PNG_BYTES is not None:
        return PNG_BYTES

    width, height = 2, 2
    raw = b""
    for y in range(height):
        raw += b"\x00"  # filter byte
        for x in range(width):
            raw += b"\xff\x00\x00\xff"  # RGBA red pixel

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", idat)
    png += chunk(b"IEND", b"")
    PNG_BYTES = png
    return png


def log(status: str, msg: str):
    print(f"  {status}  {msg}")


def check(label: str, ok_flag: bool, detail: str = ""):
    global STEP
    status = "PASS" if ok_flag else "FAIL"
    msg = f"Step {STEP}: {label}"
    if detail:
        msg += f" — {detail}"
    log(status, msg)
    if not ok_flag:
        exit(1)
    STEP += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    base = args.base_url
    client = httpx.Client(timeout=30)

    access_token = None
    screen_token = None
    screen_id = None
    content_id = None

    print(f"\nOlrac Smoke Test — {base}\n")

    # ── 1. Register (idempotent) ────────────────────────────────────────

    r = client.post(
        f"{base}/auth/register",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": ADMIN_NAME},
    )
    if r.status_code == 200:
        data = r.json()["data"]
        check("Register", True, f"created {data['email']}")
    elif r.status_code == 409:
        check("Register (idempotent)", True, "already exists")
    else:
        check("Register", False, f"{r.status_code} {r.text}")

    # ── 2. Login → capture access_token ─────────────────────────────────

    r = client.post(
        f"{base}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    if r.status_code == 200:
        data = r.json()["data"]
        access_token = data["access_token"]
        check("Login", bool(access_token), f"token starts {access_token[:20]}...")
    else:
        check("Login", False, f"{r.status_code} {r.text}")

    headers = {"Authorization": f"Bearer {access_token}"}

    # ── 3. Upload content ───────────────────────────────────────────────

    png = _make_png()
    files = {"file": ("smoke-test.png", png, "image/png")}
    r = client.post(f"{base}/content/upload", files=files, headers=headers)
    if r.status_code == 200:
        content_id = r.json()["data"]["id"]
        check("Upload content", True, f"content_id={content_id}")
    else:
        check("Upload content", False, f"{r.status_code} {r.text}")

    # ── 4. Request pairing code ─────────────────────────────────────────

    r = client.post(f"{base}/screens/request-code")
    if r.status_code == 200:
        data = r.json()["data"]
        code = data["code"]
        screen_token = data["screen_token"]
        check("Request pairing code", True, f"code={code} token={screen_token[:12]}...")
    else:
        check("Request pairing code", False, f"{r.status_code} {r.text}")

    # ── 5. Pair screen ──────────────────────────────────────────────────

    r = client.post(
        f"{base}/screens/pair",
        json={"code": code, "name": "Smoke Screen", "orientation": "D90"},
        headers=headers,
    )
    if r.status_code == 200:
        screen_id = r.json()["data"]["id"]
        check("Pair screen", True, f"screen_id={screen_id} orientation=D90")
    else:
        check("Pair screen", False, f"{r.status_code} {r.text}")

    # ── 6. Build playlist ───────────────────────────────────────────────

    r = client.put(
        f"{base}/screens/{screen_id}/playlist",
        json={"items": [{"content_id": content_id, "position": 0}]},
        headers=headers,
    )
    if r.status_code == 200:
        items = r.json()["data"]
        check("Build playlist", len(items) == 1, f"{len(items)} item(s)")
    else:
        check("Build playlist", False, f"{r.status_code} {r.text}")

    # ── 7. GET /screens/me with screen_token ────────────────────────────

    time.sleep(0.5)  # let DB settle
    r = client.get(
        f"{base}/screens/me",
        headers={"Authorization": f"Bearer {screen_token}"},
    )
    if r.status_code == 200:
        data = r.json()["data"]
        status = data["screen"]["status"]
        playlist_len = len(data["playlist"])
        check(
            "GET /screens/me",
            status in ("online", "offline") and playlist_len >= 1,
            f"status={status} playlist_items={playlist_len}",
        )
    else:
        check("GET /screens/me", False, f"{r.status_code} {r.text}")

    # ── 8. Heartbeat ────────────────────────────────────────────────────

    r = client.post(
        f"{base}/screens/{screen_id}/heartbeat",
        headers={"Authorization": f"Bearer {screen_token}"},
    )
    if r.status_code == 200:
        check("Heartbeat", True, "screen now online")
    else:
        check("Heartbeat", False, f"{r.status_code} {r.text}")

    # ── 9. Playback log ─────────────────────────────────────────────────

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    r = client.post(
        f"{base}/playback/log",
        json=[{"content_id": content_id, "played_at": now, "duration_played": 8}],
        headers={"Authorization": f"Bearer {screen_token}"},
    )
    if r.status_code == 200:
        inserted = r.json()["data"]["inserted"]
        check("Playback log", inserted == 1, f"inserted={inserted}")
    else:
        check("Playback log", False, f"{r.status_code} {r.text}")

    # ── 10. Reports summary ─────────────────────────────────────────────

    r = client.get(f"{base}/reports/summary", headers=headers)
    if r.status_code == 200:
        rows = r.json()["data"]
        check(
            "Reports summary",
            len(rows) >= 1 and rows[0]["play_count"] >= 1,
            f"{len(rows)} row(s), top play_count={rows[0]['play_count'] if rows else 0}",
        )
    else:
        check("Reports summary", False, f"{r.status_code} {r.text}")

    # ── 11. CSV export ──────────────────────────────────────────────────

    r = client.get(f"{base}/reports/export?type=summary", headers=headers)
    if r.status_code == 200:
        csv_text = r.text
        check("CSV export", "content_id" in csv_text and "play_count" in csv_text, f"{len(csv_text)} bytes")
    else:
        check("CSV export", False, f"{r.status_code} {r.text}")

    print(f"\n{'='*50}")
    print(f"ALL {STEP - 1} STEPS PASSED")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
