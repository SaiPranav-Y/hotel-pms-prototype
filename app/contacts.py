"""
Contact Management — full customer profiles with call history and conversation records.
Each contact stores: name, phone, age, preferred locations, all call IDs, notes, tags.
"""

import logging
import time
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory store (synced to Firebase on writes)
_contacts: dict[str, dict] = {}  # keyed by phone number


def upsert_contact(
    phone: str,
    name: str = "",
    age: str = "",
    location: str = "",
    call_id: str = "",
    booking_id: str = "",
    notes: str = "",
    tags: list[str] = None,
) -> dict:
    """Create or update a contact. Auto-enriches from conversation data."""
    if not phone:
        return {}

    now = datetime.now().isoformat()

    if phone in _contacts:
        c = _contacts[phone]
        if name:
            c["name"] = name
        if age:
            c["age"] = age
        if location and location not in c["preferred_locations"]:
            c["preferred_locations"].append(location)
        if call_id and call_id not in c["call_history"]:
            c["call_history"].append(call_id)
        if booking_id and booking_id not in c["booking_history"]:
            c["booking_history"].append(booking_id)
        if notes:
            c["notes"].append({"text": notes, "date": now})
        if tags:
            c["tags"] = list(set(c["tags"] + tags))
        c["last_contact"] = now
        c["total_calls"] = len(c["call_history"])
        c["total_bookings"] = len(c["booking_history"])
    else:
        _contacts[phone] = {
            "phone": phone,
            "name": name or "Unknown",
            "age": age,
            "preferred_locations": [location] if location else [],
            "call_history": [call_id] if call_id else [],
            "booking_history": [booking_id] if booking_id else [],
            "notes": [{"text": notes, "date": now}] if notes else [],
            "tags": tags or [],
            "total_calls": 1 if call_id else 0,
            "total_bookings": 1 if booking_id else 0,
            "first_contact": now,
            "last_contact": now,
            "status": "active",  # active | inactive | vip
        }

    # Sync to Firebase
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("contacts").document(phone).set(_contacts[phone])
    except Exception as e:
        logger.error(f"Firebase contact sync error: {e}")

    return _contacts[phone]


def get_contact(phone: str) -> dict | None:
    """Get a contact by phone number."""
    return _contacts.get(phone)


def get_all_contacts() -> list[dict]:
    """Get all contacts sorted by last_contact desc."""
    contacts = list(_contacts.values())
    contacts.sort(key=lambda c: c.get("last_contact", ""), reverse=True)
    return contacts


def search_contacts(query: str) -> list[dict]:
    """Search contacts by name, phone, location, or tags."""
    query = query.lower()
    results = []
    for c in _contacts.values():
        if (query in c["name"].lower() or
            query in c["phone"] or
            any(query in loc.lower() for loc in c["preferred_locations"]) or
            any(query in tag.lower() for tag in c["tags"])):
            results.append(c)
    return results


def add_note(phone: str, note: str) -> bool:
    """Add a note to a contact."""
    if phone not in _contacts:
        return False
    _contacts[phone]["notes"].append({"text": note, "date": datetime.now().isoformat()})
    return True


def set_contact_status(phone: str, status: str) -> bool:
    """Set contact status: active, inactive, vip."""
    if phone not in _contacts:
        return False
    if status not in ("active", "inactive", "vip"):
        return False
    _contacts[phone]["status"] = status
    return True


def get_contact_count() -> int:
    return len(_contacts)
