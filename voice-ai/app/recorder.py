"""
Audio Recording System — stores call recordings and serves them for playback.
Recordings are saved as WebM files (browser-native format) in the /recordings directory.
"""

import os
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

RECORDINGS_DIR = Path(__file__).parent.parent / "recordings"
RECORDINGS_DIR.mkdir(exist_ok=True)

# In-memory index of recordings (maps call_id to file info)
recordings_index: dict[str, dict] = {}


def save_recording(call_id: str, audio_data: bytes, mime_type: str = "audio/webm") -> dict:
    """
    Save a call recording to disk.
    
    Args:
        call_id: Unique call identifier
        audio_data: Raw audio bytes from the browser
        mime_type: MIME type of the audio (default: audio/webm)
    
    Returns:
        Recording metadata dict
    """
    # Determine file extension from mime type
    ext_map = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
    }
    ext = ext_map.get(mime_type, ".webm")
    
    filename = f"{call_id}_{int(time.time())}{ext}"
    filepath = RECORDINGS_DIR / filename
    
    # Write audio to file
    with open(filepath, "wb") as f:
        f.write(audio_data)
    
    file_size = len(audio_data)
    logger.info(f"Recording saved: {filename} ({file_size / 1024:.1f} KB)")
    
    # Store in index
    recording_info = {
        "call_id": call_id,
        "filename": filename,
        "filepath": str(filepath),
        "mime_type": mime_type,
        "size_bytes": file_size,
        "saved_at": time.time(),
        "saved_at_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    recordings_index[call_id] = recording_info
    
    return recording_info


def get_recording(call_id: str) -> dict | None:
    """Get recording info for a call."""
    return recordings_index.get(call_id)


def get_recording_path(call_id: str) -> Path | None:
    """Get the file path for a recording."""
    info = recordings_index.get(call_id)
    if info:
        path = Path(info["filepath"])
        if path.exists():
            return path
    return None


def get_all_recordings() -> list[dict]:
    """Get all recording metadata."""
    return list(recordings_index.values())


def list_recording_files() -> list[str]:
    """List all recording files on disk."""
    return [f.name for f in RECORDINGS_DIR.iterdir() if f.is_file()]
