# -*- coding: utf-8 -*-
"""
Data-source adapter: one booking/availability surface, two backends.

The Telugu dialogue never talks to a database directly — it talks to a
`DataSource`. This lets the SAME conversation run either:

  * `SqliteDataSource` — the self-contained offline SQLite tools (Phase 1). No
    external deps, no gotram/email required. Great for demos and tests.
  * `LiveDataSource` — the real Karivena `knowledge_base` from the sibling
    hotel-voice-booking-demo (Firestore-synced, gotram-gated, generates payment/
    WhatsApp links). Bookings show up in the Flutter PMS.

Both return the same small result shapes so the state machine is backend-blind:

  check_availability(...) -> AvailabilityResult(available, room_type, price_per_night, total_price, rooms_available, error)
  create_booking(...)     -> BookResult(success, booking_id, total_price, error)
  get_booking(...)        -> dict | None
  cancel_booking(...)     -> bool

Location/room strings are normalized to each backend's expected form inside the
adapter (the live backend wants canonical names like "Srisailam"; the demo's
own vernacular map handles Telugu/colloquial input).
"""

import logging
from dataclasses import dataclass
from datetime import date

from app import config

logger = logging.getLogger(__name__)


@dataclass
class AvailabilityResult:
    available: bool
    room_type: str = ""
    price_per_night: int = 0
    total_price: int = 0
    rooms_available: int = 0
    error: str | None = None


@dataclass
class BookResult:
    success: bool
    booking_id: str | None = None
    total_price: int = 0
    error: str | None = None           # machine code: no_rooms | gotram_rejected | ...
    payment_link: str = ""
    donation_link: str = ""


class DataSource:
    """Backend-agnostic booking surface used by the dialogue."""

    #: which mandatory slots this backend needs beyond the base booking slots.
    #: base = location, check_in, nights, num_guests, room_type, guest_name
    extra_required: tuple[str, ...] = ()

    def check_availability(self, *, location, room_type, check_in: date,
                           check_out: date, num_rooms=1, guests=1) -> AvailabilityResult:
        raise NotImplementedError

    def create_booking(self, *, location, room_type, guest_name, phone,
                        check_in: date, check_out: date, guests=1, num_rooms=1,
                        gotram="", email="") -> BookResult:
        raise NotImplementedError

    def get_booking(self, *, booking_id="", phone="") -> dict | None:
        raise NotImplementedError

    def cancel_booking(self, booking_id: str, phone: str = "") -> bool:
        raise NotImplementedError

    def locations(self) -> list[str]:
        """Canonical location names this backend knows about."""
        return []

    def normalize_location(self, text: str) -> str | None:
        """Map caller text (Telugu/colloquial/English) to a canonical location."""
        from app.dialogue import slots as S
        return S.normalize_location(text, self.locations())


# ── SQLite backend (offline, self-contained) ──────────────────────────────
class SqliteDataSource(DataSource):
    extra_required = ()  # name is enough; no gotram/email/phone required

    def check_availability(self, *, location, room_type, check_in, check_out,
                           num_rooms=1, guests=1) -> AvailabilityResult:
        from app.tools import availability as av
        offers = av.check_availability(location, check_in, check_out, guests, room_type)
        offer = next((o for o in offers if o.room_type == room_type), None)
        if not offer:
            return AvailabilityResult(available=False, error="no_rooms")
        nights = (check_out - check_in).days
        return AvailabilityResult(
            available=True,
            room_type=offer.room_type,
            price_per_night=offer.price_per_night,
            total_price=offer.price_per_night * nights * num_rooms,
            rooms_available=offer.rooms_available,
        )

    def create_booking(self, *, location, room_type, guest_name, phone,
                        check_in, check_out, guests=1, num_rooms=1,
                        gotram="", email="") -> BookResult:
        from app.tools import booking as bk
        res = bk.create_booking(
            location=location, room_type=room_type, guest_name=guest_name,
            phone=phone or "unknown", check_in=check_in, check_out=check_out,
            guests=guests, num_rooms=num_rooms,
        )
        return BookResult(success=res.success, booking_id=res.booking_id,
                          total_price=res.price_total, error=res.error)

    def get_booking(self, *, booking_id="", phone="") -> dict | None:
        from app.tools import booking as bk
        b = bk.get_booking(booking_id=booking_id, phone=phone)
        if not b:
            return None
        return {"booking_id": b.id, "location": b.location, "room_type": b.room_type,
                "status": b.status, "phone": b.phone}

    def cancel_booking(self, booking_id: str, phone: str = "") -> bool:
        from app.tools import booking as bk
        return bk.cancel_booking(booking_id, phone=phone)

    def locations(self) -> list[str]:
        from app.db.seed import all_locations
        try:
            return all_locations()
        except Exception:
            return []


