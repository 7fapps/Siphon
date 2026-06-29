import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

import yt_dlp
from celery import shared_task, current_task
from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings
from app.services.proxy_pool import get_proxy_pool
from app.database import db_session, JobRepository

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_rotated_user_agent() -> str:
    """Return a rotated user agent from config or default."""
    if settings.ytdlp_user_agents:
        agents = [a.strip() for a in settings.ytdlp_user_agents.split(",") if a.strip()]
        import random
        return random.choice(agents)
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )


def _update_progress(state: str, progress: float, message: str):
    if current_task and current_task.request.id:
        current_task.update_state(
            state=state,
            meta={"progress": progress, "message": message},
        )


def _update_db(job_id: str, **kwargs):
    try:
        with db_session() as db:
            JobRepository.update(db, job_id, **kwargs)
    except Exception as e:
        logger.warning(f"[db] Failed to update job {job_id}: {e}")


def _ytdlp_progress_hook(d: Dict[str, Any]):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
        pct = d.get("downloaded_bytes", 0) / max(total, 1) * 100
        _update_progress("PROGRESS", min(pct, 95.0), f"Downloading... {pct:.1f}%")
    elif d["status"] == "finished":
        _update_progress("PROGRESS", 95.0, "Assembling chunks...")


def _find_output_file(base_path: Path, output_dir: Path, job_id: str) -> Optional[Path]:
    for ext in [".mp4", ".webm", ".mkv", ".mov", ".avi", ".mp3", ".m4a", ".ogg", ".wav"]:
        candidate = base_path.with_suffix(ext)
        if candidate.exists():
            return candidate
    for f in output_dir.iterdir():
        if f.is_file() and job_id in f.name:
            return f
    return None


def _convert_to_mp4(source: Path, target: Path) -> Path:
    cmd = [
        "ffmpeg", "-y", "-i", str(source),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        str(target),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"FFmpeg conversion failed: {e}")
        if not target.exists():
            shutil.copy2(str(source), str(target))
    return target


def _convert_to_mp3(source: Path, target: Path) -> Path:
    cmd = [
        "ffmpeg", "-y", "-i", str(source),
        "-vn", "-c:a", "libmp3lame", "-q:a", "2",
        "-ar", "44100", "-ac", "2",
        str(target),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"FFmpeg MP3 conversion failed: {e}")
        if not target.exists():
            shutil.copy2(str(source), str(target))
    return target


def _cleanup_partial_files(base_path: Path, output_dir: Path, job_id: str):
    for f in output_dir.iterdir():
        if f.is_file() and job_id in f.name:
            try:
                f.unlink()
                logger.info(f"Cleaned up partial file: {f}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {f}: {e}")


# ── Video Download ─────────────────────────────────────────────

