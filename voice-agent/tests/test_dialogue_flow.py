# -*- coding: utf-8 -*-
"""
End-to-end dialogue tests (deterministic, no LLM).

Drives DialogueSession turn-by-turn exactly like the text REPL would, and
asserts that:
  * every agent line is Telugu (the non-negotiable output guard),
  * a full booking completes and yields a speakable booking number,
  * cancellation completes,
  * availability is correctly reported as full once inventory is exhausted.
"""

from datetime import timedelta

import pytest

from app.nlp_te import normalize as nz
from app.dialogue.state_machine import DialogueSession
from app.tools import availability as av
from app.tools import booking as bk

FULL_LOC = "Vruddasramam"


def _drive(session, turns):
    """Feed turns; assert every reply is Telugu; return the last reply."""
    last = None
    for u in turns:
        last = session.handle(u)
        assert nz.is_telugu(last), f"NON-TELUGU OUTPUT for {u!r}: {last!r}"
    return last


def test_greeting_is_telugu(seeded_db):
    s = DialogueSession(caller_id="+91", locations=seeded_db["locations"])
    assert nz.is_telugu(s.greeting())


def test_full_booking_completes(seeded_db):
    s = DialogueSession(caller_id="+919876543210", locations=seeded_db["locations"])
    assert nz.is_telugu(s.greeting())
    last = _drive(s, [
        "బుక్ చేయాలి",     # intent -> book
        "శ్రీశైలం",         # location
        "రేపు",            # check-in
        "రెండు రోజులు",     # nights
        "ఇద్దరు",           # guests (human-counting word)
        "ఏసీ",             # room type
        "రవి కుమార్",       # name
        "అవును",           # confirm
    ])
    assert s.finished
    assert "బుకింగ్ నంబర్" in last

    # The booking really exists in the DB for this caller.
    b = bk.get_booking(phone="+919876543210")
    assert b is not None
    assert b.location == "Srisailam"
    assert b.room_type == "AC"


def test_cancellation_completes(seeded_db):
    # First create a booking to cancel.
    s = DialogueSession(caller_id="+919876543210", locations=seeded_db["locations"])
    s.greeting()
    _drive(s, ["బుక్", "శ్రీశైలం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ", "రవి", "అవును"])
    b = bk.get_booking(phone="+919876543210")
    assert b is not None

    # Now cancel it.
    s2 = DialogueSession(caller_id="+919876543210", locations=seeded_db["locations"])
    s2.greeting()
    last = _drive(s2, ["నా బుకింగ్ రద్దు చేయాలి", b.id, "అవును"])
    assert s2.finished
    assert "రద్దు" in last


def test_availability_reports_full(seeded_db):
    locs = seeded_db["locations"]
    ci = nz.today() + timedelta(days=1)
    co = ci + timedelta(days=1)
    offers = av.check_availability(FULL_LOC, ci, co, 1, "AC")
    ac = next((o for o in offers if o.room_type == "AC"), None)
    cap = ac.rooms_available if ac else 0
    assert cap >= 1

    names = ["రవి", "సీత", "గోపి", "లక్ష్మి", "కృష్ణ", "రాధ"]
    for i in range(cap):
        sx = DialogueSession(caller_id=f"+9190{i}", locations=locs)
        sx.greeting()
        last = _drive(sx, [
            "బుక్", "వృద్ధాశ్రమం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ",
            names[i % len(names)], "అవును",
        ])
        assert sx.finished and "బుకింగ్ నంబర్" in last

    # The next caller for the same dates/type is told none are available.
    sc = DialogueSession(caller_id="+91999", locations=locs)
    sc.greeting()
    resp = _drive(sc, ["బుక్", "వృద్ధాశ్రమం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ", "మోహన్"])
    assert "అందుబాటులో లేవు" in resp


def test_transfer_to_human(seeded_db):
    s = DialogueSession(caller_id="+91", locations=seeded_db["locations"])
    s.greeting()
    last = s.handle("నాకు మనిషితో మాట్లాడాలి")
    assert nz.is_telugu(last)
    assert s.finished  # TRANSFER is a terminal state


def test_invalid_slot_reprompts_then_transfers(seeded_db):
    # Two consecutive unparseable answers on the same slot -> transfer.
    s = DialogueSession(caller_id="+91", locations=seeded_db["locations"])
    s.greeting()
    s.handle("బుక్")            # -> ASK_LOCATION
    r1 = s.handle("గోవా")       # unknown location -> retry 1
    assert nz.is_telugu(r1)
    r2 = s.handle("గోవా")       # unknown again -> transfer
    assert nz.is_telugu(r2)
    assert s.finished
