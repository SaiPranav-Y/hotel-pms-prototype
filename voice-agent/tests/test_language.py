# -*- coding: utf-8 -*-
"""
Bilingual (English / Telugu) language-choice tests.

Covers the language picker, template parity, and full booking dialogues in each
language via the SQLite data source (offline, always runnable).
"""

import pytest

from app.nlp_te import normalize as nz
from app.dialogue import templates_te as T_TE
from app.dialogue import templates_en as T_EN
from app.dialogue import templates_common as C
from app.dialogue.state_machine import DialogueSession, ASK_LANGUAGE
from app.tools.datasource import SqliteDataSource


# ── Language picker ────────────────────────────────────────────────────────
class TestLanguageChoice:
    @pytest.mark.parametrize("text,expected", [
        ("1", "en"), ("2", "te"),
        ("English", "en"), ("english please", "en"),
        ("telugu", "te"), ("తెలుగు", "te"), ("ఇంగ్లీష్", "en"),
    ])
    def test_detect(self, text, expected):
        assert C.detect_language_choice(text) == expected

    @pytest.mark.parametrize("text", ["", "maybe", "3", "1 or 2"])
    def test_unclear_returns_none(self, text):
        assert C.detect_language_choice(text) is None


# ── Template parity ────────────────────────────────────────────────────────
class TestTemplateParity:
    def test_same_public_names(self):
        def public(mod):
            return {n for n in dir(mod) if not n.startswith("_")}
        te = public(T_TE)
        en = public(T_EN)
        # Every public name in the Telugu module must exist in the English one.
        missing = te - en
        # HOTEL/config are fine; only flag template names.
        assert not missing, f"templates_en missing: {missing}"

    def test_english_static_not_telugu(self):
        assert not nz.is_telugu(T_EN.GREETING)
        assert not nz.is_telugu(T_EN.ASK_LOCATION)
        assert not nz.is_telugu(T_EN.CONFIRM_PROMPT)

    def test_telugu_static_is_telugu(self):
        assert nz.is_telugu(T_TE.GREETING)
        assert nz.is_telugu(T_TE.ASK_LOCATION)


# ── Picker flow through DialogueSession ────────────────────────────────────
class TestPickerFlow:
    def _session(self, lang="ask"):
        return DialogueSession(caller_id="+91", locations=SqliteDataSource().locations(),
                               data_source=SqliteDataSource(), lang=lang)

    def test_ask_shows_bilingual_picker(self, seeded_db):
        s = self._session("ask")
        greeting = s.greeting()
        assert s.state == ASK_LANGUAGE
        assert "English" in greeting and nz.is_telugu(greeting)

    def test_pick_english(self, seeded_db):
        s = self._session("ask")
        s.greeting()
        reply = s.handle("1")
        assert s.lang == "en"
        assert not nz.is_telugu(reply)          # English greeting + question
        assert "Which place" in reply

    def test_pick_telugu(self, seeded_db):
        s = self._session("ask")
        s.greeting()
        reply = s.handle("2")
        assert s.lang == "te"
        assert nz.is_telugu(reply)

    def test_unclear_reasks(self, seeded_db):
        s = self._session("ask")
        s.greeting()
        reply = s.handle("huh?")
        assert s.state == ASK_LANGUAGE          # still choosing
        assert "English" in reply               # bilingual retry


# ── Full English booking (SQLite) ──────────────────────────────────────────
class TestEnglishBooking:
    def _session(self):
        return DialogueSession(caller_id="+919876500099",
                               locations=SqliteDataSource().locations(),
                               data_source=SqliteDataSource(), lang="en")

    def test_full_english_booking(self, seeded_db):
        s = self._session()
        greeting = s.greeting()
        assert not nz.is_telugu(greeting)
        last = None
        for t in ["Srisailam", "tomorrow", "2 nights", "2", "AC",
                  "Ravi Kumar", "yes"]:
            last = s.handle(t)
            assert not nz.is_telugu(last), f"English turn leaked Telugu: {last!r}"
        assert s.finished
        assert "booking number" in last.lower()

    def test_english_booking_number_is_plain(self, seeded_db):
        s = self._session()
        s.greeting()
        for t in ["Srisailam", "tomorrow", "1 night", "1", "AC", "Sita", "yes"]:
            last = s.handle(t)
        # Plain digits, not Telugu-spelled words.
        assert any(ch.isdigit() for ch in last)


# ── Full Telugu booking still works ────────────────────────────────────────
class TestTeluguBooking:
    def test_full_telugu_booking(self, seeded_db):
        s = DialogueSession(caller_id="+919876500098",
                            locations=SqliteDataSource().locations(),
                            data_source=SqliteDataSource(), lang="te")
        s.greeting()
        last = None
        for t in ["బుక్", "శ్రీశైలం", "రేపు", "రెండు రోజులు", "ఇద్దరు", "ఏసీ",
                  "రవి కుమార్", "అవును"]:
            last = s.handle(t)
            assert nz.is_telugu(last)
        assert s.finished and "బుకింగ్ నంబర్" in last


# ── Live-mode English booking (skips without the demo) ─────────────────────
def _live_available() -> bool:
    try:
        from app.integration import karivena
        return karivena.available()
    except Exception:
        return False


@pytest.mark.skipif(not _live_available(),
                    reason="hotel-voice-booking-demo not importable")
def test_live_english_booking():
    from app.tools.datasource import LiveDataSource
    ds = LiveDataSource()
    s = DialogueSession(caller_id="+919876500097", locations=ds.locations(),
                        data_source=ds, lang="en")
    s.greeting()
    last = None
    for t in ["Srisailam", "tomorrow", "2 nights", "2", "AC", "Ravi Kumar",
              "9876543210", "Bharadwaja", "ravi at gmail dot com", "yes"]:
        last = s.handle(t)
        assert not nz.is_telugu(last)
    assert s.finished and "booking number" in last.lower()
