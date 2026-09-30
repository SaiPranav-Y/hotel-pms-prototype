# -*- coding: utf-8 -*-
"""
Local mic + speaker I/O (Phase 4).

`record_until_silence()` captures a single caller turn: it streams mic frames,
tracks short-term loudness (RMS), and stops once the caller has been quiet for
AUDIO_SILENCE_SECS (or the hard cap AUDIO_MAX_TURN_SECS is hit). It also waits
for speech to actually start before arming the silence timer, so the leading
pause before someone speaks doesn't end the turn.

`play(path)` plays a WAV/MP3 file through the default speaker.

Both import `sounddevice`/`soundfile` lazily so this module (and the whole app)
still imports on machines with no audio backend; the functions raise a clear
AudioUnavailable in that case, which run_voice.py catches to fall back to text.
"""

import logging
import wave

import numpy as np

from app import config

logger = logging.getLogger(__name__)


class AudioUnavailable(RuntimeError):
    """Raised when no usable audio device/backend is present."""


def _rms(block: np.ndarray) -> float:
    if block.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))))


def audio_available() -> bool:
    """True if we can import sounddevice and see at least one input device."""
    try:
        import sounddevice as sd
        devs = sd.query_devices()
        return any(d.get("max_input_channels", 0) > 0 for d in devs)
    except Exception as e:
        logger.info(f"audio unavailable: {e}")
        return False


def record_until_silence(
    sample_rate: int | None = None,
    silence_rms: float | None = None,
    silence_secs: float | None = None,
    max_secs: float | None = None,
) -> np.ndarray:
    """
    Record one turn of mono float32 audio in [-1, 1]. Returns the samples.
    Raises AudioUnavailable if there's no input device.
    """
    sample_rate = sample_rate or config.AUDIO_SAMPLE_RATE
    silence_rms = silence_rms if silence_rms is not None else config.AUDIO_SILENCE_RMS
    silence_secs = silence_secs if silence_secs is not None else config.AUDIO_SILENCE_SECS
    max_secs = max_secs if max_secs is not None else config.AUDIO_MAX_TURN_SECS

    try:
        import sounddevice as sd
    except Exception as e:
        raise AudioUnavailable(f"sounddevice import failed: {e}") from e

    block_dur = 0.05  # 50 ms analysis blocks
    block_len = int(sample_rate * block_dur)
    max_blocks = int(max_secs / block_dur)
    silence_blocks_needed = int(silence_secs / block_dur)

    collected: list[np.ndarray] = []
    speech_started = False
    silent_run = 0

    try:
        with sd.InputStream(
            samplerate=sample_rate, channels=1, dtype="float32", blocksize=block_len
        ) as stream:
            for _ in range(max_blocks):
                block, _overflowed = stream.read(block_len)
                mono = block.reshape(-1)
                collected.append(mono.copy())
                level = _rms(mono)

                if not speech_started:
                    if level >= silence_rms:
                        speech_started = True
                    continue

                if level < silence_rms:
                    silent_run += 1
                    if silent_run >= silence_blocks_needed:
                        break
                else:
                    silent_run = 0
    except AudioUnavailable:
        raise
    except Exception as e:
        raise AudioUnavailable(f"recording failed: {e}") from e

    if not collected:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(collected).astype(np.float32)


def play(path) -> None:
    """Play an audio file (WAV or MP3) through the default output device."""
    path = str(path)
    try:
        import sounddevice as sd
        import soundfile as sf
    except Exception as e:
        raise AudioUnavailable(f"playback import failed: {e}") from e

    try:
        data, sr = sf.read(path, dtype="float32")
        sd.play(data, sr)
        sd.wait()
    except Exception as e:
        # soundfile can't decode mp3 without libsndfile>=1.1; log + skip rather
        # than crash the conversation.
        logger.warning(f"playback failed for {path}: {e}")


def save_wav(audio: np.ndarray, path, sample_rate: int | None = None) -> str:
    """Write mono float32 audio to a 16-bit PCM WAV (handy for debugging)."""
    sample_rate = sample_rate or config.AUDIO_SAMPLE_RATE
    path = str(path)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm16.tobytes())
    return path
