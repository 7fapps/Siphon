from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path
from typing import List
import os

class Settings(BaseSettings):
    # App
    app_name: str = "Siphon"
    debug: bool = False
    
    # Paths
    temp_download_dir: Path = Path(__file__).resolve().parent.parent.parent / "temp" / "downloads"
    
    # Database
    database_url: str = "sqlite:///./siphon.db"
    
    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_concurrency: int = 2
    
    # Rate Limiting
    rate_limit_probe: str = "10/minute"
    rate_limit_download: str = "5/minute"
    rate_limit_status: str = "60/minute"
    
    # Proxy
    proxy_url: str | None = None
    proxy_urls: str | None = None  # Comma-separated for rotation
    proxy_rotation_strategy: str = "round_robin"  # round_robin | random
    
    # Playwright stealth
    playwright_headless: bool = True
    playwright_timeout: int = 30000
    
    # yt-dlp
    ytdlp_timeout: int = 120
    ytdlp_max_filesize_mb: int = 2048
    ytdlp_user_agents: str | None = None  # Comma-separated list
    
    # Cleanup
    max_file_age_minutes: int = 30
    cleanup_interval_minutes: int = 10
    
    # Logging
    log_format: str = "json"  # json | text
    log_level: str = "INFO"
    
    # Security
    api_key: str | None = None  # Optional API key for access control
    admin_token: str | None = None  # For admin endpoints
    
    # Features
    enable_batch: bool = True
    enable_audio_only: bool = True
    enable_websocket: bool = True
    enable_push_notifications: bool = False
    enable_analytics: bool = True
    enable_proxy_rotation: bool = False
    
    # WebSocket
    websocket_heartbeat_interval: int = 30
    
    # Haptic / UX
    enable_haptic_feedback: bool = True  # Used by frontend only
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
