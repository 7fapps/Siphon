import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CleanupService:
    """Utilities for managing the ephemeral temp/download lifecycle."""
    
    @staticmethod
    def delete_file(path: Path) -> bool:
        """Safely delete a file, logging the outcome."""
        try:
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"[cleanup] Deleted: {path}")
                return True
        except Exception as e:
            logger.error(f"[cleanup] Failed to delete {path}: {e}")
        return False
    
    @staticmethod
    def schedule_delete_after_stream(path: Path):
        """
        Return a generator callback that deletes the file after streaming completes.
        Used with FastAPI's StreamingResponse background callback.
        """
        def _cleanup():
            CleanupService.delete_file(path)
        return _cleanup
    
    @staticmethod
    def find_orphaned_files(cutoff_minutes: Optional[int] = None) -> List[Path]:
        """Find files older than the cutoff age."""
        cutoff = cutoff_minutes or settings.max_file_age_minutes
        cutoff_time = datetime.now() - timedelta(minutes=cutoff)
        orphans = []
        
        for f in settings.temp_download_dir.iterdir():
            if f.is_file() and f.name != ".gitkeep":
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff_time:
                        orphans.append(f)
                except Exception as e:
                    logger.warning(f"[cleanup] Error checking {f}: {e}")
        
        return orphans
    
    @staticmethod
    def cleanup_orphans(cutoff_minutes: Optional[int] = None) -> int:
        """Delete all orphaned files and return count."""
        orphans = CleanupService.find_orphaned_files(cutoff_minutes)
        deleted = 0
        for f in orphans:
            if CleanupService.delete_file(f):
                deleted += 1
        return deleted
