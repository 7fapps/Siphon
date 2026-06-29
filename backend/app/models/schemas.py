from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional
from datetime import datetime

# ── Probe ──────────────────────────────────────────────────────

class ProbeRequest(BaseModel):
    url: str

class AudioProbeRequest(BaseModel):
    url: str

class FormatInfo(BaseModel):
    format_id: str
    height: int
    width: int
    ext: str
    vcodec: str
    acodec: str
    abr: Optional[float] = None
    vbr: Optional[float] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    video_ext: Optional[str] = None
    audio_ext: Optional[str] = None
    quality: Optional[str] = None
    
class ProbeResponse(BaseModel):
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    formats: List[FormatInfo]
    heights: List[int]
    message: str = "success"

# ── Download ───────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    url: str
    height: int = 0
    filename: Optional[str] = "siphon_video.mp4"

class AudioDownloadRequest(BaseModel):
    url: str
    format: Optional[str] = "mp3"
    quality: Optional[str] = "192"
    filename: Optional[str] = "siphon_audio.mp3"

class BatchDownloadRequest(BaseModel):
    urls: List[str]
    height: Optional[int] = 0
    filename: Optional[str] = "siphon_video.mp4"

class DownloadResponse(BaseModel):
    job_id: str
    status: str = "queued"
    message: str = "Download job queued"

class BatchDownloadResponse(BaseModel):
    batch_id: str
    job_ids: List[str]
    total: int
    status: str = "queued"
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    file_path: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ── History ────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    id: int
    url: str
    title: Optional[str] = None
    height: Optional[int] = None
    audio_only: bool = False
    file_size: Optional[int] = None
    thumbnail: Optional[str] = None
    duration: Optional[float] = None
    downloaded_at: Optional[datetime] = None

class HistoryResponse(BaseModel):
    entries: List[HistoryEntry]

# ── Admin ──────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    services: dict
    config: dict

class StatsResponse(BaseModel):
    jobs: dict
    downloads: dict
    orphaned_files: int
    timestamp: str

