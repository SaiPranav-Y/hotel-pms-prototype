# -*- coding: utf-8 -*-
"""
Telephony adapter seam (Phases 5-6, steering §4/§12).

The dialogue core is transport-agnostic: it consumes caller text and produces
Telugu text. An audio front-end (Phase 4) turns speech <-> text. A *telephony*
front-end does the same but over a phone channel instead of a local mic.

This module defines the boundary so a real channel (Asterisk/SIP in dev, a
carrier/number provider later) can be dropped in WITHOUT touching the dialogue
core. Per the steering, no live SIP server or paid number is wired here — this
is the interface + a local MockTelephony you can drive from tests, plus config
templates and docs under docs/TELEPHONY.md.

A telephony adapter is responsible for exactly three things:
  1. accept an inbound call and hand us a `CallSession` (caller id, call id),
  2. stream caller audio in and agent audio out over the channel,
  3. hang up.

Everything else — STT, dialogue, TTS — is shared with the local voice loop.
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CallSession:
    """One phone call. `caller_id` becomes the booking's callback number."""
    call_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    caller_id: str = "unknown"
    metadata: dict = field(default_factory=dict)


class TelephonyAdapter(ABC):
    """
    Contract every phone-channel backend must satisfy. Implementations bridge
    the channel's audio to the shared STT -> DialogueSession -> TTS pipeline.
    """

    @abstractmethod
    def start(self) -> None:
        """Bind/register the channel and begin listening for inbound calls."""

    @abstractmethod
    def wait_for_call(self) -> CallSession | None:
        """Block until an inbound call arrives; return its session (None = shutdown)."""

    @abstractmethod
    def receive_audio(self, call: CallSession):
        """Yield/return the next chunk of caller audio for `call`."""

    @abstractmethod
    def send_audio(self, call: CallSession, audio_path) -> None:
        """Play an agent audio file to the caller on `call`."""

    @abstractmethod
    def hangup(self, call: CallSession) -> None:
        """End the call and release the channel."""

    def stop(self) -> None:
        """Optional: unregister/close the channel. Default no-op."""


class MockTelephony(TelephonyAdapter):
    """
    In-memory adapter for local testing — NO real phone/SIP involved.

    It simulates a single inbound call whose caller turns are supplied as a list
    of text strings (as if already transcribed). `send_audio` just records what
    would have been played. This lets us exercise the *call lifecycle* wiring in
    tests without any telephony hardware, exactly like the steering's dev path.
    """

    def __init__(self, caller_id: str = "+915550000000", turns: list[str] | None = None):
        self.caller_id = caller_id
        self._turns = list(turns or [])
        self._idx = 0
        self._call: CallSession | None = None
        self.played: list[str] = []   # audio paths (or text) we "sent"
        self.started = False
        self.hung_up = False

    def start(self) -> None:
        self.started = True
        logger.info("MockTelephony started (no real channel).")

    def wait_for_call(self) -> CallSession | None:
        if self._call is not None:
            return None  # only one simulated call
        self._call = CallSession(caller_id=self.caller_id)
        return self._call

    def receive_audio(self, call: CallSession):
        """Return the next caller 'utterance' as text, or None when exhausted."""
        if self._idx >= len(self._turns):
            return None
        text = self._turns[self._idx]
        self._idx += 1
        return text

    def send_audio(self, call: CallSession, audio_path) -> None:
        self.played.append(str(audio_path))

    def hangup(self, call: CallSession) -> None:
        self.hung_up = True
        logger.info(f"MockTelephony hangup {call.call_id}")

    def stop(self) -> None:
        self.started = False


def get_telephony(kind: str = "mock", **kwargs) -> TelephonyAdapter:
    """
    Factory. Only 'mock' is implemented in this repo (dev/testing).

    'asterisk' and 'sip' are documented seams (see docs/TELEPHONY.md): wire an
    ARI/AGI or SIP client here to bridge a real channel to the shared pipeline.
    """
    kind = (kind or "mock").lower()
    if kind == "mock":
        return MockTelephony(**kwargs)
    raise NotImplementedError(
        f"Telephony backend '{kind}' is not wired in this repo. It is a "
        f"documented adapter seam — see docs/TELEPHONY.md for the Asterisk/SIP "
        f"dev setup and where to implement TelephonyAdapter."
    )
