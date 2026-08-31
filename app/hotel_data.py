"""
Temple Accommodation Data — rooms at Srisailam, Tirupati, Shirdi.
Manages room types, availability, and bookings.
"""

from datetime import date, timedelta
from typing import Optional
import uuid


# --- Organization Info ---

HOTEL_INFO = {
    "name": "Temple Stay Accommodations",
    "tagline": "Comfortable stays near sacred temples",
    "address": "Srisailam, Tirupati & Shirdi locations",
    "phone": "+91-9133654248",
    "check_in_time": "12:00 PM",
    "check_out_time": "11:00 AM",
    "policies": {
        "cancellation": "Free cancellation up to 24 hours before check-in. After that, one night charge applies.",
        "pets": "Pets are not allowed in temple accommodation areas.",
        "extra_bed": "Extra bed available on request at select locations.",
        "children": "Children under 5 stay free. Ages 5-12 at half rate.",
    },
}


# --- Temple Locations ---

TEMPLES = {
    "srisailam": {
        "name": "Srisailam",
        "total_capacity": 35,
        "available_rooms": 24,
        "maintenance_rooms": 1,
    },
    "tirupati": {
        "name": "Tirupati",
        "total_capacity": 15,
        "available_rooms": 9,
        "maintenance_rooms": 0,
    },
    "shirdi": {
        "name": "Shirdi",
        "total_capacity": 20,
        "available_rooms": 14,
        "maintenance_rooms": 2,
    },
}


# --- Room Types ---

ROOM_TYPES = {
    "single_ac": {
        "name": "Single Cot with A/C",
        "description": "Air-conditioned room with a single cot, attached bathroom, and basic amenities.",
        "base_price": 1500,
        "max_occupancy": 2,
        "amenities": ["A/C", "Attached Bathroom", "Fan", "Drinking Water"],
    },
    "single_nonac": {
        "name": "Single Cot Non A/C",
        "description": "Non air-conditioned room with a single cot, fan, and attached bathroom.",
        "base_price": 800,
        "max_occupancy": 2,
        "amenities": ["Fan", "Attached Bathroom", "Drinking Water"],
    },
    "double_ac": {
        "name": "Double Cot with A/C",
        "description": "Air-conditioned room with a double cot, suitable for families. Attached bathroom.",
        "base_price": 2200,
        "max_occupancy": 4,
        "amenities": ["A/C", "Double Cot", "Attached Bathroom", "Fan", "Drinking Water"],
    },
    "double_nonac": {
        "name": "Double Cot Non A/C",
        "description": "Non air-conditioned room with a double cot, fan, and attached bathroom.",
        "base_price": 1200,
        "max_occupancy": 4,
        "amenities": ["Fan", "Double Cot", "Attached Bathroom", "Drinking Water"],
    },
}


# --- In-memory bookings store ---

bookings: dict[str, dict] = {}


# --- Availability tracking per temple per date ---
# Key: (temple, room_type, date) -> rooms booked
_booked_counts: dict[tuple[str, str, date], int] = {}


def _get_rooms_for_temple(temple: str) -> int:
    """Get total available rooms for a temple (excluding maintenance)."""
    t = TEMPLES.get(temple)
    if t:
        return t["available_rooms"]
    return 0


def _get_booked_count(temple: str, room_type: str, d: date) -> int:
    return _booked_counts.get((temple, room_type, d), 0)


def _increment_booked(temple: str, room_type: str, check_in: date, check_out: date, num_rooms: int = 1):
    current = check_in
    while current < check_out:
        key = (temple, room_type, current)
        _booked_counts[key] = _booked_counts.get(key, 0) + num_rooms
        current += timedelta(days=1)


def _decrement_booked(temple: str, room_type: str, check_in: date, check_out: date, num_rooms: int = 1):
    current = check_in
    while current < check_out:
        key = (temple, room_type, current)
        _booked_counts[key] = max(0, _booked_counts.get(key, 0) - num_rooms)
        current += timedelta(days=1)


def check_availability(
    room_type: str,
    check_in: date,
    check_out: date,
    num_guests: int = 1,
    temple: str = "srisailam",
    num_rooms: int = 1,
) -> dict:
    """Check if rooms are available at a temple for given dates."""
    temple = temple.lower()
    if temple not in TEMPLES:
        return {
            "available": False,
            "error": f"Unknown temple location '{temple}'. Available: {', '.join(TEMPLES.keys())}",
        }

    if room_type not in ROOM_TYPES:
        return {
            "available": False,
            "error": f"Unknown room type '{room_type}'. Available: {', '.join(ROOM_TYPES.keys())}",
        }

    room = ROOM_TYPES[room_type]
    temple_info = TEMPLES[temple]

    if check_in >= check_out:
        return {"available": False, "error": "Check-out date must be after check-in date."}

    if check_in < date.today():
        return {"available": False, "error": "Check-in date cannot be in the past."}

    # Check availability for each night
    total_available = temple_info["available_rooms"]
    min_available = total_available
    current = check_in
    while current < check_out:
        booked = _get_booked_count(temple, room_type, current)
        available = total_available - booked
        min_available = min(min_available, available)
        current += timedelta(days=1)

    num_nights = (check_out - check_in).days
    total_price = room["base_price"] * num_nights * num_rooms

    return {
        "available": min_available >= num_rooms,
        "rooms_available": min_available,
        "temple": temple_info["name"],
        "room_type": room["name"],
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_nights": num_nights,
        "price_per_night": room["base_price"],
        "total_price": total_price,
        "num_rooms": num_rooms,
        "currency": "INR",
        "max_occupancy": room["max_occupancy"],
    }


