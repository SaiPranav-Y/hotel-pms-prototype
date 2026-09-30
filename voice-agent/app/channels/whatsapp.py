# -*- coding: utf-8 -*-
"""
WhatsApp text channel — the SAME Telugu conversation as the voice agent.

A WhatsApp chat is just another transport for the shared `DialogueSession`: the
user types Telugu (or code-mixed) text, and we run it through the identical
state machine that powers the phone/voice flow — same greeting, same guided
questions, same gotram / email / phone collection in live mode, same Telugu
confirmation. Nothing about the booking logic is duplicated.

Key WhatsApp-specific behaviours:
  * One conversation per sender phone. The sender's number is used as the
    caller id, so in live mode we DON'T ask for the phone again (only gotram +
    email remain as extra questions).
  * A first message (or "hi"/"start"/"namaste"/"బుక్") starts a fresh booking
    and returns the greeting followed by the first question.
  * "cancel" / "reset" / "restart" (English or Telugu) starts over.
  * Finished conversations are cleared so the next message starts fresh.
  * Idle sessions expire after WA_SESSION_TTL_SECS so memory doesn't grow.

This module is transport-agnostic: `handle_incoming(phone, text) -> reply`.
The webhook server (run_whatsapp.py) feeds messages in and sends replies out.
"""

import logging
import time

from app import config
from app.dialogue.state_machine import DialogueSession
from app.dialogue import templates_te as T
from app.nlp_te import normalize as nz
from app.tools.datasource import get_data_source

logger = logging.getLogger(__name__)

# Session TTL (idle sessions are dropped after this many seconds).
WA_SESSION_TTL_SECS = int(getattr(config, "WA_SESSION_TTL_SECS", 1800))

# Fresh-start / reset trigger words (Telugu + English).
_START_WORDS = {"hi", "hello", "hey", "start", "menu", "namaste",
                "నమస్కారం", "నమస్తే", "బుక్", "start booking"}
_RESET_WORDS = {"cancel", "reset", "restart", "stop",
                "రద్దు", "మళ్ళీ", "ఆపు"}


class _Conversation:
    def __init__(self, session: DialogueSession):
        self.session = session
        self.last_seen = time.time()

    def touch(self):
        self.last_seen = time.time()


class WhatsAppChannel:
    """Holds per-sender conversations and drives them via DialogueSession."""

    def __init__(self, llm=None, data_source=None, lang=None):
        self.llm = llm
        # Language mode for new conversations: "ask" (default) shows the
        # bilingual picker first; "te"/"en" go straight to that language.
        self.lang = lang or config.LANG
        # Build one shared data source (sqlite or live) for all conversations.
        self.ds = data_source if data_source is not None else get_data_source()
        try:
            self._locations = self.ds.locations()
        except Exception:
            self._locations = []
        self._convos: dict[str, _Conversation] = {}

    # ---- public API ----
    def handle_incoming(self, phone: str, text: str) -> str:
        """Process one inbound WhatsApp message; return the Telugu reply."""
        phone = (phone or "").strip()
        text = (text or "").strip()
        if not phone:
            return T.NOT_UNDERSTOOD

        self._expire_idle()
        low = text.lower()

        # Explicit reset.
        if low in _RESET_WORDS or any(w in low for w in ("cancel", "reset", "restart")):
            self._start(phone)
            return self._greeting_plus_first(phone)

        convo = self._convos.get(phone)

        # First contact, no active convo, or a start word → greet + first question.
        if convo is None or low in _START_WORDS:
            self._start(phone)
            # If the very first message already carries intent/slots, feed it too,
            # unless it's just a greeting word.
            if low in _START_WORDS or not text:
                return self._greeting_plus_first(phone)
            greeting = self._convos[phone].session.greeting()
            reply = self._convos[phone].session.handle(text)
            self._maybe_finish(phone)
            return self._join(greeting, reply)

        # Ongoing conversation.
        convo.touch()
        reply = convo.session.handle(text)
        self._maybe_finish(phone)
        return reply

    def active_count(self) -> int:
        return len(self._convos)

    # ---- helpers ----
    def _start(self, phone: str):
        session = DialogueSession(
            llm=self.llm, caller_id=phone, locations=self._locations,
            data_source=self.ds,
            prefill_phone=True,  # sender's WhatsApp number is their contact
            lang=self.lang,
        )
        self._convos[phone] = _Conversation(session)

    def _greeting_plus_first(self, phone: str) -> str:
        """Greeting followed by the first concrete question (location).

        The voice greeting ends with a generic "what dates?" line, but the
        guided flow actually asks for the location first. On WhatsApp we want a
        single, unambiguous prompt, so we show the greeting and then the real
        first question (location) together.
        """
        convo = self._convos[phone]
        greeting = convo.session.greeting()
        # If we're still asking the caller to pick a language, just show the
        # picker — their next reply selects it and auto-advances to the first
        # question (handled by DialogueSession._choose_language).
        from app.dialogue.state_machine import ASK_LANGUAGE
        if convo.session.state == ASK_LANGUAGE:
            return greeting
        # Otherwise advance to the first booking question in one message.
        first_q = convo.session.handle("book")  # 'book' intent → asks location
        return self._join(greeting, first_q)

    def _maybe_finish(self, phone: str):
        convo = self._convos.get(phone)
        if convo and convo.session.finished:
            # Conversation done — drop it so the next message starts fresh.
            self._convos.pop(phone, None)

    def _expire_idle(self):
        now = time.time()
        stale = [p for p, c in self._convos.items()
                 if now - c.last_seen > WA_SESSION_TTL_SECS]
        for p in stale:
            self._convos.pop(p, None)

    @staticmethod
    def _join(*parts: str) -> str:
        return "\n\n".join(p for p in parts if p)


# Module-level default channel (lazy) so the webhook can share one instance.
_DEFAULT: WhatsAppChannel | None = None


def get_channel() -> WhatsAppChannel:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = WhatsAppChannel()
    return _DEFAULT


def handle_incoming(phone: str, text: str) -> str:
    """Convenience wrapper over the default channel."""
    return get_channel().handle_incoming(phone, text)
