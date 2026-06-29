from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
import logging
import json

from app.models.schemas import ProbeRequest, ProbeResponse, AudioProbeRequest
from app.services.extractor import get_extractor
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/probe", tags=["probe"])
settings = get_settings()

@router.post("", status_code=status.HTTP_200_OK)
async def probe_url(request: ProbeRequest, req: Request):
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    extractor = get_extractor()
    try:
        result = await extractor.probe(request.url)
        
        # If result is empty or None, don't let it return a blank 200
        if not result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Extractor returned empty results")
            
        # Safely convert Pydantic model or object to dictionary
        if hasattr(result, "dict"):
            return result.dict()
        elif hasattr(result, "model_dump"):
            return result.model_dump()
        return result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Probe failed for {request.url}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")

@router.post("/audio", status_code=status.HTTP_200_OK)
async def probe_audio(request: AudioProbeRequest, req: Request):
    if not settings.enable_audio_only:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Audio-only extraction is disabled")
    if not request.url or not request.url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL")

    extractor = get_extractor()
    try:
        result = await extractor.probe_audio(request.url)
        
        if not result:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Extractor returned empty audio results")
            
        if hasattr(result, "dict"):
            return result.dict()
        elif hasattr(result, "model_dump"):
            return result.model_dump()
        return result
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Audio probe failed for {request.url}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Extraction failed: {str(e)}")