def get_pricing(room_type: str, check_in: date, check_out: date, addons: list[str] = None, num_rooms: int = 1) -> dict:
    """Get pricing details."""
    if room_type not in ROOM_TYPES:
        return {"error": f"Unknown room type. Available: {', '.join(ROOM_TYPES.keys())}"}

    room = ROOM_TYPES[room_type]
    num_nights = (check_out - check_in).days
    room_total = room["base_price"] * num_nights * num_rooms

    return {
        "room_type": room["name"],
        "price_per_night": room["base_price"],
        "num_nights": num_nights,
        "num_rooms": num_rooms,
        "grand_total": room_total,
        "currency": "INR",
    }


def create_booking(
    customer_name: str,
    customer_phone: str,
    room_type: str,
    check_in: date,
    check_out: date,
    num_guests: int = 1,
    addons: list[str] = None,
    customer_age: str = "",
    customer_city: str = "",
    temple: str = "srisailam",
    num_rooms: int = 1,
) -> dict:
    """Create a new booking."""
    temple = temple.lower()

    # Verify availability
    avail = check_availability(room_type, check_in, check_out, num_guests, temple, num_rooms)
    if not avail.get("available"):
        return {"success": False, "error": avail.get("error", "No rooms available for the selected dates.")}

    # Calculate pricing
    pricing = get_pricing(room_type, check_in, check_out, addons, num_rooms)

    # Generate booking ID
    booking_id = f"BK-{uuid.uuid4().hex[:8].upper()}"

    # Create booking record
    booking = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_age": customer_age,
        "customer_city": customer_city,
        "temple": TEMPLES.get(temple, {}).get("name", temple),
        "room_type": room_type,
        "room_type_name": ROOM_TYPES[room_type]["name"],
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_guests": num_guests,
        "num_rooms": num_rooms,
        "num_nights": (check_out - check_in).days,
        "addons": addons or [],
        "total_price": pricing["grand_total"],
        "currency": "INR",
        "status": "confirmed",
        "source": "voice_ai",
        "created_at": date.today().isoformat(),
    }

    # Store booking
    bookings[booking_id] = booking

    # Update availability
    _increment_booked(temple, room_type, check_in, check_out, num_rooms)

    # Save to Firebase (if enabled)
    try:
        from app.firebase_store import save_booking_to_firebase
        save_booking_to_firebase(booking)
    except Exception:
        pass

    return {
        "success": True,
        "booking_id": booking_id,
        "confirmation": f"Booking confirmed! Your booking ID is {booking_id}.",
        "details": booking,
    }


def get_booking_status(booking_id: str) -> dict:
    """Look up a booking by ID."""
    if booking_id in bookings:
        return {"found": True, "booking": bookings[booking_id]}
    return {"found": False, "error": f"No booking found with ID {booking_id}."}


def cancel_booking(booking_id: str) -> dict:
    """Cancel an existing booking."""
    if booking_id not in bookings:
        return {"success": False, "error": f"No booking found with ID {booking_id}."}

    booking = bookings[booking_id]
    if booking["status"] == "cancelled":
        return {"success": False, "error": "This booking is already cancelled."}

    # Release availability
    check_in = date.fromisoformat(booking["check_in"])
    check_out = date.fromisoformat(booking["check_out"])
    temple = booking.get("temple", "srisailam").lower()
    num_rooms = booking.get("num_rooms", 1)
    _decrement_booked(temple, booking["room_type"], check_in, check_out, num_rooms)

    # Update status
    booking["status"] = "cancelled"
    bookings[booking_id] = booking

    # Update Firebase (if enabled)
    try:
        from app.firebase_store import update_booking_status_firebase
        update_booking_status_firebase(booking_id, "cancelled")
    except Exception:
        pass

    return {
        "success": True,
        "message": f"Booking {booking_id} has been cancelled. {HOTEL_INFO['policies']['cancellation']}",
    }


def get_all_bookings() -> list[dict]:
    """Get all bookings."""
    return list(bookings.values())


def get_room_types_summary() -> str:
    """Formatted summary of room types."""
    lines = []
    for key, room in ROOM_TYPES.items():
        lines.append(
            f"- {room['name']}: {room['base_price']} rupees/night, max {room['max_occupancy']} persons"
        )
    return "\n".join(lines)


def get_temples_summary() -> str:
    """Formatted summary of temple locations."""
    lines = []
    for key, t in TEMPLES.items():
        lines.append(f"- {t['name']}: {t['available_rooms']} rooms available")
    return "\n".join(lines)


def get_addons_summary() -> str:
    """No addons for temple stays."""
    return "No add-ons currently available."
