from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime

from app.models.schemas import HistoryEntry

router = APIRouter(prefix="/history", tags=["history"])

@router.get("")
async def get_history(limit: int = 50):
    """Get recent download history for the client."""
    return {
        "entries": []
    }