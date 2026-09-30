# -*- coding: utf-8 -*-
"""Phone + email parsing used in live-booking mode (no DB, no network)."""

from app.nlp_te import normalize as nz


class TestParsePhone:
    def test_plain_10_digits(self):
        assert nz.parse_phone("9876543210") == "9876543210"

    def test_with_spaces_and_dashes(self):
        assert nz.parse_phone("98765 43210") == "9876543210"
        assert nz.parse_phone("987-654-3210") == "9876543210"

    def test_country_code_stripped(self):
        assert nz.parse_phone("+91 9876543210") == "9876543210"
        assert nz.parse_phone("919876543210") == "9876543210"

    def test_trunk_zero_stripped(self):
        assert nz.parse_phone("09876543210") == "9876543210"

    def test_telugu_digit_words(self):
        # "తొమ్మిది ఎనిమిది ఏడు ఆరు ఐదు నాలుగు మూడు రెండు ఒకటి సున్నా" = 9876543210
        spoken = "తొమ్మిది ఎనిమిది ఏడు ఆరు ఐదు నాలుగు మూడు రెండు ఒకటి సున్నా"
        assert nz.parse_phone(spoken) == "9876543210"

    def test_too_few_digits_returns_none(self):
        assert nz.parse_phone("12345") is None
        assert nz.parse_phone("") is None


class TestParseEmail:
    def test_literal_email(self):
        assert nz.parse_email("ravi.kumar@gmail.com") == "ravi.kumar@gmail.com"

    def test_uppercase_normalized(self):
        assert nz.parse_email("Ravi@Gmail.COM") == "ravi@gmail.com"

    def test_spoken_at_dot_english(self):
        assert nz.parse_email("ravi at gmail dot com") == "ravi@gmail.com"

    def test_spoken_at_dot_telugu(self):
        # యాట్ = at, డాట్ = dot
        assert nz.parse_email("ravi యాట్ gmail డాట్ com") == "ravi@gmail.com"

    def test_no_email_returns_none(self):
        assert nz.parse_email("hello there") is None
        assert nz.parse_email("") is None
