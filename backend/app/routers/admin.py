from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app
from app.config import get_settings
from app.services.proxy_pool import get_proxy_pool
from app.services.cleanup import CleanupService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

def verify_admin_token(token: str | None = None):
    if not settings.admin_token:
        return True
    if token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True

@router.get("/health")
async def health_dashboard():
    """Comprehensive health check of all services."""
    from redis import Redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    import subprocess

    # Redis check
    redis_ok = False
    redis_info = {}
    try:
        r = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        redis_info = r.info()
        redis_ok = True
    except RedisConnectionError as e:
        redis_info = {"error": str(e)}

    # Celery worker check
    celery_inspect = celery_app.control.inspect()
    active_workers = celery_inspect.active() if celery_inspect else None
    worker_count = len(active_workers) if active_workers else 0

    # FFmpeg check
    ffmpeg_ok = False
    ffmpeg_version = ""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        ffmpeg_ok = result.returncode == 0
        ffmpeg_version = result.stdout.splitlines()[0] if result.stdout else ""
    except Exception as e:
        ffmpeg_version = str(e)

    # Playwright check
    playwright_ok = False
    try:
        import playwright
        playwright_ok = True
    except ImportError:
        pass

    # yt-dlp check
    ytdlp_ok = False
    ytdlp_version = ""
    try:
        import yt_dlp
        ytdlp_version = yt_dlp.version.__version__
        ytdlp_ok = True
    except Exception as e:
        ytdlp_version = str(e)

    # Proxy pool
    proxy_pool = get_proxy_pool()

    return {
        "status": "healthy" if redis_ok and worker_count > 0 and ffmpeg_ok else "degraded",
        "services": {
            "redis": {"ok": redis_ok, "info": redis_info},
            "celery": {"ok": worker_count > 0, "active_workers": worker_count},
            "ffmpeg": {"ok": ffmpeg_ok, "version": ffmpeg_version},
            "playwright": {"ok": playwright_ok},
            "yt_dlp": {"ok": ytdlp_ok, "version": ytdlp_version},
            "proxy_pool": {"ok": proxy_pool.has_proxies, "count": proxy_pool.count},
        },
        "config": {
            "concurrency": settings.celery_concurrency,
            "batch_enabled": settings.enable_batch,
            "audio_enabled": settings.enable_audio_only,
            "websocket_enabled": settings.enable_websocket,
            "proxy_rotation": settings.enable_proxy_rotation,
        }
    }

@router.get("/stats")
async def get_stats(token: str = None):
    verify_admin_token(token)

    return {
        "jobs": {
            "total_completed": 0,
            "failed": 0,
            "queued": 0,
            "active": 0,
        },
        "downloads": [],
        "orphaned_files": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.get("/jobs")
async def list_jobs(limit: int = 50, token: str = None):
    verify_admin_token(token)
    return {
        "jobs": []
    }

@router.post("/cleanup")
async def force_cleanup(token: str = None):
    verify_admin_token(token)
    deleted = CleanupService.cleanup_orphans()
    return {"deleted": deleted, "message": "Cleanup completed"}