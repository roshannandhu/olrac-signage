import os
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
from .routers import analytics, auth, billing, content, enrollment_tokens, groups, playlists, screens, users, websockets, emergency, screenshots, releases, provisioning

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = database.SessionLocal()
    try:
        auth.ensure_initial_owner(db)
        ensure_billing_catalog(db)
    finally:
        db.close()
    yield


app = FastAPI(title="OLRAC Signage API", version="2.0.0", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(websockets.router, prefix="/api/ws", tags=["Websockets"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(emergency.router, prefix="/api/emergency", tags=["Emergency"])
app.include_router(screenshots.router, prefix="/api/screenshots", tags=["Screenshots"])
app.include_router(releases.router, prefix="/api/releases", tags=["Releases"])
app.include_router(analytics.router)
app.include_router(enrollment_tokens.router, prefix="/api", tags=["enrollment-tokens"])
app.include_router(provisioning.router, prefix="/api/provisioning", tags=["provisioning"])


@app.get("/")
def read_root():
    return {"message": "Welcome to OLRAC Signage API"}
