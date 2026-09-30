# -*- coding: utf-8 -*-
"""Swappable LLM provider interface + the NLU result schema."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator

# The intents the dialogue manager understands (steering §6.1).
INTENTS = {
    "book_room", "check_availability", "cancel_booking", "booking_status",
    "ask_price", "ask_facilities", "talk_to_human", "goodbye", "unknown",
}


class NLUSlots(BaseModel):
    """Raw slot values as the LLM extracted them (strings; app resolves them)."""
    location: str | None = None
    check_in_date: str | None = None      # may be ISO or a Telugu phrase
    check_out_date: str | None = None
    nights: int | None = None
    num_guests: int | None = None
    room_type: str | None = None          # normalized later via aliases
    guest_name: str | None = None
    callback_number: str | None = None
    booking_id: str | None = None

    model_config = {"extra": "ignore"}


class NLUResult(BaseModel):
    intent: str = "unknown"
    slots: NLUSlots = Field(default_factory=NLUSlots)
    confidence: float = 0.0

    model_config = {"extra": "ignore"}

    @field_validator("intent")
    @classmethod
    def _known_intent(cls, v: str) -> str:
        return v if v in INTENTS else "unknown"


class LLMProvider(ABC):
    """Contract every LLM backend must satisfy."""

    @abstractmethod
    def warm_up(self) -> None:
        """Preload the model so the first real call isn't slow."""

    @abstractmethod
    def extract_nlu(self, user_text: str, context: dict) -> NLUResult:
        """Return intent + slots as a validated NLUResult (never raises)."""

    @abstractmethod
    def rephrase_te(self, facts: str) -> str | None:
        """Optional: produce a short polite Telugu sentence from given facts.
        Returns None if the output fails the Telugu-script guard."""
