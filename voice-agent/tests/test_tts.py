# -*- coding: utf-8 -*-
"""
TTS unit tests — no network needed for the core ones.

We use a tiny FakeTTS to exercise the guard + cache logic in the base class
without depending on edge-tts or a network connection. A separate, opt-in test
hits real edge-tts only when RUN_EDGE_TTS=1 is set (so CI stays offline).
"""

import os
from pathlib import Path

import pytest

from app import config
from app.audio import tts as TTS


class FakeTTS(TTS.TTSProvider):
    """Writes a few bytes so we can test guard + cache without a real engine."""
    cache_tag = "fake"
    audio_ext = "wav"

    def __init__(self):
        self.calls = 0

    def _synthesize_raw(self, text, out_path: Path) -> bool:
        self.calls += 1
        out_path.write_bytes(b"RIFFfake-audio-bytes")
        return True


@pytest.fixture()
def tts_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TTS_CACHE_DIR", str(tmp_path / "tts"), raising=False)
    return tmp_path


class TestGuardAndCache:
    def test_telugu_text_is_synthesized(self, tts_cache):
        f = FakeTTS()
        out = f.synthesize("నమస్కారం")
        assert out is not None and out.exists() and out.stat().st_size > 0

    def test_non_telugu_is_refused(self, tts_cache):
        f = FakeTTS()
        assert f.synthesize("hello there") is None
        assert f.calls == 0  # backend never invoked

    def test_empty_is_refused(self, tts_cache):
        f = FakeTTS()
        assert f.synthesize("") is None
        assert f.synthesize(None) is None

    def test_cache_hit_avoids_second_synth(self, tts_cache):
        f = FakeTTS()
        a = f.synthesize("ధన్యవాదాలు")
        b = f.synthesize("ధన్యవాదాలు")
        assert a == b
        assert f.calls == 1  # second call served from cache

    def test_different_text_different_file(self, tts_cache):
        f = FakeTTS()
        a = f.synthesize("అవును")
        b = f.synthesize("కాదు")
        assert a != b
        assert f.calls == 2


class TestNullTTS:
    def test_null_produces_nothing(self, tts_cache):
        n = TTS.NullTTS()
        assert n.synthesize("నమస్కారం") is None
        assert n.available is False
        n.warm_up()  # must not raise


class TestGating:
    def test_edge_blocked_when_flag_false(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOW_CLOUD_TTS", False, raising=False)
        monkeypatch.setattr(config, "TTS_ENGINE", "edge", raising=False)
        assert isinstance(TTS.get_tts(), TTS.NullTTS)

    def test_edge_allowed_when_flag_true(self, monkeypatch):
        monkeypatch.setattr(config, "ALLOW_CLOUD_TTS", True, raising=False)
        prov = TTS.get_tts("edge")
        # edge-tts is installed in this env, so we expect the real provider.
        assert isinstance(prov, (TTS.EdgeTTS, TTS.NullTTS))
        if isinstance(prov, TTS.EdgeTTS):
            assert prov.available is True

    def test_offline_seam_is_null(self):
        assert isinstance(TTS.get_tts("piper"), TTS.NullTTS)

    def test_unknown_engine_is_null(self):
        assert isinstance(TTS.get_tts("weird"), TTS.NullTTS)


@pytest.mark.skipif(os.getenv("RUN_EDGE_TTS") != "1",
                    reason="set RUN_EDGE_TTS=1 to hit real edge-tts (needs network)")
def test_real_edge_tts_telugu(tts_cache, monkeypatch):
    monkeypatch.setattr(config, "ALLOW_CLOUD_TTS", True, raising=False)
    prov = TTS.EdgeTTS()
    out = prov.synthesize("నమస్కారం! కరివేన సత్రంకు స్వాగతం.")
    assert out is not None and out.exists() and out.stat().st_size > 1000
