import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

from app.config import settings
from app.responses import register_exception_handlers, ok
from app.tasks import offline_sweeper

# ── Routers ─────────────────────────────────────────────────────────────

from app.routers.auth import router as auth_router
from app.routers.content import router as content_router
from app.routers.screens import router as screens_router
from app.routers.playlists import router as playlists_router
from app.routers.groups import router as groups_router
from app.routers.playback import router as playback_router
from app.routers.reports import router as reports_router
from app.routers.websites import router as websites_router

app = FastAPI(
    title="Olrac Signage API",
    docs_url=None,
    redoc_url=None,
)

# CORS — allow both frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers — never leak a raw traceback
register_exception_handlers(app)

# ── Include routers ─────────────────────────────────────────────────────

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(content_router, prefix="/content", tags=["content"])
app.include_router(screens_router, prefix="/screens", tags=["screens"])
app.include_router(playlists_router, prefix="", tags=["playlists"])
app.include_router(groups_router, prefix="/groups", tags=["groups"])
app.include_router(playback_router, prefix="", tags=["playback"])
app.include_router(reports_router, prefix="/reports", tags=["reports"])
app.include_router(websites_router, prefix="/websites", tags=["websites"])


# ── Health ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return ok({"status": "ok"})


@app.get("/docs", include_in_schema=False)
async def custom_swagger():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Olrac Signage API")


# ── Startup: offline screen sweeper ─────────────────────────────────────


@app.on_event("startup")
async def startup():
    asyncio.create_task(offline_sweeper())
