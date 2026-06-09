"""Idempotent script to create the default admin user.

Usage:
    python scripts/seed_admin.py

Custom URL:
    python scripts/seed_admin.py --base-url http://localhost:8000
"""
import argparse
import httpx

BASE_URL = "http://localhost:8000"
EMAIL = "admin@olrac.com"
PASSWORD = "admin123"
NAME = "Admin"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()

    url = f"{args.base_url}/auth/register"
    payload = {"email": EMAIL, "password": PASSWORD, "name": NAME}

    resp = httpx.post(url, json=payload, timeout=15)

    if resp.status_code == 200:
        data = resp.json()
        print(f"PASS  Registered admin: {data['data']['email']} (id={data['data']['id']})")
    elif resp.status_code == 409:
        print(f"PASS  Admin already exists (idempotent) — {EMAIL}")
    else:
        body = resp.json()
        err = body.get("error", {})
        print(f"FAIL  {resp.status_code} — {err.get('message', 'unknown')}")
        exit(1)

    # Verify we can log in
    login_resp = httpx.post(
        f"{args.base_url}/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    if login_resp.status_code == 200:
        data = login_resp.json()
        token = data["data"]["access_token"][:20]
        print(f"PASS  Login successful — access_token starts with {token}...")
    else:
        print(f"FAIL  Login failed: {login_resp.text}")
        exit(1)


if __name__ == "__main__":
    main()