@shared_task(
    bind=True,
    name="app.tasks.download.download_video",
    max_retries=1,
    default_retry_delay=30,
    queue="siphon",
)
def download_video(self, url: str, height: int, filename: str, client_ip: str = None) -> Dict[str, Any]:
    job_id = self.request.id
    output_dir = settings.temp_download_dir
    os.makedirs(output_dir, exist_ok=True)
    base_path = Path(output_dir) / f"{job_id}"
    output_template = str(base_path) + ".%(ext)s"
    final_path = base_path.with_suffix(".mp4")

    _update_db(job_id, status="started", started_at=datetime.now(), retries=self.request.retries)
    _update_progress("STARTED", 5.0, "Initializing download...")

    proxy_pool = get_proxy_pool()
    proxy_url = proxy_pool.get_random() if proxy_pool.has_proxies else None
    user_agent = _get_rotated_user_agent()

    ydl_opts = {
        "format": f"bv[height={height}][vcodec!*=av01]+ba/b[height={height}]/b" if height > 0 else "bv*[vcodec!*=av01]+ba/b",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}],
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_ytdlp_progress_hook],
        "proxy": proxy_url,
        "user_agent": user_agent,
        "retries": 3,
        "fragment_retries": 3,
        "skip_unavailable_fragments": True,
        "max_filesize": settings.ytdlp_max_filesize_mb * 1024 * 1024,
    }

    info = None
    try:
        _update_progress("STARTED", 10.0, "Extracting stream info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        actual_file = _find_output_file(base_path, output_dir, job_id)
        if not actual_file or not actual_file.exists():
            raise FileNotFoundError(f"Downloaded file not found for job {job_id}")

        if actual_file.suffix.lower() != ".mp4":
            _update_progress("PROGRESS", 85.0, "Converting to MP4...")
            final_path = _convert_to_mp4(actual_file, final_path)
            if actual_file != final_path and actual_file.exists():
                os.unlink(actual_file)
        else:
            if actual_file != final_path:
                shutil.move(str(actual_file), str(final_path))

        _update_progress("SUCCESS", 100.0, "Download complete")
        _update_db(job_id, status="completed", completed_at=datetime.now(),
                   file_path=str(final_path), progress=100.0)

        return {
            "job_id": job_id,
            "status": "completed",
            "file_path": str(final_path),
            "file_size": final_path.stat().st_size if final_path.exists() else 0,
            "title": info.get("title") if info else None,
            "thumbnail": info.get("thumbnail") if info else None,
            "duration": info.get("duration") if info else None,
            "message": "Download complete",
            "is_audio": False,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"[task] Soft time limit exceeded for job {job_id}")
        _cleanup_partial_files(base_path, output_dir, job_id)
        _update_db(job_id, status="failed", error="Soft time limit exceeded")
        raise self.retry(exc=Exception("Soft time limit exceeded"), countdown=60)

    except Exception as e:
        logger.exception(f"[task] Download failed for job {job_id}")
        _cleanup_partial_files(base_path, output_dir, job_id)
        _update_db(job_id, status="failed", error=str(e)[:500])
        raise self.retry(exc=e, countdown=30)


# ── Audio-Only Download ────────────────────────────────────────

@shared_task(
    bind=True,
    name="app.tasks.download.download_audio",
    max_retries=1,
    default_retry_delay=30,
    queue="siphon",
)
def download_audio(self, url: str, format: str, quality: str, filename: str, client_ip: str = None) -> Dict[str, Any]:
    job_id = self.request.id
    output_dir = settings.temp_download_dir
    os.makedirs(output_dir, exist_ok=True)
    base_path = Path(output_dir) / f"{job_id}"
    output_template = str(base_path) + ".%(ext)s"
    final_path = base_path.with_suffix(f".{format}")

    _update_db(job_id, status="started", started_at=datetime.now(), retries=self.request.retries, audio_only=True)
    _update_progress("STARTED", 5.0, "Initializing audio download...")

    proxy_pool = get_proxy_pool()
    proxy_url = proxy_pool.get_random() if proxy_pool.has_proxies else None
    user_agent = _get_rotated_user_agent()

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": format,
                "preferredquality": quality,
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_ytdlp_progress_hook],
        "proxy": proxy_url,
        "user_agent": user_agent,
        "retries": 3,
        "fragment_retries": 3,
        "skip_unavailable_fragments": True,
        "max_filesize": settings.ytdlp_max_filesize_mb * 1024 * 1024,
    }

    info = None
    try:
        _update_progress("STARTED", 10.0, "Extracting audio info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        actual_file = _find_output_file(base_path, output_dir, job_id)
        if not actual_file or not actual_file.exists():
            raise FileNotFoundError(f"Downloaded audio file not found for job {job_id}")

        if actual_file.suffix.lower() != f".{format}":
            if format == "mp3":
                final_path = _convert_to_mp3(actual_file, final_path)
            if actual_file != final_path and actual_file.exists():
                os.unlink(actual_file)
        else:
            if actual_file != final_path:
                shutil.move(str(actual_file), str(final_path))

        _update_progress("SUCCESS", 100.0, "Audio download complete")
        _update_db(job_id, status="completed", completed_at=datetime.now(),
                   file_path=str(final_path), progress=100.0)

        return {
            "job_id": job_id,
            "status": "completed",
            "file_path": str(final_path),
            "file_size": final_path.stat().st_size if final_path.exists() else 0,
            "title": info.get("title") if info else None,
            "thumbnail": info.get("thumbnail") if info else None,
            "duration": info.get("duration") if info else None,
            "message": "Audio download complete",
            "is_audio": True,
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"[task] Soft time limit exceeded for audio job {job_id}")
        _cleanup_partial_files(base_path, output_dir, job_id)
        _update_db(job_id, status="failed", error="Soft time limit exceeded")
        raise self.retry(exc=Exception("Soft time limit exceeded"), countdown=60)

    except Exception as e:
        logger.exception(f"[task] Audio download failed for job {job_id}")
        _cleanup_partial_files(base_path, output_dir, job_id)
        _update_db(job_id, status="failed", error=str(e)[:500])
        raise self.retry(exc=e, countdown=30)


# ── Cleanup ────────────────────────────────────────────────────

@shared_task(name="app.tasks.download.cleanup_orphaned_files")
def cleanup_orphaned_files():
    import time
    cutoff = time.time() - (settings.max_file_age_minutes * 60)
    deleted = 0

    for f in settings.temp_download_dir.iterdir():
        if f.is_file() and f.name != ".gitkeep":
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    deleted += 1
                    logger.info(f"[cleanup] Deleted orphaned file: {f}")
            except Exception as e:
                logger.warning(f"[cleanup] Failed to delete {f}: {e}")

    logger.info(f"[cleanup] Orphan cleanup complete. Deleted {deleted} files.")
    return {"deleted": deleted}


from datetime import datetime
