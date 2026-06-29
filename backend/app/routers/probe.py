from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.models.schemas import ProbeRequest, ProbeResponse, AudioProbeRequest
from app.services.extractor import get_extractor
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/probe", tags=["probe"])
settings = get_settings()

# ADDED FALLBACK: This handles GET requests gracefully if the frontend uses GET with a query string (?url=...)
@router.get("", response_model=ProbeResponse, status_code=status.HTTP_200_OK)
async def probe_url_get(url: str, req: Request) -> ProbeResponse:
    if not url or not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    extractor = get_extractor()
    try:
        result = await extractor.probe(url)
    except Exception as e:
        logger.exception(f"Probe failed for {url}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")

    if not result.formats:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No video formats found")

    return result

@router.post("", response_model=ProbeResponse, status_code=status.HTTP_200_OK)
async def probe_url(request: ProbeRequest, req: Request) -> ProbeResponse:
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    extractor = get_extractor()
    try:
        result = await extractor.probe(request.url)
    except Exception as e:
        logger.exception(f"Probe failed for {request.url}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")

    if not result.formats:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No video formats found")

    return result

@router.post("/audio", response_model=ProbeResponse, status_code=status.HTTP_200_OK)
async def probe_audio(request: AudioProbeRequest, req: Request) -> ProbeResponse:
    if not settings.enable_audio_only:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audio-only extraction is disabled")
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    extractor = get_extractor()
    try:
        result = await extractor.probe_audio(request.url)
    except Exception as e:
        logger.exception(f"Audio probe failed for {request.url}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")

    if not result.formats:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No audio formats found")

    return result
