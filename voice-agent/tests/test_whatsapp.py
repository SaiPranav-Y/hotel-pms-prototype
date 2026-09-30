# -*- coding: utf-8 -*-
"""
WhatsApp text channel tests.

Covers the channel conversation (SQLite mode), payload parsing / phone
normalization, and the webhook via FastAPI's TestClient. A live-mode channel
test skips when the demo project isn't importable.
"""

import pytest

from app.nlp_te import normalize as nz
from app.channels.whatsapp import WhatsAppChannel
from app.channels import whatsapp_io
from app.tools.datasource import SqliteDataSource


# ── whatsapp_io ────────────────────────────────────────────────────────────
class TestPayloadParsing:
    def test_simple_shape(self):
        assert whatsapp_io.parse_incoming({"from": "+91999", "text": "hi"}) == ("+91999", "hi")

    def test_alt_keys(self):
        assert whatsapp_io.parse_incoming({"phone": "+91999", "message": "hi"}) == ("+91999", "hi")

    def test_meta_shape(self):
        body = {"entry": [{"changes": [{"value": {"messages": [
            {"from": "919876543210", "text": {"body": "namaste"}}]}}]}]}
        assert whatsapp_io.parse_incoming(body) == ("919876543210", "namaste")

    def test_empty_payload(self):
        assert whatsapp_io.parse_incoming({}) == ("", "")

    def test_normalize_phone_adds_country_code(self):
        assert whatsapp_io.normalize_phone("9876543210") == "919876543210"
        assert whatsapp_io.normalize_phone("+91 98765 43210") == "919876543210"


class TestMockSend:
    def test_mock_send_succeeds(self, monkeypatch):
        # No provider configured → MOCK send always "succeeds" (logs).
        monkeypatch.setattr(whatsapp_io.config, "WHATSAPP_TOKEN", "", raising=False)
        monkeypatch.setattr(whatsapp_io.config, "WHATSAPP_PHONE_ID", "", raising=False)
        monkeypatch.setattr(whatsapp_io.config, "WHATSAPP_WEBHOOK_URL", "", raising=False)
        r = whatsapp_io.send("+919876543210", "నమస్కారం")
        assert r["success"] and r["provider"] == "mock"


# ── Channel conversation (SQLite) ──────────────────────────────────────────
class TestChannelSqlite:
    def _channel(self):
        # Force Telugu so these tests exercise the booking flow directly
        # (the bilingual picker is covered separately in test_language.py).
        return WhatsAppChannel(data_source=SqliteDataSource(), lang="te")

    def test_greeting_is_telugu(self, seeded_db):
        ch = self._channel()
        reply = ch.handle_incoming("+919876500001", "hi")
        assert nz.is_telugu(reply)
        assert "నమస్కారం" in reply

    def test_full_booking(self, seeded_db):
        ch = self._channel()
        phone = "+919876500002"
        ch.handle_incoming(phone, "namaste")
        last = None
        for t in ["శ్రీశైలం", "రేపు", "రెండు రోజులు", "ఇద్దరు", "ఏసీ",
                  "రవి కుమార్", "అవును"]:
            last = ch.handle_incoming(phone, t)
            assert nz.is_telugu(last)
        assert "బుకింగ్ నంబర్" in last
        # Finished conversation is cleared.
        assert ch.active_count() == 0

    def test_sessions_are_isolated(self, seeded_db):
        ch = self._channel()
        a, b = "+91900000001", "+91900000002"
        ch.handle_incoming(a, "hi")
        ch.handle_incoming(a, "శ్రీశైలం")   # A is now on the check-in question
        # B starts fresh and should be asked for location, not check-in.
        rb = ch.handle_incoming(b, "hi")
        assert "ప్రాంతం" in rb  # location question word
        assert ch.active_count() == 2

    def test_reset_starts_over(self, seeded_db):
        ch = self._channel()
        phone = "+91900000003"
        ch.handle_incoming(phone, "hi")
        ch.handle_incoming(phone, "శ్రీశైలం")
        reply = ch.handle_incoming(phone, "cancel")
        assert nz.is_telugu(reply) and "నమస్కారం" in reply


# ── Webhook (FastAPI TestClient) ───────────────────────────────────────────
class TestWebhook:
    def _client(self):
        from fastapi.testclient import TestClient
        import run_whatsapp
        return TestClient(run_whatsapp.app)

    def test_health(self, seeded_db):
        r = self._client().get("/health")
        assert r.status_code == 200 and r.json()["status"] == "ok"

    def test_webhook_simple(self, seeded_db):
        r = self._client().post("/webhook", json={"from": "+919876500010", "text": "namaste"})
        assert r.status_code == 200
        assert "నమస్కారం" in r.json()["reply"]

    def test_webhook_meta_shape(self, seeded_db):
        body = {"entry": [{"changes": [{"value": {"messages": [
            {"from": "919876500011", "text": {"body": "hi"}}]}}]}]}
        r = self._client().post("/webhook", json=body)
        assert r.status_code == 200 and nz.is_telugu(r.json()["reply"])

    def test_webhook_no_phone(self, seeded_db):
        r = self._client().post("/webhook", json={"text": "hi"})
        assert r.status_code == 400

    def test_webhook_verify_challenge(self, seeded_db):
        from app import config
        r = self._client().get("/webhook", params={
            "hub.mode": "subscribe",
            "hub.verify_token": config.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": "12345",
        })
        assert r.status_code == 200 and r.text == "12345"

    def test_webhook_verify_bad_token(self, seeded_db):
        r = self._client().get("/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": "wrong",
            "hub.challenge": "x",
        })
        assert r.status_code == 403


# ── Live-mode channel (skips without the demo) ─────────────────────────────
def _live_available() -> bool:
    try:
        from app.integration import karivena
        return karivena.available()
    except Exception:
        return False


@pytest.mark.skipif(not _live_available(),
                    reason="hotel-voice-booking-demo not importable")
def test_live_channel_collects_gotram_email():
    from app.tools.datasource import LiveDataSource
    ch = WhatsAppChannel(data_source=LiveDataSource(), lang="te")
    phone = "+919876590001"
    ch.handle_incoming(phone, "namaste")
    last = None
    for t in ["శ్రీశైలం", "రేపు", "రెండు రోజులు", "ఇద్దరు", "ఏసీ", "రవి కుమార్",
              "Bharadwaja", "ravi at gmail dot com", "అవును"]:
        last = ch.handle_incoming(phone, t)
        assert nz.is_telugu(last)
    # Live booking confirms with a booking number (phone came from the sender).
    assert "బుకింగ్ నంబర్" in last
