# -*- coding: utf-8 -*-
"""
Booking tools — create / get / cancel, on SQLite.

- Booking IDs are short + speakable (4 digits) per steering §9.
- create_booking is TRANSACTIONAL: it re-checks availability inside the same
  transaction before writing, preventing double-booking under concurrent calls.
  SQLite serialises writes; we use BEGIN IMMEDIATE so the availability read and
  the insert are atomic against other writers.
"""

import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.db.models import Booking, get_session
from app.tools.availability import check_availability, price_for

logger = logging.getLogger(__name__)


@dataclass
class BookingResult:
    success: bool
    booking_id: str | None = None
    price_total: int = 0
    error: str | None = None       # machine code: "no_rooms" | "bad_input" | ...


def _new_speakable_id(session) -> str:
    """A unique 4-digit code (1000-9999) not already used by an active booking."""
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        exists = session.execute(
            select(Booking).where(Booking.id == code)
        ).scalars().first()
        if not exists:
            return code
    # Extremely unlikely fallback: widen to 5 digits.
    return str(random.randint(10000, 99999))


def create_booking(
    *,
    location: str,
    room_type: str,
    guest_name: str,
    phone: str,
    check_in: date,
    check_out: date,
    guests: int = 1,
    num_rooms: int = 1,
) -> BookingResult:
    """
    Create a confirmed booking after an atomic availability re-check.
    Returns BookingResult(success, booking_id, price_total, error).
    """
    if check_out <= check_in:
        return BookingResult(False, error="bad_dates")
    if num_rooms < 1:
        num_rooms = 1

    session = get_session()
    try:
        # BEGIN IMMEDIATE: take a write lock so the re-check + insert are atomic
        # against other bookers (prevents double-booking the last room).
        session.execute(select(Booking).limit(1))  # ensure connection open
        conn = session.connection()
        conn.exec_driver_sql("BEGIN IMMEDIATE")

        offers = check_availability(
            location, check_in, check_out, guests, room_type, session=session
        )
        offer = next((o for o in offers if o.room_type == room_type), None)
        if not offer or offer.rooms_available < num_rooms:
            conn.exec_driver_sql("ROLLBACK")
            return BookingResult(False, error="no_rooms")

        nights = (check_out - check_in).days
        price = (offer.price_per_night or 0) * nights * num_rooms

        code = _new_speakable_id(session)
        booking = Booking(
            id=code,
            location=location,
            room_type=room_type,
            guest_name=guest_name.strip(),
            phone=phone.strip(),
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            num_rooms=num_rooms,
            price_total=price,
            status="confirmed",
            created_at=datetime.now(timezone.utc),
        )
        session.add(booking)
        session.commit()  # releases the IMMEDIATE lock
        logger.info(f"Booking created: {code} {location}/{room_type} {check_in}->{check_out}")
        return BookingResult(True, booking_id=code, price_total=price)
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        logger.error(f"create_booking failed: {e}")
        return BookingResult(False, error="db_error")
    finally:
        session.close()


def get_booking(booking_id: str = "", phone: str = "") -> Booking | None:
    """Look up a booking by id, or the latest confirmed one by phone."""
    session = get_session()
    try:
        if booking_id:
            return session.execute(
                select(Booking).where(Booking.id == str(booking_id).strip())
            ).scalars().first()
        if phone:
            return session.execute(
                select(Booking)
                .where(Booking.phone == phone.strip(), Booking.status == "confirmed")
                .order_by(Booking.created_at.desc())
            ).scalars().first()
        return None
    finally:
        session.close()


def cancel_booking(booking_id: str, phone: str = "") -> bool:
    """
    Cancel a confirmed booking. If `phone` is given it MUST match the booking's
    phone (steering §9). Returns True on success.
    """
    session = get_session()
    try:
        b = session.execute(
            select(Booking).where(Booking.id == str(booking_id).strip())
        ).scalars().first()
        if not b or b.status != "confirmed":
            return False
        if phone and b.phone.strip() != phone.strip():
            return False
        b.status = "cancelled"
        session.commit()
        logger.info(f"Booking cancelled: {booking_id}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"cancel_booking failed: {e}")
        return False
    finally:
        session.close()
