# -*- coding: utf-8 -*-
"""
Telephony seam tests — exercise the call lifecycle via MockTelephony, with the
real DialogueSession, against an isolated seeded DB. No SIP/hardware.
"""

import pytest

from app.nlp_te import normalize as nz
from app.telephony.base import get_telephony, MockTelephony, TelephonyAdapter
from app.tools import booking as bk
from run_call import handle_call


def test_factory_returns_mock():
    assert isinstance(get_telephony("mock"), MockTelephony)


def test_factory_unknown_raises():
    with pytest.raises(NotImplementedError):
        get_telephony("asterisk")


def test_call_lifecycle_order():
    turns = ["నమస్కారం", "వద్దు"]  # greeting then goodbye
    a = MockTelephony(caller_id="+91555", turns=turns)
    a.start()
    assert a.started
    call = a.wait_for_call()
    assert call is not None and call.caller_id == "+91555"
    # only one simulated call
    assert a.wait_for_call() is None
    a.hangup(call)
    assert a.hung_up


def test_full_booking_over_mock_telephony(seeded_db):
    turns = [
        "బుక్ చేయాలి", "శ్రీశైలం", "రేపు", "రెండు రోజులు",
        "ఇద్దరు", "ఏసీ", "రవి కుమార్", "అవును",
    ]
    a = get_telephony("mock", caller_id="+915551234567", turns=turns)
    a.start()
    call = a.wait_for_call()

    transcript = handle_call(a, call, seeded_db["locations"])

    # Every agent line must be Telugu.
    agent_lines = [line for who, line in transcript if who == "agent"]
    assert agent_lines
    for line in agent_lines:
        assert nz.is_telugu(line), f"non-Telugu agent line: {line!r}"

    # The last agent line confirms the booking; call hung up.
    assert "బుకింగ్ నంబర్" in agent_lines[-1]
    assert a.hung_up

    # The booking really exists for this caller id.
    b = bk.get_booking(phone="+915551234567")
    assert b is not None and b.location == "Srisailam" and b.room_type == "AC"


def test_send_audio_records_played(seeded_db):
    turns = ["వద్దు"]  # immediate goodbye
    a = MockTelephony(caller_id="+91999", turns=turns)
    a.start()
    call = a.wait_for_call()
    handle_call(a, call, seeded_db["locations"])
    # greeting + at least one reply were "played" to the caller
    assert len(a.played) >= 1
