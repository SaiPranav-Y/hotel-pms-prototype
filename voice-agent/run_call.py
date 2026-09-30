# -*- coding: utf-8 -*-
"""
Telephony driver (Phases 5-6) — connects a TelephonyAdapter to the shared
dialogue core. By default it uses the in-memory MockTelephony (no real phone),
which proves the call lifecycle wiring end to end without any SIP hardware.

    accept call → for each caller turn: (audio→)text → DialogueSession
                → Telugu reply → (TTS→)audio → send to caller
    → hang up when the dialogue finishes.

Swap in a real Asterisk/SIP adapter (see docs/TELEPHONY.md) without changing
the dialogue core. This file is the single place that ties channel I/O to the
agent, mirroring run_text.py / run_voice.py.

Run (mock demo):
    py run_call.py
"""

import logging

from app import config
from app.db.seed import seed, all_locations
from app.dialogue.state_machine import DialogueSession
from app.telephony.base import get_telephony, TelephonyAdapter

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("run_call")


def handle_call(adapter: TelephonyAdapter, call, locations, llm=None, tts=None,
                lang: str = "te"):
    """Run one full call through the shared dialogue core. Returns the transcript."""
    session = DialogueSession(llm=llm, caller_id=call.caller_id,
                              locations=locations, lang=lang)
    transcript: list[tuple[str, str]] = []

    def say(text: str):
        transcript.append(("agent", text))
        # If a TTS engine is provided, synthesize + stream it; else send text.
        if tts:
            path = tts.synthesize(text)
            adapter.send_audio(call, path if path else text)
        else:
            adapter.send_audio(call, text)

    say(session.greeting())
    while not session.finished:
        caller = adapter.receive_audio(call)  # text (mock) or transcribed audio
        if caller is None:
            break
        transcript.append(("caller", caller))
        say(session.handle(caller))

    adapter.hangup(call)
    return transcript


def main():
    seed(config.DB_PATH)
    locations = all_locations()

    # A scripted inbound call for the mock adapter (as if already transcribed).
    demo_turns = [
        "బుక్ చేయాలి", "శ్రీశైలం", "రేపు", "రెండు రోజులు",
        "ఇద్దరు", "ఏసీ", "రవి కుమార్", "అవును",
    ]
    adapter = get_telephony("mock", caller_id="+915550000000", turns=demo_turns)
    adapter.start()

    print("=" * 60)
    print(f"  {config.HOTEL_NAME} — Telugu Voice Agent (Telephony: mock)")
    print("=" * 60)

    call = adapter.wait_for_call()
    if not call:
        print("No call.")
        return
    print(f"[inbound call {call.call_id} from {call.caller_id}]\n")

    transcript = handle_call(adapter, call, locations)
    for who, line in transcript:
        tag = "Agent" if who == "agent" else "Caller"
        print(f"{tag}: {line}")
    adapter.stop()
    print("\n[call ended]")


if __name__ == "__main__":
    main()
