"""
Local Text-to-Speech using Piper (100% free, runs on your machine).
Falls back to a simple edge-tts (Microsoft Edge free TTS) if Piper isn't installed.

Piper: https://github.com/rhasspy/piper (fast, offline, natural voices)
Edge-TTS: https://github.com/rany2/edge-tts (free, uses Edge's online TTS - no API key needed)
"""

import logging
import io
import subprocess
import tempfile
import os
import wave

logger = logging.getLogger(__name__)

# Try to detect which TTS is available
_tts_engine = None


def _detect_tts_engine():
    """Detect which TTS engine is available."""
    global _tts_engine
    
    if _tts_engine is not None:
        return _tts_engine

    # Try Piper first (fully offline)
    try:
        result = subprocess.run(
            ["piper", "--help"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0 or b"piper" in result.stdout.lower() or b"piper" in result.stderr.lower():
            _tts_engine = "piper"
            logger.info("TTS engine: Piper (offline)")
            return _tts_engine
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fall back to edge-tts (free, online, no API key)
    try:
        import edge_tts
        _tts_engine = "edge_tts"
        logger.info("TTS engine: Edge-TTS (free online)")
        return _tts_engine
    except ImportError:
        pass

    # Last resort: browser's built-in Web Speech API (handled client-side)
    _tts_engine = "browser"
    logger.info("TTS engine: Browser Web Speech API (client-side)")
    return _tts_engine


async def synthesize_speech(text: str) -> bytes | None:
    """
    Convert text to speech audio (WAV format).
    
    Args:
        text: Text to speak
        
    Returns:
        WAV audio bytes, or None if using browser-side TTS
    """
    engine = _detect_tts_engine()

    if engine == "piper":
        return _synthesize_piper(text)
    elif engine == "edge_tts":
        return await _synthesize_edge_tts(text)
    else:
        # Browser handles TTS client-side
        return None


def _synthesize_piper(text: str) -> bytes | None:
    """Use Piper for offline TTS."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        result = subprocess.run(
            ["piper", "--model", "en_US-amy-medium", "--output_file", temp_path],
            input=text.encode(),
            capture_output=True,
            timeout=30,
        )

        if result.returncode == 0 and os.path.exists(temp_path):
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            os.unlink(temp_path)
            return audio_data
        else:
            logger.error(f"Piper error: {result.stderr.decode()}")
            os.unlink(temp_path)
            return None

    except Exception as e:
        logger.error(f"Piper TTS error: {e}")
        return None


async def _synthesize_edge_tts(text: str) -> bytes | None:
    """Use Edge-TTS (free, no API key, uses Microsoft's TTS)."""
    try:
        import edge_tts
        from app.pronunciation import apply_pronunciation

        # Apply pronunciation rules before TTS
        text_for_tts = apply_pronunciation(text)

        communicate = edge_tts.Communicate(
            text_for_tts,
            voice="en-IN-NeerjaNeural",  # Indian English female voice
            rate="+5%",  # Slightly faster for professional pace
            pitch="+0Hz",
        )

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        await communicate.save(temp_path)

        with open(temp_path, "rb") as f:
            audio_data = f.read()
        os.unlink(temp_path)
        return audio_data

    except Exception as e:
        logger.error(f"Edge-TTS error: {e}")
        return None
