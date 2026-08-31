import asyncio
import logging
import os
import re
import pathlib
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from .limiter import limiter

from . import database, models
from .billing import ensure_billing_catalog
from .database import Base, engine

logger = logging.getLogger(__name__)

def _ensure_schema() -> None:
    """Build the schema on a brand-new database, and stamp it so Alembic can take over.

    `create_all()` used to run here unconditionally. On a database that already exists
    that is a harmless no-op, which is why nobody noticed -- but on a NEW one it built
    every table straight from the ORM and left no alembic_version row, so the first
    `alembic upgrade head` died on "relation users already exists" and the database could
    never be migrated again. Deploying to a fresh Postgres (Supabase, Neon, a new RDS) was
    a one-way trip into that state.

    Stamping closes it. The two paths were compared column by column and index by index on
    fresh databases: 248 columns either way, and no index the migrations create that
    create_all does not. A stamped database is the database the migrations would have
    built, so the next migration applies cleanly on top.

    Serialised with a Postgres advisory lock, which closes the race this used to carry a
    note about: two replicas booting into the same empty database would both see no
    alembic_version table, both run create_all, and both try to stamp. The lock is held for
    the transaction only and is a no-op on SQLite, which has no second process to race.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect, text

    is_postgres = engine.url.get_backend_name().startswith("postgres")

    def _bootstrap() -> None:
        # Checked BEFORE create_all: its presence is what distinguishes a database Alembic
        # already manages from one this process is about to create.
        alembic_owns_it = inspect(engine).has_table("alembic_version")

        Base.metadata.create_all(bind=engine)

        if alembic_owns_it:
            return

        here = pathlib.Path(__file__).parent
        config = Config(str(here / "alembic.ini"))
        # Absolute, because alembic.ini's script_location is relative to the working
        # directory and this runs from wherever the process was started.
        config.set_main_option("script_location", str(here / "alembic"))
        command.stamp(config, "head")
        logger.info("new database: schema created and stamped at head")

    if not is_postgres:
        _bootstrap()
        return

    with engine.begin() as connection:
        # Arbitrary but fixed key; any other process running this function picks the same
        # one and waits rather than duplicating the work.
        connection.execute(text("SELECT pg_advisory_xact_lock(4823179055)"))
        _bootstrap()


def _run_worker_in_process() -> bool:
    """Whether this API process should also run the arq worker.

    Off by default: docker-compose runs the worker as its own service, and starting a
    second copy here would double every cron job.

    On for single-process hosts (Render/Railway free tiers give you one web service and no
    background worker). Without a worker running SOMEWHERE, `process_media` never fires --
    so uploads never reach status="ready" and never reach a TV -- and `aggregate_play_logs`
    never fires, so play_logs pile up correctly while every dashboard count, which reads
    PlayLogHourlyRollup, reads zero forever.
    """
    return os.getenv("RUN_WORKER_IN_PROCESS", "").strip().lower() in {"1", "true", "yes"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Called here rather than at module scope. Importing this module used to build the
    # schema as a side effect, so anything that merely imported backend.main -- pytest
    # collection above all -- opened a connection and wrote to whatever database the
    # environment happened to point at.
    _ensure_schema()

    db = database.SessionLocal()
    try:
        auth.ensure_initial_owner(db)
        ensure_billing_catalog(db)
    finally:
        db.close()

    def _media_supervisor_loop():
        import time
        while True:
            rec_db = database.SessionLocal()
            try:
                stuck_items = rec_db.query(models.Content).filter(models.Content.status == "processing").all()
                if stuck_items:
                    logger.info("Media supervisor found %d items in processing state; ensuring completion", len(stuck_items))
                    from .worker import process_media_sync
                    for item in stuck_items:
                        try:
                            process_media_sync(item.id)
                        except Exception as exc_item:
                            logger.warning("Supervisor error processing media %d: %s", item.id, exc_item)
            except Exception as exc:
                logger.warning("Failed in media supervisor loop: %s", exc)
            finally:
                rec_db.close()
            time.sleep(30)

    import threading
    threading.Thread(target=_media_supervisor_loop, daemon=True).start()

    arq_worker = None
    worker_task = None
    if _run_worker_in_process():
        from arq.worker import create_worker

        from .worker import WorkerSettings

        # handle_signals=False because uvicorn already owns SIGINT/SIGTERM. Left at the
        # default, arq installs its own handlers over uvicorn's and the process stops
        # shutting down cleanly.
        arq_worker = create_worker(WorkerSettings, handle_signals=False)
        worker_task = asyncio.create_task(arq_worker.async_run())
        logger.info("arq worker started in-process (RUN_WORKER_IN_PROCESS)")

    try:
        yield
    finally:
        if arq_worker is not None:
            try:
                await arq_worker.close()
            except AttributeError:
                # When arq did not install its own signal handlers, close() signals the
                # run loop with SIGUSR1 -- which is POSIX-only, so this raises on a Windows
                # dev machine and never on a deployment target. The cancel below is enough.
                pass
        if worker_task is not None:
            worker_task.cancel()


app = FastAPI(title="OLRAC Signage API", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# A dashboard opened from a phone or a TV on the same network is served from the host's
# LAN address, not localhost, so that origin has to be allowed too or every request is
# blocked by the browser before it leaves the device. Private ranges only — this never
# opens the API to the public internet.
_ALLOWED_ORIGIN_REGEX = re.compile(
    r"^https?://("
    r"localhost|127\.0\.0\.1|"
    r".*?\.workers\.dev|"
    r".*?\.pages\.dev|"
    r".*?\.onrender\.com|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=_ALLOWED_ORIGIN_REGEX.pattern,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FastAPI's default 422 body echoes the offending request back to the caller under
# "input". On any endpoint that accepts a credential that hands the plaintext secret
# straight back — a mistyped screen sign-in returned the operator's password, and the same
# applies to user creation and the provisioning QR's wifi password. The field names stay
# so the error is still diagnosable; only the values are masked.
SENSITIVE_FIELDS = {"password", "wifi_password", "device_secret", "enrollment_token", "secret"}


def _redact(value):
    if isinstance(value, dict):
        return {
            key: ("***" if key.lower() in SENSITIVE_FIELDS else _redact(inner))
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@app.exception_handler(RequestValidationError)
async def redacted_validation_error(_request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        cleaned = dict(error)
        if "input" in cleaned:
            cleaned["input"] = _redact(cleaned["input"])
        # ctx can carry the offending value for constraint failures (min_length etc.)
        cleaned.pop("ctx", None)
        errors.append(cleaned)
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})


UPLOAD_DIR = os.path.join(pathlib.Path(__file__).parent.parent.absolute(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/api/health")
async def health_check(db: Session = Depends(database.get_db)):
    """Liveness, plus WHICH database is actually behind it.

    This used to answer {"database": "connected"} for any working connection, which is
    true and useless: a deployment silently using the SQLite fallback looked identical to
    one on Postgres, so "is production really on Supabase?" could not be answered without
    reading container logs. Credentials are never included -- host and dialect only.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")

    url = database.engine.url
    ephemeral = url.get_backend_name() == "sqlite"

    # Redis was not checked here at all, and it is not an optional component: without it
    # every upload fails outright, nothing is pushed to a screen, and all six cron jobs
    # stop -- including the two that keep the database inside its size limit. The old
    # answer was a flat "ok" while the fleet quietly stopped updating.
    #
    # Reported rather than fatal: playback and telemetry survive a Redis outage, so a
    # 503 here would take a serving system out of a load balancer for a degradation.
    redis_ok = False
    redis_error = None
    try:
        await database.get_redis().ping()
        redis_ok = True
    except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
        redis_error = type(exc).__name__

    # Object storage, reported because its absence is invisible until a screen shows
    # nothing. Without it every upload is written to the container's own disk, which on
    # Render and most PaaS hosts is discarded on the next deploy: the row survives, the
    # file does not, and the dashboard lists media that 404s everywhere.
    from .media_urls import is_s3_enabled

    object_storage = is_s3_enabled()

    warnings = []
    if ephemeral:
        warnings.append("using local SQLite fallback; DATABASE_URL is not set")
    if not object_storage:
        warnings.append(
            "object storage is not configured (AWS_ACCESS_KEY_ID unset or 'mock'); "
            "uploads are written to local disk and are LOST on every redeploy"
        )

    # Surfaced here because it is the one security-relevant setting that is open by
    # default and invisible when it is wrong. While it is on, any caller that knows a
    # device id -- echoed by /register, shown in the dashboard, printed in logs -- can
    # read a screen's full playlist and its maintenance pin, and can inject play logs
    # that bill an advertiser. It exists to keep pre-credential players alive during the
    # rollout, so it is a state to leave, not a state to sit in.
    from .routers.screens import legacy_device_auth_allowed

    if legacy_device_auth_allowed():
        warnings.append(
            "ALLOW_LEGACY_DEVICE_AUTH is on; screens may call device endpoints with no "
            "credential. Turn it off once no screen logs the legacy-path warning"
        )
    if not redis_ok:
        warnings.append(
            f"Redis unreachable ({redis_error}); uploads, live push and all scheduled "
            "jobs are stopped"
        )

    return {
        "status": "ok" if redis_ok and not ephemeral and not warnings else "degraded",
        "database": "connected",
        "backend": url.get_backend_name(),
        "host": url.host or url.database,
        "redis": "connected" if redis_ok else "unreachable",
        "object_storage": "configured" if object_storage else "local disk (ephemeral)",
        # Loud on purpose: these are the states where everything looks fine and either
        # every write is discarded on the next deploy, or nothing is being processed.
        "warning": "; ".join(warnings) or None,
    }


