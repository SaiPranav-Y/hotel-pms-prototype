"""
90-Day Data Retention Policy — auto-cleanup old recordings and logs.
Configurable retention window. Runs cleanup on server start and periodically.
"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
_config = {
    "retention_days": 90,
    "cleanup_recordings": True,
    "cleanup_call_logs": True,
    "archive_before_delete": False,  # If True, move to archive folder instead of deleting
    "last_cleanup": None,
}

RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
ARCHIVE_DIR = Path(__file__).parent.parent / "archive"


def get_retention_config() -> dict:
    return {**_config}


def set_retention_days(days: int) -> bool:
    """Set retention window (1-365 days)."""
    if 1 <= days <= 365:
        _config["retention_days"] = days
        return True
    return False


def run_cleanup() -> dict:
    """
    Run retention cleanup.
    Deletes/archives recordings and logs older than retention window.
    Returns cleanup stats.
    """
    cutoff = datetime.now() - timedelta(days=_config["retention_days"])
    stats = {"recordings_deleted": 0, "recordings_archived": 0, "logs_cleaned": 0}

    # Clean recordings
    if _config["cleanup_recordings"] and RECORDINGS_DIR.exists():
        for f in RECORDINGS_DIR.iterdir():
            if not f.is_file():
                continue
            # Check file modification time
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                if _config["archive_before_delete"]:
                    _archive_file(f)
                    stats["recordings_archived"] += 1
                else:
                    f.unlink()
                    stats["recordings_deleted"] += 1

    _config["last_cleanup"] = datetime.now().isoformat()
    logger.info(f"Retention cleanup: {stats}")
    return stats


def check_retention_status() -> dict:
    """Check what would be cleaned up without actually doing it."""
    cutoff = datetime.now() - timedelta(days=_config["retention_days"])
    old_recordings = 0
    total_size_bytes = 0

    if RECORDINGS_DIR.exists():
        for f in RECORDINGS_DIR.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    old_recordings += 1
                    total_size_bytes += f.stat().st_size

    return {
        "retention_days": _config["retention_days"],
        "cutoff_date": cutoff.isoformat()[:10],
        "recordings_to_clean": old_recordings,
        "space_to_reclaim_mb": round(total_size_bytes / 1024 / 1024, 2),
        "last_cleanup": _config["last_cleanup"],
    }


def _archive_file(filepath: Path):
    """Move file to archive directory."""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    dest = ARCHIVE_DIR / filepath.name
    filepath.rename(dest)


def get_storage_stats() -> dict:
    """Get current storage usage."""
    rec_size = 0
    rec_count = 0
    if RECORDINGS_DIR.exists():
        for f in RECORDINGS_DIR.iterdir():
            if f.is_file():
                rec_count += 1
                rec_size += f.stat().st_size

    return {
        "recordings_count": rec_count,
        "recordings_size_mb": round(rec_size / 1024 / 1024, 2),
        "retention_days": _config["retention_days"],
    }
