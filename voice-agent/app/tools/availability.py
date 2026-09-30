# -*- coding: utf-8 -*-
"""
Availability tool — the single source of truth for whether a room can be booked.

Availability = the room-type's capacity at a location MINUS the count of
overlapping confirmed bookings for that (location, room_type) over the requested
date range. Never invented by the LLM (steering §4/§9).
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from app.db.models import Room, Booking, get_session


@dataclass
class RoomOffer:
    location: str
    room_type: str
    price_per_night: int
    rooms_available: int
    capacity: int


def _overlaps(b_in: date, b_out: date, q_in: date, q_out: date) -> bool:
    """Half-open overlap: [b_in, b_out) intersects [q_in, q_out)."""
    return b_in < q_out and q_in < b_out


def check_availability(
    location: str,
    check_in: date,
    check_out: date,
    guests: int = 1,
    room_type: str | None = None,
    session=None,
) -> list[RoomOffer]:
    """
    Return the room offers available at `location` for the date range.
    If `room_type` is given, restrict to it. Empty list = nothing available.
    """
    own = session is None
    session = session or get_session()
    try:
        q = select(Room).where(Room.location == location, Room.active == True)  # noqa: E712
        if room_type:
            q = q.where(Room.type == room_type)
        rooms = session.execute(q).scalars().all()
        if not rooms:
            return []

        # Count overlapping confirmed bookings per room_type at this location.
        bq = select(Booking).where(
            Booking.location == location,
            Booking.status == "confirmed",
        )
        bookings = session.execute(bq).scalars().all()

        offers: list[RoomOffer] = []
        for room in rooms:
            booked = sum(
                b.num_rooms
                for b in bookings
                if b.room_type == room.type
                and _overlaps(b.check_in, b.check_out, check_in, check_out)
            )
            avail = max(room.capacity - booked, 0)
            if avail > 0:
                offers.append(RoomOffer(
                    location=room.location,
                    room_type=room.type,
                    price_per_night=room.price_per_night,
                    rooms_available=avail,
                    capacity=room.capacity,
                ))
        return offers
    finally:
        if own:
            session.close()


def price_for(location: str, room_type: str, session=None) -> int | None:
    """Per-night price for a location + room type (None if not found)."""
    own = session is None
    session = session or get_session()
    try:
        room = session.execute(
            select(Room).where(
                Room.location == location, Room.type == room_type, Room.active == True  # noqa: E712
            )
        ).scalars().first()
        return room.price_per_night if room else None
    finally:
        if own:
            session.close()
