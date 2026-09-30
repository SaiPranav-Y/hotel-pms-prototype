# -*- coding: utf-8 -*-
"""
Mic/audio-I/O tests that don't require live recording.

Covers the RMS loudness helper and the WAV writer (round-tripped via the stdlib
wave module). Live recording + playback are user-run via run_voice.py.
"""

import wave

import numpy as np

from app.audio import mic as M


class TestRms:
    def test_silence_is_zero(self):
        assert M._rms(np.zeros(1000, dtype=np.float32)) == 0.0

    def test_empty_is_zero(self):
        assert M._rms(np.zeros(0, dtype=np.float32)) == 0.0

    def test_full_scale_is_one(self):
        ones = np.ones(1000, dtype=np.float32)
        assert abs(M._rms(ones) - 1.0) < 1e-6

    def test_louder_signal_has_higher_rms(self):
        quiet = 0.1 * np.ones(1000, dtype=np.float32)
        loud = 0.5 * np.ones(1000, dtype=np.float32)
        assert M._rms(loud) > M._rms(quiet)


class TestSaveWav:
    def test_roundtrip_shape_and_rate(self, tmp_path):
        sr = 16000
        sig = (0.25 * np.sin(np.linspace(0, 2 * np.pi * 5, sr))).astype(np.float32)
        path = M.save_wav(sig, tmp_path / "t.wav", sample_rate=sr)

        with wave.open(path, "rb") as w:
            assert w.getnchannels() == 1
            assert w.getsampwidth() == 2         # 16-bit
            assert w.getframerate() == sr
            assert w.getnframes() == sr

    def test_clipping_is_bounded(self, tmp_path):
        # Values beyond [-1, 1] must be clipped, not wrapped.
        loud = np.array([5.0, -5.0, 0.0], dtype=np.float32)
        path = M.save_wav(loud, tmp_path / "c.wav", sample_rate=16000)
        with wave.open(path, "rb") as w:
            frames = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        assert frames.max() <= 32767 and frames.min() >= -32768


class TestAudioAvailable:
    def test_returns_bool(self):
        # Whatever the environment, this must be a clean boolean, never raise.
        assert isinstance(M.audio_available(), bool)
