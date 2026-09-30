# -*- coding: utf-8 -*-
"""
Unit tests for Telugu number/date parsing + rendering + the Telugu-script guard.

These are pure functions (no DB, no LLM). Dates are computed relative to a fixed
base date so the assertions are stable regardless of when the suite runs.
"""

from datetime import date, timedelta

import pytest

from app.nlp_te import normalize as nz


# ── Telugu-script guard ───────────────────────────────────────────────────
class TestTeluguGuard:
    def test_pure_telugu_is_telugu(self):
        assert nz.is_telugu("నమస్కారం")

    def test_empty_is_not_telugu(self):
        assert not nz.is_telugu("")
        assert not nz.is_telugu(None)

    def test_pure_latin_is_not_telugu(self):
        assert not nz.is_telugu("hello world")

    def test_mixed_counts_as_telugu(self):
        # One Telugu char is enough to pass the outgoing guard.
        assert nz.is_telugu("Karivena కి స్వాగతం")

    def test_mostly_latin_detects_bad_llm_output(self):
        assert nz.mostly_latin("this is english")
        assert not nz.mostly_latin("పూర్తిగా తెలుగు వాక్యం")

    def test_mostly_latin_ignores_non_letters(self):
        assert not nz.mostly_latin("12345 !@#")


# ── number -> Telugu words ────────────────────────────────────────────────
class TestNumberToTelugu:
    @pytest.mark.parametrize("n,expected", [
        (0, "సున్నా"),
        (1, "ఒకటి"),
        (2, "రెండు"),
        (10, "పది"),
        (12, "పన్నెండు"),
    ])
    def test_small_numbers(self, n, expected):
        assert nz.number_to_telugu(n) == expected

    def test_thousand_words(self):
        # 1500 and 3000 are the prices we actually quote.
        assert nz.number_to_telugu(1500) == "వెయ్యి ఐదు వందల"
        assert nz.number_to_telugu(3000) == "మూడు వేల"

    def test_output_is_telugu(self):
        for n in (0, 5, 50, 500, 1500, 3000, 25000):
            assert nz.is_telugu(nz.number_to_telugu(n))


class TestDigitsGrouped:
    def test_phone_grouped_is_telugu(self):
        out = nz.digits_to_telugu_grouped("9876543210", group=3)
        assert nz.is_telugu(out)
        # 10 digits in groups of 3 -> 4 comma-separated chunks
        assert out.count(",") == 3

    def test_booking_id_grouped(self):
        out = nz.digits_to_telugu_grouped("7993", group=4)
        assert out == "ఏడు తొమ్మిది తొమ్మిది మూడు"


# ── parse_number ──────────────────────────────────────────────────────────
class TestParseNumber:
    @pytest.mark.parametrize("text,expected", [
        ("3", 3),
        ("రెండు", 2),
        ("ఒకటి", 1),
        ("two", 2),
        ("5 people", 5),
    ])
    def test_variants(self, text, expected):
        assert nz.parse_number(text) == expected

    @pytest.mark.parametrize("text,expected", [
        ("ఒకరు", 1),
        ("ఇద్దరు", 2),
        ("ముగ్గురు", 3),
        ("నలుగురు", 4),
    ])
    def test_human_counting_words(self, text, expected):
        # Regression: "ఇద్దరు" must parse as 2 guests (the bug fixed in Task 6).
        assert nz.parse_number(text) == expected

    def test_unknown_returns_default(self):
        assert nz.parse_number("గోబెల్డిగూక్", default=None) is None
        assert nz.parse_number("", default=7) == 7


# ── dates ─────────────────────────────────────────────────────────────────
class TestDates:
    BASE = date(2026, 6, 26)  # a Friday

    def test_tomorrow(self):
        assert nz.parse_relative_date("రేపు", base=self.BASE) == self.BASE + timedelta(days=1)

    def test_day_after(self):
        assert nz.parse_relative_date("ఎల్లుండి", base=self.BASE) == self.BASE + timedelta(days=2)

    def test_today(self):
        assert nz.parse_relative_date("ఈరోజు", base=self.BASE) == self.BASE

    def test_iso(self):
        assert nz.parse_relative_date("2026-10-12", base=self.BASE) == date(2026, 10, 12)

    def test_next_weekday_is_future(self):
        # From Friday, "శనివారం" (Saturday) is the next day.
        d = nz.parse_relative_date("శనివారం", base=self.BASE)
        assert d is not None and d > self.BASE and d.weekday() == 5

    def test_unrecognised_returns_none(self):
        assert nz.parse_relative_date("ఎప్పుడైనా", base=self.BASE) is None

    def test_date_to_telugu_is_telugu(self):
        assert nz.date_to_telugu(date(2026, 10, 1)) == "అక్టోబర్ ఒకటి"
        assert nz.is_telugu(nz.date_to_telugu(self.BASE))


class TestNights:
    def test_nights_telugu(self):
        assert nz.parse_nights("రెండు రోజులు") == 2
        assert nz.parse_nights("ఒక రాత్రి") == 1

    def test_nights_english(self):
        assert nz.parse_nights("3 nights") == 3
