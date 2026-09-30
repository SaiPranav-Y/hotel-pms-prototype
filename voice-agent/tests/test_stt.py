# -*- coding: utf-8 -*-
"""
STT unit tests that do NOT require a microphone or a downloaded model.

They cover the audio-shaping helpers (mono mix, dtype scaling, resample) and
the NullSTT fallback path. The actual Telugu transcription accuracy is a live
test the user runs with run_voice.py.
"""

import numpy as np

from app.audio import stt as S


class TestAudioShaping:
    def test_stereo_to_mono(self):
        stereo = np.zeros((100, 2), dtype=np.float32)
        stereo[:, 0] = 0.5
        stereo[:, 1] = -0.5
        out = S.FasterWhisperSTT._to_mono_16k_float32(stereo, 16000)
        assert out.ndim == 1
        assert np.allclose(out, 0.0)  # 0.5 + -0.5 averaged = 0

    def test_int16_scaled_to_unit_range(self):
        pcm = np.array([32767, -32768, 0], dtype=np.int16)
        out = S.FasterWhisperSTT._to_mono_16k_float32(pcm, 16000)
        assert out.dtype == np.float32
        assert -1.01 <= out.min() and out.max() <= 1.01

    def test_resample_changes_length(self):
        # 1 second at 48k -> ~1 second at 16k (about 1/3 the samples).
        sig = np.sin(np.linspace(0, 2 * np.pi * 5, 48000)).astype(np.float32)
        out = S._resample_to_16k(sig, 48000)
        assert abs(out.shape[0] - 16000) <= 2

    def test_resample_noop_at_16k(self):
        sig = np.ones(16000, dtype=np.float32)
        out = S._resample_to_16k(sig, 16000)
        assert out.shape[0] == 16000

    def test_empty_audio_safe(self):
        out = S._resample_to_16k(np.zeros(0, dtype=np.float32), 48000)
        assert out.shape[0] == 0


class TestNullSTT:
    def test_returns_empty_and_unavailable(self):
        n = S.NullSTT()
        assert n.transcribe(np.zeros(10, dtype=np.float32), 16000) == ""
        assert n.available is False
        n.warm_up()  # must not raise


class TestFactory:
    def test_get_stt_returns_provider(self):
        # faster-whisper is installed in this env, so we expect the real class;
        # but the test only asserts the contract so it passes either way.
        prov = S.get_stt("faster-whisper")
        assert isinstance(prov, S.STTProvider)

    def test_unknown_backend_is_null(self):
        assert isinstance(S.get_stt("nonexistent-engine"), S.NullSTT)
