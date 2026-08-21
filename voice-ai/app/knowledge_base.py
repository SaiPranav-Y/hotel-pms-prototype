"""
Knowledge Base — Karivena Satram room inventory across 10 pilgrimage locations.
Loaded from parsed Excel data. Provides availability checks and room info.

Organization: Akhila Bharatheeya Brahmana Karivena Nityannadana Satram
Purpose: Pilgrim accommodation at temple locations across India
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

# Load room data from parsed JSON
_DATA_PATH = Path(__file__).parent / "room_data.json"
_room_data: dict = {}
_bookings: dict[str, dict] = {}
_customers: dict[str, dict] = {}
_call_logs: dict[str, dict] = {}

# Availability tracking: (location, room_type, date) -> count booked
_booked: dict[tuple[str, str, date], int] = {}


def load_knowledge_base():
    """Load room data from JSON file."""
    global _room_data
    try:
        with open(str(_DATA_PATH), "r") as f:
            _room_data = json.load(f)
        total = sum(loc["total_rooms"] for loc in _room_data.values())
        logger.info(f"Knowledge base loaded: {len(_room_data)} locations, {total} rooms")
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        _room_data = {}


# === ORGANIZATION INFO ===

ORG_INFO = {
    "name": "Karivena Satram",
    "full_name": "Akhila Bharatheeya Brahmana Karivena Nityannadana Satram",
    "purpose": "Pilgrim accommodation at sacred temple locations",
    "check_in_time": "12:00 PM",
    "check_out_time": "11:00 AM",
    "contact": "+91-9133654248",
    "policies": {
        "cancellation": "Free cancellation up to 24 hours before check-in.",
        "children": "Children under 5 stay free.",
        "pets": "Pets are not allowed.",
        "id_required": "Valid government ID required at check-in.",
    },
}


# === LOCATION QUERIES ===

def get_all_locations() -> dict:
    """Get all location data."""
    return _room_data


def get_location_names() -> list[str]:
    """Get list of all location names."""
    return [loc["name"] for loc in _room_data.values()]


def get_location_info(location: str) -> dict | None:
    """Get info for a specific location."""
    key = location.lower().replace(" ", "_")
    return _room_data.get(key)


def get_locations_summary() -> str:
    """Human-readable summary for the AI prompt."""
    lines = []
    for key, loc in _room_data.items():
        if loc["total_rooms"] == 0:
            continue
        ac_price = loc["prices_ac"][0] if loc["prices_ac"] else "free"
        nonac_price = loc["prices_nonac"][0] if loc["prices_nonac"] else "free"
        lines.append(
            f"- {loc['name']}: {loc['total_rooms']} rooms "
            f"(AC: {loc['ac_rooms']}, Non-AC: {loc['nonac_rooms']}). "
            f"AC from INR {ac_price}, Non-AC from INR {nonac_price}"
        )
    return "\n".join(lines)


# === AVAILABILITY ===

def check_availability(
    location: str,
    room_type: str = "ac",
    check_in: date = None,
    check_out: date = None,
    num_rooms: int = 1,
) -> dict:
    """Check room availability at a location."""
    key = location.lower().replace(" ", "_")
    loc = _room_data.get(key)

    if not loc:
        available_locs = [l["name"] for l in _room_data.values() if l["total_rooms"] > 0]
        return {"available": False, "error": f"Unknown location. Available: {', '.join(available_locs)}"}

    if not check_in:
        check_in = date.today()
    if not check_out:
        check_out = check_in + timedelta(days=1)

    if check_in >= check_out:
        return {"available": False, "error": "Check-out must be after check-in."}

    # Determine total rooms of this type
    rt = room_type.lower().replace(" ", "").replace("-", "")
    if "non" in rt:
        total_of_type = loc["nonac_rooms"]
        prices = loc["prices_nonac"]
        type_name = "Non-AC"
    else:
        total_of_type = loc["ac_rooms"]
        prices = loc["prices_ac"]
        type_name = "AC"

    if total_of_type == 0:
        return {"available": False, "error": f"No {type_name} rooms at {loc['name']}."}

    # Check booked count for each night
    min_available = total_of_type
    current = check_in
    while current < check_out:
        booked = _booked.get((key, rt, current), 0)
        avail = total_of_type - booked
        min_available = min(min_available, avail)
        current += timedelta(days=1)

    num_nights = (check_out - check_in).days
    price_per_night = prices[0] if prices else 0
    total_price = price_per_night * num_nights * num_rooms

    return {
        "available": min_available >= num_rooms,
        "rooms_available": min_available,
        "location": loc["name"],
        "room_type": type_name,
        "num_rooms": num_rooms,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_nights": num_nights,
        "price_per_night": price_per_night,
        "total_price": total_price,
        "currency": "INR",
    }


# === BOOKING ===

def create_booking(
    customer_name: str,
    customer_phone: str,
    location: str,
    room_type: str = "ac",
    check_in: date = None,
    check_out: date = None,
    num_rooms: int = 1,
    num_guests: int = 1,
    customer_age: str = "",
) -> dict:
    """Create a new booking."""
    if not check_in:
        check_in = date.today()
    if not check_out:
        check_out = check_in + timedelta(days=1)

    # Check availability
    avail = check_availability(location, room_type, check_in, check_out, num_rooms)
    if not avail.get("available"):
        return {"success": False, "error": avail.get("error", "No rooms available.")}

    booking_id = f"BK-{uuid.uuid4().hex[:8].upper()}"
    key = location.lower().replace(" ", "_")
    loc = _room_data.get(key, {})
    rt = room_type.lower().replace(" ", "").replace("-", "")

    booking = {
        "booking_id": booking_id,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_age": customer_age,
        "location": loc.get("name", location),
        "room_type": "AC" if "non" not in rt else "Non-AC",
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_rooms": num_rooms,
        "num_guests": num_guests,
        "num_nights": (check_out - check_in).days,
        "price_per_night": avail["price_per_night"],
        "total_price": avail["total_price"],
        "currency": "INR",
        "status": "confirmed",
        "workflow_status": "pending",
        "source": "voice_ai",
        "created_at": date.today().isoformat(),
    }

    # Store
    _bookings[booking_id] = booking

    # Update availability
    current = check_in
    while current < check_out:
        bkey = (key, rt, current)
        _booked[bkey] = _booked.get(bkey, 0) + num_rooms
        current += timedelta(days=1)

    # Update/create customer profile
    _enrich_customer(customer_name, customer_phone, customer_age, location, booking_id)

    # Firebase sync
    try:
        from app.firebase_store import save_booking_to_firebase
        save_booking_to_firebase(booking)
    except Exception:
        pass

    return {
        "success": True,
        "booking_id": booking_id,
        "confirmation": f"Booking confirmed. ID: {booking_id}",
        "details": booking,
    }


def cancel_booking(booking_id: str) -> dict:
    """Cancel a booking."""
    if booking_id not in _bookings:
        return {"success": False, "error": f"Booking {booking_id} not found."}

    booking = _bookings[booking_id]
    if booking["status"] == "cancelled":
        return {"success": False, "error": "Already cancelled."}

    # Release rooms
    key = booking["location"].lower().replace(" ", "_")
    rt = "nonac" if "non" in booking["room_type"].lower() else "ac"
    check_in = date.fromisoformat(booking["check_in"])
    check_out = date.fromisoformat(booking["check_out"])
    num_rooms = booking.get("num_rooms", 1)

    current = check_in
    while current < check_out:
        bkey = (key, rt, current)
        _booked[bkey] = max(0, _booked.get(bkey, 0) - num_rooms)
        current += timedelta(days=1)

    booking["status"] = "cancelled"
    _bookings[booking_id] = booking

    try:
        from app.firebase_store import update_booking_status_firebase
        update_booking_status_firebase(booking_id, "cancelled")
    except Exception:
        pass

    return {"success": True, "message": f"Booking {booking_id} cancelled."}


def get_booking(booking_id: str) -> dict | None:
    return _bookings.get(booking_id)


def get_all_bookings() -> list[dict]:
    return list(_bookings.values())


# === CUSTOMER PROFILES ===

def _enrich_customer(name: str, phone: str, age: str, location: str, booking_id: str):
    """Create or update customer profile from conversation data."""
    if not phone:
        return

    if phone in _customers:
        # Update existing
        cust = _customers[phone]
        cust["name"] = name or cust["name"]
        cust["age"] = age or cust["age"]
        cust["booking_history"].append(booking_id)
        cust["preferred_locations"].add(location)
        cust["total_bookings"] += 1
    else:
        # New customer
        _customers[phone] = {
            "name": name,
            "phone": phone,
            "age": age,
            "preferred_locations": {location},
            "booking_history": [booking_id],
            "total_bookings": 1,
            "first_contact": date.today().isoformat(),
            "last_contact": date.today().isoformat(),
        }

    _customers[phone]["last_contact"] = date.today().isoformat()


def get_customer(phone: str) -> dict | None:
    """Get customer profile by phone number."""
    cust = _customers.get(phone)
    if cust:
        # Convert set to list for serialization
        return {**cust, "preferred_locations": list(cust["preferred_locations"])}
    return None


def get_all_customers() -> list[dict]:
    """Get all customer profiles."""
    return [
        {**c, "preferred_locations": list(c["preferred_locations"])}
        for c in _customers.values()
    ]


# === CALL WORKFLOW ===

WORKFLOW_STATUSES = ["pending", "needs_review", "completed"]


def create_call_log(
    call_id: str,
    duration: float = 0,
    transcript: list = None,
    gathered_info: dict = None,
    status: str = "pending",
) -> dict:
    """Create a call log entry with workflow status."""
    from datetime import datetime

    log = {
        "call_id": call_id,
        "date": date.today().isoformat(),
        "time": datetime.now().strftime("%H:%M:%S"),
        "duration_seconds": round(duration),
        "transcript": transcript or [],
        "gathered_info": gathered_info or {},
        "workflow_status": status,  # pending | needs_review | completed
        "has_booking": False,
        "booking_id": None,
        "customer_phone": gathered_info.get("customer_phone", "") if gathered_info else "",
        "created_at": datetime.now().isoformat(),
    }
    _call_logs[call_id] = log

    # Firebase sync
    try:
        from app.firebase_store import save_call_record_firebase
        save_call_record_firebase(log)
    except Exception:
        pass

    return log


def update_call_workflow(call_id: str, new_status: str) -> bool:
    """Update workflow status of a call."""
    if call_id not in _call_logs:
        return False
    if new_status not in WORKFLOW_STATUSES:
        return False
    _call_logs[call_id]["workflow_status"] = new_status
    return True


def get_call_log(call_id: str) -> dict | None:
    return _call_logs.get(call_id)


def get_all_call_logs() -> list[dict]:
    return list(_call_logs.values())


def get_calls_by_status(status: str) -> list[dict]:
    return [c for c in _call_logs.values() if c["workflow_status"] == status]


# === INIT ===

load_knowledge_base()
