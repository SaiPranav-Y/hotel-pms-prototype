# -*- coding: utf-8 -*-
"""Alias normalization + BookingSlots logic (no DB)."""

from datetime import date

from app.dialogue import slots as S


class TestRoomType:
    def test_ac_aliases(self):
        for t in ["AC", "ఏసీ", "ఎసి", "ఏసి", "air conditioned"]:
            assert S.normalize_room_type(t) == "AC"

    def test_nonac_aliases(self):
        for t in ["Non-AC", "నాన్-ఏసీ", "నాన్ ఏసీ", "without ac"]:
            assert S.normalize_room_type(t) == "Non-AC"

    def test_garbage_returns_none(self):
        assert S.normalize_room_type("ఎ") is None
        assert S.normalize_room_type("") is None


class TestLocation:
    LOCS = ["Srisailam", "Tirupathi", "Vruddasramam"]

    def test_english_match(self):
        assert S.normalize_location("srisailam please", self.LOCS) == "Srisailam"

    def test_telugu_match(self):
        assert S.normalize_location("శ్రీశైలం", self.LOCS) == "Srisailam"

    def test_unknown_returns_none(self):
        assert S.normalize_location("గోవా", self.LOCS) is None

    def test_location_te_render(self):
        assert S.location_te("Srisailam") == "శ్రీశైలం"
        # Falls back to the raw name if no Telugu spelling is known.
        assert S.location_te("Unknownplace") == "Unknownplace"


class TestBookingSlots:
    def test_missing_in_ask_order(self):
        s = S.BookingSlots()
        assert s.missing_for_booking() == [
            "location", "check_in_date", "nights", "num_guests",
            "room_type", "guest_name",
        ]

    def test_complete_slots_have_nothing_missing(self):
        s = S.BookingSlots(
            location="Srisailam", check_in_date=date(2026, 10, 1), nights=2,
            num_guests=2, room_type="AC", guest_name="రవి",
        )
        assert s.missing_for_booking() == []

    def test_resolved_checkout_from_nights(self):
        s = S.BookingSlots(check_in_date=date(2026, 10, 1), nights=2)
        assert s.resolved_checkout() == date(2026, 10, 3)

    def test_resolved_checkout_none_without_dates(self):
        assert S.BookingSlots().resolved_checkout() is None
