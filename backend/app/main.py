from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

from app.config import get_settings
from app.database import init_db
from app.middleware import StructuredLoggingMiddleware, SecurityHeadersMiddleware
from app.routers import probe, download, admin, history, websocket
from app.celery_app import celery_app

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(settings.temp_download_dir, exist_ok=True)
logger.info(f"Temp download directory: {settings.temp_download_dir}")

# Initialize database
init_db()
logger.info("Database initialized")

app = FastAPI(
    title=settings.app_name,
    description="Stealth video extraction and download service — PWA-enabled, installable on Android, iOS, Windows, and macOS.",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ── Middleware (order matters) ─────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://siphon-app.onrender.com",
        "https://siphon-app.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "event_id": str(id(exc))},
    )


# ── Routers ────────────────────────────────────────────────────
app.include_router(probe.router, prefix="/api")
app.include_router(download.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.app_name, "version": "2.0.0"}


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": "2.0.0",
        "features": {
            "batch_download": settings.enable_batch,
            "audio_only": settings.enable_audio_only,
            "websocket": settings.enable_websocket,
            "proxy_rotation": settings.enable_proxy_rotation,
            "analytics": settings.enable_analytics,
        },
        "endpoints": {
            "probe": "/api/probe",
            "download": "/api/download",
            "audio": "/api/download/audio",
            "batch": "/api/download/batch",
            "status": "/api/download/{job_id}/status",
            "stream": "/api/download/{job_id}/file",
            "websocket": "/api/ws/job/{job_id}",
            "health": "/health",
            "admin": "/api/admin/health",
        }
    }
