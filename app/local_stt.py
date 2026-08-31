"""
Speech-to-Text — handled entirely by the browser's Web Speech API.
No server-side STT needed! The browser sends already-transcribed text.

This module exists as a fallback for when audio is sent instead of text,
using faster-whisper (lighter alternative to OpenAI whisper, no PyTorch needed).
If faster-whisper isn't installed, audio will be rejected with a friendly error.
"""

import logging

logger = logging.getLogger(__name__)


def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    """
    Fallback transcription for raw audio.
    In the browser-based demo, STT happens client-side via Web Speech API,
    so this should rarely be called.
    """
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        segments, _ = model.transcribe(temp_path, language="en")
        text = " ".join(s.text for s in segments).strip()
        os.unlink(temp_path)
        return text
        
    except ImportError:
        logger.info("No server-side STT available — using browser Web Speech API instead")
        return ""
    except Exception as e:
        logger.error(f"STT error: {e}")
        return ""
