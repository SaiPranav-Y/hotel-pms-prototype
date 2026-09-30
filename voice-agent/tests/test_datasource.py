# -*- coding: utf-8 -*-
"""
DataSource adapter tests.

SQLite tests always run (against the isolated seeded_db fixture). Live tests
run only when the sibling hotel-voice-booking-demo can be imported; otherwise
they skip, so the suite stays green on a checkout that doesn't have the demo.
"""

from datetime import timedelta

import pytest

from app import config
from app.nlp_te import normalize as nz
from app.tools.datasource import (
    DataSource, SqliteDataSource, get_data_source, AvailabilityResult, BookResult,
)

FULL_LOC = "Vruddasramam"


def _dates():
    ci = nz.today() + timedelta(days=1)
    return ci, ci + timedelta(days=1)


class TestSqliteDataSource:
    def test_factory_returns_sqlite_by_default(self, seeded_db):
        assert isinstance(get_data_source("sqlite"), SqliteDataSource)

    def test_extra_required_is_empty(self):
        assert SqliteDataSource().extra_required == ()

    def test_availability(self, seeded_db):
        ci, co = _dates()
        ds = SqliteDataSource()
        r = ds.check_availability(location=FULL_LOC, room_type="AC",
                                  check_in=ci, check_out=co, num_rooms=1, guests=1)
        assert isinstance(r, AvailabilityResult)
        assert r.available and r.rooms_available >= 1 and r.price_per_night > 0

    def test_book_get_cancel(self, seeded_db):
        ci, co = _dates()
        ds = SqliteDataSource()
        res = ds.create_booking(location=FULL_LOC, room_type="AC",
                                guest_name="రవి", phone="9876543210",
                                check_in=ci, check_out=co, guests=1, num_rooms=1)
        assert isinstance(res, BookResult) and res.success and res.booking_id
        got = ds.get_booking(booking_id=res.booking_id)
        assert got and got["booking_id"] == res.booking_id
        assert ds.cancel_booking(res.booking_id)

    def test_locations_nonempty(self, seeded_db):
        assert FULL_LOC in SqliteDataSource().locations()

    def test_normalize_location_telugu(self, seeded_db):
        # Falls back to our slot matcher against seeded locations.
        assert SqliteDataSource().normalize_location("శ్రీశైలం") == "Srisailam"


# ── Live backend (skips if the demo project isn't importable) ──────────────
def _live_available() -> bool:
    try:
        from app.integration import karivena
        return karivena.available()
    except Exception:
        return False


live = pytest.mark.skipif(not _live_available(),
                          reason="hotel-voice-booking-demo not importable")


@live
class TestLiveDataSource:
    def _ds(self):
        from app.tools.datasource import LiveDataSource
        return LiveDataSource()

    def test_extra_required(self):
        assert self._ds().extra_required == ("phone", "gotram", "email")

    def test_locations_include_srisailam(self):
        assert "Srisailam" in self._ds().locations()

    def test_normalize_telugu_location(self):
        assert self._ds().normalize_location("శ్రీశైలం") == "Srisailam"

    def test_availability_srisailam(self):
        ci, co = _dates()
        r = self._ds().check_availability(location="శ్రీశైలం", room_type="AC",
                                          check_in=ci, check_out=co)
        assert r.available and r.rooms_available >= 1

    def test_full_live_booking(self):
        ci, co = _dates()
        r = self._ds().create_booking(
            location="శ్రీశైలం", room_type="AC", guest_name="Ravi Kumar",
            phone="9876500011", check_in=ci, check_out=co, guests=2, num_rooms=1,
            gotram="Bharadwaja", email="ravi@example.com",
        )
        assert r.success and r.booking_id and r.booking_id.startswith("BK-")

    def test_gotram_rejected(self):
        ci, co = _dates()
        r = self._ds().create_booking(
            location="శ్రీశైలం", room_type="AC", guest_name="Test User",
            phone="9876500022", check_in=ci, check_out=co, guests=1, num_rooms=1,
            gotram="ZZZ-not-a-real-gotram", email="t@example.com",
        )
        assert not r.success and r.error == "gotram_rejected"
