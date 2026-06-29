from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import StreamingResponse
from celery.result import AsyncResult
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.models.schemas import (
    DownloadRequest, DownloadResponse, JobStatusResponse,
    BatchDownloadRequest, BatchDownloadResponse, AudioDownloadRequest,
)
from app.celery_app import celery_app, JOB_STATES
from app.tasks.download import download_video, download_audio
from app.services.cleanup import CleanupService
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/download", tags=["download"])
settings = get_settings()

@router.post("", response_model=DownloadResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_download(request: DownloadRequest, req: Request) -> DownloadResponse:
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")
    if request.height and request.height <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Height must be positive")

    client_ip = req.client.host if req.client else None

    task = download_video.delay(
        url=request.url,
        height=request.height or 0,
        filename=request.filename or "siphon_video.mp4",
        client_ip=client_ip,
    )

    logger.info(f"[download] Queued job {task.id} for {request.url} at {request.height}p")
    return DownloadResponse(job_id=task.id, status="queued", message="Download job queued")

@router.post("/audio", response_model=DownloadResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_audio_download(request: AudioDownloadRequest, req: Request) -> DownloadResponse:
    if not settings.enable_audio_only:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audio-only downloads are disabled")
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    client_ip = req.client.host if req.client else None

    task = download_audio.delay(
        url=request.url,
        format=request.format or "mp3",
        quality=request.quality or "192",
        filename=request.filename or "siphon_audio.mp3",
        client_ip=client_ip,
    )

    logger.info(f"[download] Queued audio job {task.id} for {request.url}")
    return DownloadResponse(job_id=task.id, status="queued", message="Audio download job queued")

@router.post("/batch", response_model=BatchDownloadResponse, status_code=status.HTTP_202_ACCEPTED)
async def queue_batch_download(request: BatchDownloadRequest, req: Request) -> BatchDownloadResponse:
    if not settings.enable_batch:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Batch downloads are disabled")
    if not request.urls:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided")
    if len(request.urls) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 10 URLs per batch")

    job_ids = []
    client_ip = req.client.host if req.client else None

    for url in request.urls:
        if not url.startswith(("http://", "https://")):
            continue
        task = download_video.delay(
            url=url,
            height=request.height or 0,
            filename=request.filename or "siphon_video.mp4",
            client_ip=client_ip,
        )
        job_ids.append(task.id)

    return BatchDownloadResponse(
        batch_id=job_ids[0] if job_ids else "",
        job_ids=job_ids,
        total=len(job_ids),
        status="queued",
        message=f"Batch queued with {len(job_ids)} jobs",
    )

@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    result = AsyncResult(job_id, app=celery_app)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    state = JOB_STATES.get(result.state, "unknown")
    meta = result.info or {}

    file_path = None
    if result.state == "SUCCESS" and isinstance(result.result, dict):
        file_path = result.result.get("file_path")
    elif isinstance(meta, dict):
        file_path = meta.get("file_path")

    return JobStatusResponse(
        job_id=job_id,
        status=state,
        progress=meta.get("progress") if isinstance(meta, dict) else None,
        message=meta.get("message") if isinstance(meta, dict) else None,
        file_path=file_path,
        error=str(meta) if result.state == "FAILURE" and not isinstance(meta, dict) else None,
        created_at=None,
        updated_at=None,
    )

@router.get("/{job_id}/file")
async def stream_file(job_id: str, req: Request):
    result = AsyncResult(job_id, app=celery_app)
    if not result or result.state != "SUCCESS":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not ready")

    task_result = result.result
    if not isinstance(task_result, dict) or not task_result.get("file_path"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File path missing")

    file_path = Path(task_result["file_path"])
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File no longer exists")

    file_size = file_path.stat().st_size
    filename = task_result.get("filename", "siphon_video.mp4")
    is_audio = task_result.get("is_audio", False)
    media_type = "audio/mpeg" if is_audio else "video/mp4"
    ext = ".mp3" if is_audio else ".mp4"
    if not filename.endswith(ext):
        filename = filename.rsplit(".", 1)[0] + ext

    def file_generator(path: Path):
        try:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    yield chunk
        finally:
            CleanupService.delete_file(path)
            logger.info(f"[stream] File {path} unlinked after transfer for job {job_id}")

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "none",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }

    return StreamingResponse(
        file_generator(file_path),
        media_type=media_type,
        headers=headers,
        status_code=200,
    )