"""Pre-deployment environment check.

    backend\\venv\\Scripts\\python.exe scripts/preflight.py

Reports EVERY problem in one pass and exits non-zero if any are fatal. An earlier version
exited on the first failure, which meant a deployer fixed one thing, re-ran, hit the next,
and needed up to seven round trips to learn what was wrong.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import redis
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"[FAIL] {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"[WARN] {msg}")


def ok(msg: str) -> None:
    print(f"[ OK ] {msg}")


def main() -> int:
    print("Preflight checks\n")
    load_dotenv(os.path.join(ROOT, "backend", ".env"))

    secret = os.getenv("SECRET_KEY", "")
    if not secret or secret == "replace-with-a-long-random-secret":
        fail("SECRET_KEY is unset or still the example value — anyone can forge a session token.")
    elif len(secret) < 32:
        warn(f"SECRET_KEY is only {len(secret)} characters; use at least 32 random bytes.")
    else:
        ok("SECRET_KEY is configured.")

    base_url = os.getenv("PUBLIC_BASE_URL", "")
    if not base_url:
        fail("PUBLIC_BASE_URL is not set — TVs would receive unusable media URLs.")
    elif "localhost" in base_url or "127.0.0.1" in base_url:
        fail(f"PUBLIC_BASE_URL points at {base_url}. A TV cannot resolve that; use a public address.")
    else:
        ok(f"PUBLIC_BASE_URL is {base_url}")

    if os.getenv("AWS_ACCESS_KEY_ID", "") == "mock":
        warn(
            "Storage is LOCAL (AWS_ACCESS_KEY_ID=mock): single host only, requires the "
            "shared uploads_data volume, and large files are served through the API. "
            "Configure Cloudflare R2 before scaling past one backend."
        )
    else:
        ok("Cloud storage (R2/S3) is configured.")

    try:
        retention = int(os.getenv("PLAY_LOG_RETENTION_DAYS", "180"))
        if retention < 90:
            warn(
                f"PLAY_LOG_RETENTION_DAYS={retention}. Proof-of-play is billing evidence in "
                "advertiser disputes; 90+ days is safer."
            )
        else:
            ok(f"Play-log retention is {retention} days.")
    except ValueError:
        fail("PLAY_LOG_RETENTION_DAYS is not a number.")

    # Database. Everything below needs a live connection, so skip rather than crash.
    conn = None
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        fail("DATABASE_URL is not set.")
    else:
        try:
            engine = create_engine(db_url, connect_args={"connect_timeout": 5})
            conn = engine.connect()
            conn.execute(text("SELECT 1"))
            ok("Postgres is reachable.")
        except Exception as exc:
            fail(f"Cannot connect to Postgres: {exc}")

    try:
        redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379"), socket_timeout=5
        ).ping()
        ok("Redis is reachable.")
    except Exception as exc:
        # Non-fatal by design: presence and push degrade to polling, and the API stays up.
        warn(f"Redis unreachable ({exc}). Presence and realtime push fall back to polling.")

    if conn is not None:
        try:
            current = MigrationContext.configure(conn).get_current_heads()
            script = ScriptDirectory.from_config(
                Config(os.path.join(ROOT, "backend", "alembic.ini"))
            )
            head = script.get_current_head()
            if head not in current:
                fail(f"Schema out of date. Database at {current}, migrations at {head}. Run alembic upgrade head.")
            else:
                ok(f"Schema is current ({head}).")
        except Exception as exc:
            fail(f"Could not verify migrations: {exc}")

        try:
            owners = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE role = 'owner'")
            ).scalar()
            if not owners:
                fail("No owner account exists. Create one with: python -m backend.seed_admin <username>")
            else:
                ok(f"{owners} owner account(s) present.")
        except Exception as exc:
            fail(f"Could not query users: {exc}")
    else:
        warn("Skipped schema and owner checks — no database connection.")

    print()
    if failures:
        print(f"{len(failures)} blocking problem(s), {len(warnings)} warning(s). Not ready for production.")
        return 1
    if warnings:
        print(f"No blocking problems, {len(warnings)} warning(s). Review them before going live.")
        return 0
    print("All preflight checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
