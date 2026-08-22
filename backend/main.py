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
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import database, models
from .billing import ensure_billing_catalog
from .database import Base, engine
from .routers import alerts, analytics, auth, billing, content, enrollment_tokens, groups, placements, playlists, screens, users, websockets, emergency, screenshots, releases, provisioning

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

    ponytail: no cross-process lock. Two instances booting into the same empty database at
    the same instant could race; take a Postgres advisory lock here if this ever runs more
    than one replica.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    # Checked BEFORE create_all: its presence is what distinguishes a database Alembic
    # already manages from one this process is about to create.
    alembic_owns_it = inspect(engine).has_table("alembic_version")

    Base.metadata.create_all(bind=engine)

    if alembic_owns_it:
        return

    here = pathlib.Path(__file__).parent
    config = Config(str(here / "alembic.ini"))
    # Absolute, because alembic.ini's script_location is relative to the working directory
    # and this runs from wherever the process was started.
    config.set_main_option("script_location", str(here / "alembic"))
    command.stamp(config, "head")
    logger.info("new database: schema created and stamped at head")


_ensure_schema()


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
    db = database.SessionLocal()
    try:
        auth.ensure_initial_owner(db)
        ensure_billing_catalog(db)
    finally:
        db.close()

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

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# A dashboard opened from a phone or a TV on the same network is served from the host's
# LAN address, not localhost, so that origin has to be allowed too or every request is
# blocked by the browser before it leaves the device. Private ranges only — this never
# opens the API to the public internet.
_LAN_ORIGIN = re.compile(
    r"^https?://("
    r"localhost|127\.0\.0\.1|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=_LAN_ORIGIN.pattern,
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
def health_check(db: Session = Depends(database.get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
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


@app.get("/")
def read_root():
    return {"message": "Welcome to OLRAC Signage API"}
