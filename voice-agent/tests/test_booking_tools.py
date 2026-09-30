# -*- coding: utf-8 -*-
"""Availability + booking tools against a freshly-seeded temp DB."""

from datetime import timedelta

import pytest

from app.nlp_te import normalize as nz
from app.tools import availability as av
from app.tools import booking as bk

FULL_LOC = "Vruddasramam"  # smallest inventory in the Karivena data


def _dates():
    ci = nz.today() + timedelta(days=1)
    co = ci + timedelta(days=1)
    return ci, co


def _ac_capacity(loc=FULL_LOC):
    ci, co = _dates()
    offers = av.check_availability(loc, ci, co, 1, "AC")
    ac = next((o for o in offers if o.room_type == "AC"), None)
    return ac.rooms_available if ac else 0


def test_seed_has_rooms(seeded_db):
    assert FULL_LOC in seeded_db["locations"]
    assert _ac_capacity() >= 1


def test_no_double_booking(seeded_db):
    ci, co = _dates()
    cap = _ac_capacity()
    assert cap >= 1

    # Book every AC room.
    for i in range(cap):
        res = bk.create_booking(
            location=FULL_LOC, room_type="AC", guest_name=f"guest{i}",
            phone=f"+9190{i}", check_in=ci, check_out=co, guests=1, num_rooms=1,
        )
        assert res.success, f"booking {i} should succeed"

    # One more must be rejected.
    res = bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="overflow",
        phone="+91999", check_in=ci, check_out=co, guests=1, num_rooms=1,
    )
    assert not res.success
    assert res.error == "no_rooms"


def test_price_is_per_night_times_nights(seeded_db):
    ci = nz.today() + timedelta(days=1)
    co = ci + timedelta(days=2)  # 2 nights
    per_night = av.price_for(FULL_LOC, "AC")
    assert per_night and per_night > 0
    res = bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="రవి",
        phone="+91777", check_in=ci, check_out=co, guests=1, num_rooms=1,
    )
    assert res.success
    assert res.price_total == per_night * 2


def test_get_and_cancel(seeded_db):
    ci, co = _dates()
    res = bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="సీత",
        phone="+91555", check_in=ci, check_out=co, guests=1, num_rooms=1,
    )
    assert res.success
    bid = res.booking_id

    # Retrieve by id and by phone.
    assert bk.get_booking(booking_id=bid).id == bid
    assert bk.get_booking(phone="+91555").id == bid

    # Wrong phone must not cancel.
    assert not bk.cancel_booking(bid, phone="+90000")
    # Correct phone cancels.
    assert bk.cancel_booking(bid, phone="+91555")


def test_rebook_after_cancel(seeded_db):
    ci, co = _dates()
    cap = _ac_capacity()

    ids = []
    for i in range(cap):
        r = bk.create_booking(
            location=FULL_LOC, room_type="AC", guest_name=f"g{i}",
            phone=f"+9180{i}", check_in=ci, check_out=co, guests=1, num_rooms=1,
        )
        assert r.success
        ids.append(r.booking_id)

    # Full now.
    assert not bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="x",
        phone="+91x", check_in=ci, check_out=co, guests=1, num_rooms=1,
    ).success

    # Cancel one, then a new booking should fit.
    assert bk.cancel_booking(ids[0])
    assert bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="రీబుక్",
        phone="+91re", check_in=ci, check_out=co, guests=1, num_rooms=1,
    ).success


def test_non_overlapping_dates_are_free(seeded_db):
    cap = _ac_capacity()
    ci1 = nz.today() + timedelta(days=1)
    co1 = ci1 + timedelta(days=1)
    # Fill all rooms for night 1.
    for i in range(cap):
        assert bk.create_booking(
            location=FULL_LOC, room_type="AC", guest_name=f"n1_{i}",
            phone=f"+9170{i}", check_in=ci1, check_out=co1, guests=1, num_rooms=1,
        ).success

    # A later, non-overlapping range is still bookable.
    ci2 = nz.today() + timedelta(days=10)
    co2 = ci2 + timedelta(days=1)
    assert bk.create_booking(
        location=FULL_LOC, room_type="AC", guest_name="later",
        phone="+91later", check_in=ci2, check_out=co2, guests=1, num_rooms=1,
    ).success