# ── Live backend (Karivena knowledge_base, Firestore-synced) ───────────────
class LiveDataSource(DataSource):
    # The demo's create_booking rejects a booking without these.
    extra_required = ("phone", "gotram", "email")

    def __init__(self):
        from app.integration.karivena import bridge
        self._b = bridge()  # raises KarivenaUnavailable if the demo isn't present

    def _canon_location(self, location: str) -> str:
        """Map Telugu/colloquial location to the demo's canonical name."""
        try:
            with self._b.use_demo_app():
                canon = self._b.vernacular.normalize_location(location)
            if canon:
                return canon
        except Exception:
            pass
        return location

    def check_availability(self, *, location, room_type, check_in, check_out,
                           num_rooms=1, guests=1) -> AvailabilityResult:
        loc = self._canon_location(location)
        rt = "nonac" if "non" in (room_type or "").lower() else "ac"
        with self._b.use_demo_app():
            r = self._b.kb.check_availability(loc, rt, check_in, check_out, num_rooms)
        if not r.get("available"):
            return AvailabilityResult(available=False,
                                      error=r.get("error", "no_rooms"))
        return AvailabilityResult(
            available=True,
            room_type=r.get("room_type", room_type),
            price_per_night=int(r.get("price_per_night", 0) or 0),
            total_price=int(r.get("total_price", 0) or 0),
            rooms_available=int(r.get("rooms_available", 0) or 0),
        )

    def create_booking(self, *, location, room_type, guest_name, phone,
                        check_in, check_out, guests=1, num_rooms=1,
                        gotram="", email="") -> BookResult:
        loc = self._canon_location(location)
        rt = "nonac" if "non" in (room_type or "").lower() else "ac"
        with self._b.use_demo_app():
            r = self._b.kb.create_booking(
                customer_name=guest_name,
                customer_phone=phone,
                location=loc,
                room_type=rt,
                check_in=check_in,
                check_out=check_out,
                num_rooms=num_rooms,
                num_guests=guests,
                gotram=gotram,
                customer_email=email,
                send_whatsapp=True,
            )
        if r.get("success"):
            return BookResult(
                success=True,
                booking_id=r.get("booking_id"),
                total_price=int(r.get("total_price", 0) or 0),
                payment_link=r.get("payment_link", ""),
                donation_link=r.get("donation_link", ""),
            )
        # Map the demo's error shapes to our machine codes.
        if r.get("no_rooms"):
            return BookResult(success=False, error="no_rooms")
        if r.get("gotram_rejected"):
            return BookResult(success=False, error="gotram_rejected")
        if r.get("missing_fields"):
            return BookResult(success=False, error="missing_fields")
        return BookResult(success=False, error=r.get("error") or "error")

    def get_booking(self, *, booking_id="", phone="") -> dict | None:
        with self._b.use_demo_app():
            if booking_id:
                return self._b.kb.get_booking(booking_id)
            if phone:
                for b in reversed(self._b.kb.get_all_bookings()):
                    if b.get("customer_phone") == phone:
                        return b
        return None

    def cancel_booking(self, booking_id: str, phone: str = "") -> bool:
        with self._b.use_demo_app():
            r = self._b.kb.cancel_booking(booking_id)
        return bool(r.get("success"))

    def locations(self) -> list[str]:
        try:
            with self._b.use_demo_app():
                names = self._b.kb.get_location_names()
            # Only locations that actually have rooms.
            return [n for n in names] if names else []
        except Exception:
            return []

    def normalize_location(self, text: str) -> str | None:
        # Prefer the demo's rich Telugu/colloquial vernacular map; return None on
        # no match so the dialogue re-asks.
        if not text:
            return None
        try:
            with self._b.use_demo_app():
                canon = self._b.vernacular.normalize_location(text)
            return canon or None
        except Exception:
            return None


# ── Factory ────────────────────────────────────────────────────────────────
def get_data_source(kind: str | None = None) -> DataSource:
    """
    Return the configured DataSource. Falls back to SQLite if 'live' is asked
    for but the demo project can't be imported (so the agent still runs).
    """
    kind = (kind or config.DATA_SOURCE or "sqlite").lower()
    if kind == "live":
        try:
            ds = LiveDataSource()
            logger.info("Using LIVE Karivena data source (knowledge_base).")
            return ds
        except Exception as e:
            logger.warning(f"Live data source unavailable ({e}); using SQLite.")
            return SqliteDataSource()
    return SqliteDataSource()
