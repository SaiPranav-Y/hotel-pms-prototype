# -*- coding: utf-8 -*-
"""
Booking slots + alias normalization (handles Telugu / English / code-mixed input).
"""

from dataclasses import dataclass, field
from datetime import date

from app.nlp_te import normalize as nz

# Room-type aliases → canonical value.
_ROOM_TYPE_ALIASES = {
    "ac": "AC", "ఏసీ": "AC", "ఎసి": "AC", "ఏసి": "AC", "a c": "AC",
    "airconditioned": "AC", "air conditioned": "AC", "ఏర్ కండిషన్": "AC",
    "nonac": "Non-AC", "non ac": "Non-AC", "non-ac": "Non-AC",
    "నాన్ ఏసీ": "Non-AC", "నాన్-ఏసీ": "Non-AC", "నాన్ ఎసి": "Non-AC",
    "నాన్ ఏర్ కండిషన్": "Non-AC", "without ac": "Non-AC",
}

# Location display name in Telugu (for spoken output). Latin proper nouns are
# kept where a common Telugu spelling isn't confidently known → flag for review.
LOCATION_TE = {
    "Srisailam": "శ్రీశైలం",
    "Kasi": "కాశీ",
    "Tirupathi": "తిరుపతి",
    "Shiridi": "షిర్డీ",
    "Mahanandi": "మహానంది",
    "Rameswaram": "రామేశ్వరం",
    "Brundavanam": "బృందావనం",
    "Naimisaranyam": "నైమిశారణ్యం",
    "Vruddasramam": "వృద్ధాశ్రమం",
    "Arunachalam": "అరుణాచలం",
}


def normalize_room_type(text: str) -> str | None:
    if not text:
        return None
    t = nz.nfc(text).strip().lower()
    # Check the most specific aliases first. "నాన్-ఏసీ" contains "ఏసీ", so if we
    # matched AC aliases first we'd wrongly classify Non-AC input as AC. Sorting
    # by descending alias length guarantees the longer, more specific alias wins.
    for alias, canonical in sorted(_ROOM_TYPE_ALIASES.items(),
                                   key=lambda kv: len(kv[0]), reverse=True):
        if alias in t:
            return canonical
    return None


def normalize_location(text: str, known_locations: list[str]) -> str | None:
    """Match caller text to a known location (English or Telugu spelling)."""
    if not text:
        return None
    t = nz.nfc(text).strip().lower()
    # direct English name substring
    for loc in known_locations:
        if loc.lower() in t:
            return loc
    # Telugu spelling substring
    for loc, loc_te in LOCATION_TE.items():
        if loc in known_locations and loc_te in text:
            return loc
    return None


def location_te(loc: str) -> str:
    return LOCATION_TE.get(loc, loc)


@dataclass
class BookingSlots:
    check_in_date: date | None = None
    check_out_date: date | None = None
    nights: int | None = None
    num_guests: int | None = None
    room_type: str | None = None
    location: str | None = None
    guest_name: str | None = None
    callback_number: str | None = None
    # Live-booking-only fields (Karivena knowledge_base requires these).
    gotram: str | None = None
    email: str | None = None

    def missing_for_booking(self, extra_required: tuple[str, ...] = ()) -> list[str]:
        """
        Which mandatory slots are still empty, in ask order.

        `extra_required` names additional fields the active data source needs
        (the live Karivena backend requires phone + gotram + email). Passing an
        empty tuple keeps the offline SQLite flow exactly as before.
        """
        need = []
        if not self.location:
            need.append("location")
        if not self.check_in_date:
            need.append("check_in_date")
        if not (self.check_out_date or self.nights):
            need.append("nights")
        if not self.num_guests:
            need.append("num_guests")
        if not self.room_type:
            need.append("room_type")
        if not self.guest_name:
            need.append("guest_name")
        # Extra live-mode slots, asked after the core ones.
        if "phone" in extra_required and not self.callback_number:
            need.append("phone")
        if "gotram" in extra_required and not self.gotram:
            need.append("gotram")
        if "email" in extra_required and not self.email:
            need.append("email")
        return need

    def resolved_checkout(self) -> date | None:
        if self.check_out_date:
            return self.check_out_date
        if self.check_in_date and self.nights:
            from datetime import timedelta
            return self.check_in_date + timedelta(days=self.nights)
        return None

    def merge(self, other: dict):
        """Merge newly-extracted values (only fill empty slots / update given)."""
        for k, v in (other or {}).items():
            if v is not None and hasattr(self, k):
                setattr(self, k, v)
