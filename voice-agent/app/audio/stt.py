# -*- coding: utf-8 -*-
"""
Speech-to-text (Phase 2) — swappable STTProvider (steering §4).

Default backend: faster-whisper (CTranslate2). It is CPU-friendly (int8),
free, fully offline after the first model download, and does NOT require
PyTorch. The model is loaded lazily on first use so importing this module is
cheap and the text-mode agent never pays for it.

`NullSTT` is a safe fallback used when the backend can't be created (model not
downloaded, no network for the first pull, etc.) so the rest of the app keeps
working and degrades to "I didn't understand" rather than crashing.
"""

import logging
from abc import ABC, abstractmethod

import numpy as np

from app import config
from app.nlp_te import normalize as nz

logger = logging.getLogger(__name__)


class STTProvider(ABC):
    """Contract every speech-to-text backend must satisfy."""

    @abstractmethod
    def warm_up(self) -> None:
        """Preload the model so the first real transcription isn't slow."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """
        Transcribe mono float32 PCM in [-1, 1] to text.
        Returns "" when nothing intelligible was heard (never raises).
        """

    @property
    def available(self) -> bool:
        return True


class NullSTT(STTProvider):
    """No-op STT. Always returns empty text. Keeps the pipeline alive."""

    def warm_up(self) -> None:
        pass

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        return ""

    @property
    def available(self) -> bool:
        return False


class FasterWhisperSTT(STTProvider):
    """Telugu ASR via faster-whisper. Model loads lazily on first transcribe."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        language: str | None = None,
        beam_size: int | None = None,
    ):
        self.model_size = model_size or config.STT_MODEL
        self.device = device or config.STT_DEVICE
        self.compute_type = compute_type or config.STT_COMPUTE_TYPE
        self.language = language or config.STT_LANGUAGE
        self.beam_size = beam_size if beam_size is not None else config.STT_BEAM_SIZE
        self._model = None

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        # Imported lazily: the dependency is optional for text mode.
        from faster_whisper import WhisperModel
        logger.info(
            f"Loading faster-whisper '{self.model_size}' "
            f"({self.device}/{self.compute_type})… first run downloads the model."
        )
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )
        return self._model

    def warm_up(self) -> None:
        try:
            model = self._ensure_model()
            # Transcribe 0.5 s of silence to force graph/vocab init.
            silence = np.zeros(int(0.5 * 16000), dtype=np.float32)
            list(model.transcribe(silence, language=self.language, beam_size=1)[0])
        except Exception as e:
            logger.warning(f"STT warm-up failed: {e}")

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        try:
            audio = self._to_mono_16k_float32(audio, sample_rate)
            model = self._ensure_model()
            segments, _info = model.transcribe(
                audio,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,  # drop leading/trailing silence
            )
            text = "".join(seg.text for seg in segments).strip()
            # NFC-normalize so downstream Telugu matching is stable.
            return nz.nfc(text)
        except Exception as e:
            logger.error(f"transcribe failed: {e}")
            return ""

    @staticmethod
    def _to_mono_16k_float32(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        a = np.asarray(audio)
        if a.ndim > 1:  # stereo -> mono
            a = a.mean(axis=1)
        if a.dtype != np.float32:
            # Assume int16 PCM if integer; scale to [-1, 1].
            if np.issubdtype(a.dtype, np.integer):
                a = a.astype(np.float32) / 32768.0
            else:
                a = a.astype(np.float32)
        if sample_rate != 16000:
            a = _resample_to_16k(a, sample_rate)
        return a


def _resample_to_16k(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Cheap linear resample to 16 kHz (whisper's expected rate)."""
    if sample_rate == 16000 or audio.size == 0:
        return audio
    duration = audio.shape[0] / float(sample_rate)
    new_len = int(round(duration * 16000))
    if new_len <= 0:
        return np.zeros(0, dtype=np.float32)
    x_old = np.linspace(0.0, duration, num=audio.shape[0], endpoint=False)
    x_new = np.linspace(0.0, duration, num=new_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def get_stt(prefer: str = "faster-whisper") -> STTProvider:
    """
    Factory: return a ready STTProvider, falling back to NullSTT if the
    preferred backend can't be constructed (missing dep, etc.).
    """
    if prefer in ("faster-whisper", "whisper"):
        try:
            import faster_whisper  # noqa: F401
            return FasterWhisperSTT()
        except Exception as e:
            logger.warning(f"faster-whisper unavailable ({e}); using NullSTT.")
            return NullSTT()
    return NullSTT()
