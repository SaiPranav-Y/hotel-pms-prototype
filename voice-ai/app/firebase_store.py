"""
Firebase Firestore Integration — stores and retrieves booking data.

Setup:
1. Go to Firebase Console → Project Settings → Service accounts
2. Click "Generate new private key" → save as firebase-key.json
3. Place firebase-key.json in the project root (hotel-voice-booking-demo/)
4. Set FIREBASE_ENABLED=true in .env

If Firebase is not configured, the app falls back to in-memory storage (default).
"""

import logging
import os
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv

# Load .env explicitly
load_dotenv()

logger = logging.getLogger(__name__)

# State
_db = None
_firebase_enabled = False

# Config — read AFTER dotenv loads
FIREBASE_KEY_PATH = os.getenv(
    "FIREBASE_KEY_PATH",
    str(Path(__file__).parent.parent / "firebase-key.json")
)
FIREBASE_ENABLED = os.getenv("FIREBASE_ENABLED", "false").lower() == "true"


def init_firebase():
    """Initialize Firebase connection. Call once at startup."""
    global _db, _firebase_enabled

    if not FIREBASE_ENABLED:
        logger.info("Firebase DISABLED (set FIREBASE_ENABLED=true in .env to enable)")
        return False

    if not os.path.exists(FIREBASE_KEY_PATH):
        logger.warning(
            f"Firebase key not found at: {FIREBASE_KEY_PATH}\n"
            "  → Download from: https://console.firebase.google.com/project/hotel-pms-prototype/settings/serviceaccounts/adminsdk\n"
            "  → Click 'Generate new private key'\n"
            "  → Save as firebase-key.json in the project root"
        )
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Check if already initialized
        try:
            firebase_admin.get_app()
        except ValueError:
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred, {
                "projectId": "hotel-pms-prototype",
            })

        _db = firestore.client()
        _firebase_enabled = True
        logger.info("Firebase connected! Project: hotel-pms-prototype")
        return True
    except Exception as e:
        logger.error(f"Firebase init failed: {e}")
        return False


def is_firebase_active() -> bool:
    """Check if Firebase is connected and active."""
    return _firebase_enabled and _db is not None


# =============================================================================
# WRITE OPERATIONS
# =============================================================================

def save_booking_to_firebase(booking: dict) -> bool:
    """
    Save a booking to Firestore /reservations collection.
    Uses the SAME schema as the Flutter PMS app so bookings appear in both.
    """
    if not is_firebase_active():
        return False

    try:
        # Map our booking fields to the Flutter PMS schema
        doc_data = {
            "customer_name": booking.get("customer_name", ""),
            "customer_phone": booking.get("customer_phone", ""),
            "customer_age": int(booking.get("customer_age", 0) or 0),
            "temple_name": booking.get("location", booking.get("temple", "")),
            "room_type": booking.get("room_type_name", booking.get("room_type", "")),
            "check_in": booking.get("check_in", ""),
            "check_out": booking.get("check_out", ""),
            "no_of_rooms": int(booking.get("num_rooms", 1)),
            "reservation_status": "CONFIRMED",
            "reservation_mode": "Voice Assistant",
            "created_at": datetime.now().isoformat(),
        }

        # Use booking_id as document ID if available, otherwise auto-generate
        doc_id = booking.get("booking_id", None)
        if doc_id:
            _db.collection("reservations").document(doc_id).set(doc_data)
        else:
            _db.collection("reservations").add(doc_data)

        logger.info(f"Firebase: Reservation saved (Voice Assistant) → {doc_id or 'auto-id'}")
        return True
    except Exception as e:
        logger.error(f"Firebase save booking error: {e}")
        return False


def update_booking_status_firebase(booking_id: str, status: str) -> bool:
    """Update a reservation's status in Firestore."""
    if not is_firebase_active():
        return False

    try:
        _db.collection("reservations").document(booking_id).update({
            "reservation_status": status.upper(),
            "updated_at": datetime.now().isoformat(),
        })
        logger.info(f"Firebase: Reservation {booking_id} → {status}")
        return True
    except Exception as e:
        logger.error(f"Firebase update error: {e}")
        return False


def save_call_record_firebase(call_data: dict) -> bool:
    """Save call transcript and metadata to Firestore /calls collection."""
    if not is_firebase_active():
        return False

    try:
        call_id = call_data.get("call_id", "")
        _db.collection("calls").document(call_id).set({
            **call_data,
            "saved_at": datetime.now().isoformat(),
        })
        logger.info(f"Firebase: Call {call_id} saved")
        return True
    except Exception as e:
        logger.error(f"Firebase save call error: {e}")
        return False


# =============================================================================
# READ OPERATIONS
# =============================================================================

def get_all_bookings_firebase() -> list[dict]:
    """Fetch all reservations from Firestore (same collection as Flutter app)."""
    if not is_firebase_active():
        return []

    try:
        docs = _db.collection("reservations").order_by(
            "created_at", direction="DESCENDING"
        ).limit(100).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Firebase fetch reservations error: {e}")
        return []


def get_booking_firebase(booking_id: str) -> dict | None:
    """Fetch a single booking from Firestore."""
    if not is_firebase_active():
        return None

    try:
        doc = _db.collection("bookings").document(booking_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Firebase get booking error: {e}")
        return None


def get_all_calls_firebase() -> list[dict]:
    """Fetch all call records from Firestore."""
    if not is_firebase_active():
        return []

    try:
        docs = _db.collection("calls").order_by(
            "saved_at", direction="DESCENDING"
        ).limit(50).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"Firebase fetch calls error: {e}")
        return []


def check_availability_firebase(room_type: str, check_in: str, check_out: str) -> int:
    """
    Check how many rooms of a type are booked for given dates (from Firebase).
    Returns the number of overlapping bookings.
    """
    if not is_firebase_active():
        return 0

    try:
        # Query bookings that overlap with requested dates
        bookings = _db.collection("bookings").where(
            "room_type", "==", room_type
        ).where(
            "status", "==", "confirmed"
        ).stream()

        overlap_count = 0
        for doc in bookings:
            b = doc.to_dict()
            b_in = b.get("check_in", "")
            b_out = b.get("check_out", "")
            # Check date overlap
            if b_in and b_out:
                if b_in < check_out and b_out > check_in:
                    overlap_count += 1

        return overlap_count
    except Exception as e:
        logger.error(f"Firebase availability check error: {e}")
        return 0
