"""A websocket must not hold a database connection open for its whole life.

Both websocket handlers took `db: Session = Depends(database.get_db)` and used it once, to
check a token, before entering a loop that runs until the client disconnects. A dependency
generator is only torn down when the handler *returns*, so each open socket kept one
connection checked out of the pool having run a single query.

Every screen in the fleet holds one of these sockets permanently. On SQLAlchemy's default
pool -- 5 plus 10 overflow -- the sixteenth screen to connect exhausted it, and because
heartbeat, playlist sync and play-log ingestion share that pool, unrelated screens then
started failing with `QueuePool limit reached`. A hundred-screen deployment could never
have got past fifteen.

The assertion here is deliberately about the pool rather than about a screen count: it
holds whatever the pool is sized to, and it fails the moment a connection is pinned again.

Run directly:  python tests/test_ws_connection_pool.py
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB = "olrac_test_ws_pool"
TEMP_DIR = tempfile.TemporaryDirectory(prefix="olrac-ws-pool-")


def _database_url() -> str:
    """Postgres when a server is there, SQLite otherwise -- as the other scripts do."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        admin = psycopg2.connect(
            "postgresql://postgres:postgres@localhost:5432/postgres", connect_timeout=3
        )
        admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        admin.cursor().execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
        admin.cursor().execute(f"CREATE DATABASE {TEST_DB} OWNER olrac")
        admin.close()
        return f"postgresql://olrac:olrac_password@localhost:5432/{TEST_DB}"
    except Exception:
        return f"sqlite:///{Path(TEMP_DIR.name) / 'ws_pool.db'}"


os.environ["DATABASE_URL"] = _database_url()
os.environ["SECRET_KEY"] = "testsecret"
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis://localhost:6379/1")
os.environ["AWS_ACCESS_KEY_ID"] = "mock"
os.environ["AWS_SECRET_ACCESS_KEY"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend import database  # noqa: E402
from backend.database import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models import Organization, Screen, utcnow  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"])
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
# The handlers no longer take Depends(get_db); they call database.SessionLocal() directly,
# so that is what has to point at this database.
database.SessionLocal = TestingSessionLocal

client = TestClient(app)

# Comfortably more than the old 5 + 10 ceiling: if a connection were still pinned per
# socket, the pool would be exhausted long before the last one opened.
SCREENS = 25


def redis_reachable() -> bool:
    import socket

    probe = socket.socket()
    probe.settimeout(2)
    try:
        probe.connect(("127.0.0.1", 6379))
        return True
    except OSError:
        return False
    finally:
        probe.close()


def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    org = Organization(name="Pool Org", slug="pool-org")
    db.add(org)
    db.commit()
    db.refresh(org)

    for index in range(SCREENS):
        db.add(Screen(
            name=f"Panel {index}",
            organization_id=org.id,
            device_id=f"pool-tv-{index}",
            # No secret, so verify_device_token accepts the handshake without a token and
            # this stays a test about the pool rather than about auth.
            device_secret_hash=None,
            approved_at=utcnow(),
        ))
    db.commit()
    db.close()


def run() -> None:
    if not redis_reachable():
        # The handler subscribes to Redis immediately after accepting, so without it this
        # would fail for a reason that has nothing to do with what is being tested.
        print("ws connection pool: SKIPPED (Redis is not reachable on localhost:6379)")
        return

    setup_db()
    pool = engine.pool

    baseline = pool.checkedout()
    sockets = []
    try:
        for index in range(SCREENS):
            socket_cm = client.websocket_connect(f"/api/ws/pool-tv-{index}/ws")
            sockets.append(socket_cm)
            socket_cm.__enter__()

            held = pool.checkedout() - baseline
            assert held == 0, (
                f"{index + 1} open sockets are holding {held} database connection(s); "
                "a websocket must not keep one checked out for its lifetime"
            )
    finally:
        for socket_cm in reversed(sockets):
            try:
                socket_cm.__exit__(None, None, None)
            except Exception:
                pass

    # And nothing leaked on the way back out.
    assert pool.checkedout() - baseline == 0, "connections were left checked out after close"


if __name__ == "__main__":
    run()
    print("ws connection pool: all checks passed")