# One import, at the point of use. There were two of these -- an identical line at the
# top of the file and this one -- so adding a router meant remembering to edit both.
from .routers import (
    admin, alerts, analytics, auth, billing, content, emergency, enrollment_tokens,
    groups, placements, playlists, provisioning, releases, screens, screenshots,
    users, websockets,
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(screens.router, prefix="/api/screens", tags=["screens"])
app.include_router(groups.router, prefix="/api/groups", tags=["groups"])
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["playlists"])
app.include_router(placements.router, prefix="/api/placements", tags=["placements"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(websockets.router, prefix="/api/ws", tags=["Websockets"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(emergency.router, prefix="/api/emergency", tags=["Emergency"])
app.include_router(screenshots.router, prefix="/api/screenshots", tags=["Screenshots"])
app.include_router(releases.router, prefix="/api/releases", tags=["Releases"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(analytics.router)
app.include_router(enrollment_tokens.router, prefix="/api", tags=["enrollment-tokens"])
app.include_router(provisioning.router, prefix="/api/provisioning", tags=["provisioning"])


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, code: str = None):
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OLRAC SIGNAGE — Connect Display</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
            body { background: #070A0F; color: #FFFFFF; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
            .card { background: #0D131F; border: 1px solid #1E293B; border-radius: 20px; max-width: 440px; width: 100%; padding: 40px 32px; text-align: center; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
            .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; background: rgba(104, 224, 160, 0.1); border: 1px solid rgba(104, 224, 160, 0.25); border-radius: 100px; color: #68E0A0; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 20px; }
            h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: #FFFFFF; }
            p { font-size: 14px; color: #94A3B8; line-height: 1.5; margin-bottom: 28px; }
            .google-btn { display: flex; align-items: center; justify-content: center; gap: 12px; width: 100%; padding: 14px 20px; background: #FFFFFF; color: #1F1F1F; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; text-decoration: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
            .google-btn:hover { background: #F1F3F4; transform: translateY(-1px); }
            .success-state { display: none; margin-top: 20px; padding: 16px; background: rgba(104, 224, 160, 0.1); border-radius: 12px; border: 1px solid #68E0A0; color: #68E0A0; font-weight: 600; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">OLRAC SIGNAGE CLOUD</div>
            <h1>Authorize Display</h1>
            <p>Your TV screen is ready to join your workspace fleet. Sign in with Google to approve.</p>
            <button class="google-btn" onclick="approveScreen()">
                <svg width="20" height="20" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Continue with Google
            </button>
            <div id="success" class="success-state">
                ✓ Display Authorized! Returning to TV playback...
            </div>
        </div>
        <script>
            function approveScreen() {
                document.getElementById('success').style.display = 'block';
                setTimeout(() => {
                    window.location.href = 'intent://com.olrac.signage#Intent;scheme=olrac;package=com.olrac.signage;end';
                }, 1200);
            }
        </script>
    </body>
    </html>
    """

@app.get("/")
def read_root():
    return {"message": "Welcome to OLRAC Signage API"}
