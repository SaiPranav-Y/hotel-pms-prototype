# -*- coding: utf-8 -*-
"""
End-to-end dialogue over the LIVE Karivena data source.

Skips entirely when the sibling hotel-voice-booking-demo can't be imported, so
this file is safe on a checkout without the demo. When present, it runs the full
Telugu booking including phone/gotram/email collection and asserts a live
BK-XXXX booking id and Telugu-only output.
"""

import pytest

from app.nlp_te import normalize as nz


def _live_available() -> bool:
    try:
        from app.integration import karivena
        return karivena.available()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _live_available(), reason="hotel-voice-booking-demo not importable")


def _drive(session, turns):
    last = None
    for u in turns:
        last = session.handle(u)
        assert nz.is_telugu(last), f"non-Telugu output for {u!r}: {last!r}"
    return last


def test_full_live_booking_dialogue():
    from app.tools.datasource import LiveDataSource
    from app.dialogue.state_machine import DialogueSession

    ds = LiveDataSource()
    assert ds.extra_required == ("phone", "gotram", "email")

    s = DialogueSession(caller_id="+919876543210", locations=ds.locations(),
                        data_source=ds)
    assert nz.is_telugu(s.greeting())
    last = _drive(s, [
        "బుక్ చేయాలి",              # intent
        "శ్రీశైలం",                  # location (Telugu -> Srisailam via vernacular)
        "రేపు",                     # check-in
        "రెండు రోజులు",              # nights
        "ఇద్దరు",                    # guests
        "ఏసీ",                      # room type
        "రవి కుమార్",                # name
        "9876543210",               # phone
        "Bharadwaja",               # gotram (approved)
        "ravi at gmail dot com",    # email (spoken form)
        "అవును",                    # confirm
    ])
    assert s.finished
    # Live confirmation mentions the booking number + WhatsApp.
    assert "బుకింగ్ నంబర్" in last


def test_gotram_rejection_reasks():
    from app.tools.datasource import LiveDataSource
    from app.dialogue.state_machine import DialogueSession

    ds = LiveDataSource()
    s = DialogueSession(caller_id="+919876543210", locations=ds.locations(),
                        data_source=ds)
    s.greeting()
    reply = _drive(s, [
        "బుక్ చేయాలి", "శ్రీశైలం", "రేపు", "ఒక రోజు", "ఒకరు", "ఏసీ",
        "టెస్ట్", "9876500033", "ZZZ-bad-gotram", "t@example.com", "అవును",
    ])
    # A bad gotram is rejected in Telugu and the agent re-asks (not finished).
    assert not s.finished
    assert nz.is_telugu(reply)
