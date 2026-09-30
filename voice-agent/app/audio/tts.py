# -*- coding: utf-8 -*-
"""
Text-to-speech (Phase 3) — swappable TTSProvider (steering §4).

Backends:
  * EdgeTTS      — Microsoft Edge neural voices. Has a genuine Telugu voice
                   (te-IN-ShrutiNeural). Free (no API key) but needs network,
                   so it's GATED behind ALLOW_CLOUD_TTS per steering §4/§11.
  * OfflinePiperTTS / MmsTTS — offline seams. On this machine PyTorch is broken
                   so the neural offline path can't run; the class is a documented
                   stub that reports unavailable rather than crashing.
  * NullTTS      — writes nothing / plays nothing. Safe fallback.

Two non-negotiables from the steering are enforced here:
  1. Telugu-script guard: we never synthesize a line that has no Telugu
     characters (§1, §8). Non-Telugu input returns no audio.
  2. Static-phrase cache: greetings/prompts are synthesized once and reused,
     cutting latency on CPU (§10).

`synthesize(text) -> Path|None` writes an audio file and returns its path (None
on failure). The mic/speaker loop plays it; tests just assert the file exists.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app import config
from app.nlp_te import normalize as nz

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Contract every text-to-speech backend must satisfy."""

    @abstractmethod
    def _synthesize_raw(self, text: str, out_path: Path) -> bool:
        """Write audio for `text` to `out_path`. Return True on success."""

    def synthesize(self, text: str) -> Path | None:
        """
        Guard + cache wrapper around the backend. Returns the audio file path,
        or None if the text isn't Telugu or synthesis failed.
        """
        text = nz.nfc((text or "").strip())
        if not text:
            return None
        # Telugu-script guard: refuse to speak non-Telugu (protects TTS + brand).
        if not nz.is_telugu(text):
            logger.warning("TTS refused non-Telugu text.")
            return None

        cache_dir = Path(config.TTS_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha1(f"{self.cache_tag}:{text}".encode("utf-8")).hexdigest()[:16]
        out_path = cache_dir / f"{key}.{self.audio_ext}"
        if out_path.exists() and out_path.stat().st_size > 0:
            return out_path  # cache hit

        try:
            if self._synthesize_raw(text, out_path):
                return out_path
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
        return None

    def warm_up(self) -> None:
        """Pre-synthesize the common static phrases so the first turn is fast."""
        from app.dialogue import templates_te as T
        for phrase in (T.GREETING, T.NOT_UNDERSTOOD, T.PLEASE_HOLD, T.GOODBYE):
            try:
                self.synthesize(phrase)
            except Exception:
                pass

    # Subclasses set these.
    cache_tag = "base"
    audio_ext = "wav"

    @property
    def available(self) -> bool:
        return True


class NullTTS(TTSProvider):
    """Produces no audio. Used when no real backend is available."""

    cache_tag = "null"
    audio_ext = "wav"

    def _synthesize_raw(self, text: str, out_path: Path) -> bool:
        return False

    def synthesize(self, text: str) -> Path | None:
        return None

    def warm_up(self) -> None:
        pass

    @property
    def available(self) -> bool:
        return False


class EdgeTTS(TTSProvider):
    """
    Telugu TTS via edge-tts (free, no key). Needs network. GATED: only used when
    config.ALLOW_CLOUD_TTS is true, because it sends text to Microsoft's service.
    """

    audio_ext = "mp3"

    def __init__(self, voice: str | None = None, rate: str | None = None,
                 pitch: str | None = None):
        self.voice = voice or config.TTS_VOICE_TE
        # Prosody makes the voice sound more natural: a slightly slower rate and
        # a touch lower pitch read warmer and clearer for Telugu than the default.
        self.rate = rate if rate is not None else config.TTS_RATE
        self.pitch = pitch if pitch is not None else config.TTS_PITCH
        # Cache key includes prosody so changing rate/pitch re-synthesizes.
        self.cache_tag = f"edge:{self.voice}:{self.rate}:{self.pitch}"

    def _synthesize_raw(self, text: str, out_path: Path) -> bool:
        import asyncio
        import edge_tts

        async def _run():
            # edge-tts accepts rate="+/-N%" and pitch="+/-NHz" for prosody.
            comm = edge_tts.Communicate(
                text, self.voice, rate=self.rate, pitch=self.pitch
            )
            await comm.save(str(out_path))

        # edge-tts is async; run it to completion synchronously.
        try:
            asyncio.run(_run())
        except RuntimeError:
            # Already inside an event loop (rare here): use a fresh loop.
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_run())
            finally:
                loop.close()
        return out_path.exists() and out_path.stat().st_size > 0

    @property
    def available(self) -> bool:
        return bool(config.ALLOW_CLOUD_TTS)


class OfflinePiperTTS(TTSProvider):
    """
    Offline neural TTS seam (Piper / MMS-tel). Kept as a documented stub: this
    machine's PyTorch/ONNX runtime isn't usable, so it reports unavailable.
    Wire a Piper voice or facebook/mms-tts-tel here for a fully offline path.
    """

    cache_tag = "piper"
    audio_ext = "wav"

    def _synthesize_raw(self, text: str, out_path: Path) -> bool:
        raise NotImplementedError(
            "Offline Piper/MMS TTS is not wired on this machine. "
            "Install a Piper Telugu voice or facebook/mms-tts-tel (needs a "
            "working PyTorch/ONNX) and implement _synthesize_raw."
        )

    @property
    def available(self) -> bool:
        return False


def get_tts(engine: str | None = None) -> TTSProvider:
    """
    Factory: return a ready TTSProvider following the steering's safety gate.

    - "edge": only if ALLOW_CLOUD_TTS is true AND edge-tts imports; else NullTTS.
    - "piper"/"mms": offline seam (currently unavailable) -> NullTTS.
    """
    engine = (engine or config.TTS_ENGINE).lower()

    if engine == "edge":
        if not config.ALLOW_CLOUD_TTS:
            logger.info("edge-tts requested but ALLOW_CLOUD_TTS=false; using NullTTS.")
            return NullTTS()
        try:
            import edge_tts  # noqa: F401
            return EdgeTTS()
        except Exception as e:
            logger.warning(f"edge-tts unavailable ({e}); using NullTTS.")
            return NullTTS()

    if engine in ("piper", "mms"):
        prov = OfflinePiperTTS()
        return prov if prov.available else NullTTS()

    logger.warning(f"Unknown TTS engine '{engine}'; using NullTTS.")
    return NullTTS()
