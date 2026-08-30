"""
Razorpay Payment Module — payment links for room bookings and donations.

Two flows:
  1. Room payment  — FIXED amount (from booking total)
  2. Donation      — FLEXIBLE amount, optionally linked to a Seva

Set your Razorpay keys in .env:
  RAZORPAY_KEY_ID=rzp_live_xxxxx  (or rzp_test_xxxxx)
  RAZORPAY_KEY_SECRET=xxxxx

If keys are not set, the module runs in MOCK mode (generates fake links so
the rest of the pipeline works end-to-end for demos).
"""

import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

_client = None
_mock_mode = True

# In-memory store of created payment links (also synced to Firebase)
_payment_links: dict[str, dict] = {}


# === SEVA OPTIONS (fixed-amount donation plans) ===
SEVA_OPTIONS = [
    {"id": "annadanam", "name": "Annadanam (Food Offering)", "amount": 1116, "description": "Sponsor a meal for pilgrims"},
    {"id": "nitya_pooja", "name": "Nitya Pooja", "amount": 516, "description": "Daily worship offering"},
    {"id": "deeparadhana", "name": "Deeparadhana", "amount": 251, "description": "Lamp offering"},
    {"id": "special_seva", "name": "Special Seva", "amount": 2116, "description": "Special occasion seva"},
    {"id": "gau_seva", "name": "Gau Seva", "amount": 1008, "description": "Cow protection service"},
    {"id": "vidya_danam", "name": "Vidya Danam", "amount": 5001, "description": "Support Vedic education"},
]


def init_razorpay():
    """Initialize Razorpay client if keys are present."""
    global _client, _mock_mode

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.info("Razorpay keys not set — running in MOCK mode (demo links)")
        _mock_mode = True
        return False

    try:
        import razorpay
        _client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        _mock_mode = False
        logger.info("Razorpay connected (LIVE mode)")
        return True
    except ImportError:
        logger.warning("razorpay package not installed — MOCK mode. Run: pip install razorpay")
        _mock_mode = True
        return False
    except Exception as e:
        logger.error(f"Razorpay init failed: {e} — MOCK mode")
        _mock_mode = True
        return False


def create_room_payment_link(
    booking_id: str,
    amount_inr: int,
    customer_name: str,
    customer_phone: str,
    description: str = "",
) -> dict:
    """
    Create a FIXED-amount payment link for a room booking.
    amount_inr: the room total in rupees.
    """
    desc = description or f"Room booking {booking_id} - Karivena Satram"
    ref_id = f"PAY-{booking_id}"

    if _mock_mode:
        link = _mock_link("room", ref_id, amount_inr)
    else:
        try:
            resp = _client.payment_link.create({
                "amount": amount_inr * 100,  # paise
                "currency": "INR",
                "accept_partial": False,
                "description": desc,
                "reference_id": ref_id,
                "customer": {"name": customer_name, "contact": customer_phone},
                "notify": {"sms": True, "whatsapp": True},
                "reminder_enable": True,
                "notes": {"type": "room_booking", "booking_id": booking_id},
            })
            link = resp.get("short_url", "")
        except Exception as e:
            logger.error(f"Razorpay room link failed: {e}")
            link = _mock_link("room", ref_id, amount_inr)

    record = {
        "payment_id": ref_id,
        "type": "room_booking",
        "booking_id": booking_id,
        "amount": amount_inr,
        "currency": "INR",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "link": link,
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }
    _payment_links[ref_id] = record
    _sync_payment(record)
    return record


def create_donation_link(
    customer_name: str,
    customer_phone: str,
    amount_inr: int = 0,
    seva_id: str = "",
) -> dict:
    """
    Create a donation payment link.
    - If seva_id given: FIXED amount from the seva plan.
    - If amount_inr given (no seva): fixed custom amount.
    - If neither: FLEXIBLE (accept_partial / any amount) link.
    """
    seva = None
    if seva_id:
        seva = next((s for s in SEVA_OPTIONS if s["id"] == seva_id), None)
        if seva:
            amount_inr = seva["amount"]

    ref_id = f"DON-{uuid.uuid4().hex[:8].upper()}"
    flexible = (amount_inr == 0)
    desc = f"Donation - {seva['name']}" if seva else "Donation to Karivena Satram"

    if _mock_mode:
        link = _mock_link("donation", ref_id, amount_inr)
    else:
        try:
            payload = {
                "amount": (amount_inr if amount_inr > 0 else 100) * 100,
                "currency": "INR",
                "accept_partial": flexible,
                "description": desc,
                "reference_id": ref_id,
                "customer": {"name": customer_name, "contact": customer_phone},
                "notify": {"sms": True, "whatsapp": True},
                "notes": {"type": "donation", "seva": seva_id or "general"},
            }
            if flexible:
                payload["first_min_partial_amount"] = 10000  # min 100 rupees
            resp = _client.payment_link.create(payload)
            link = resp.get("short_url", "")
        except Exception as e:
            logger.error(f"Razorpay donation link failed: {e}")
            link = _mock_link("donation", ref_id, amount_inr)

    record = {
        "payment_id": ref_id,
        "type": "donation",
        "seva_id": seva_id or None,
        "seva_name": seva["name"] if seva else None,
        "amount": amount_inr,
        "flexible": flexible,
        "currency": "INR",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "link": link,
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }
    _payment_links[ref_id] = record
    _sync_payment(record)
    return record


def get_seva_options() -> list[dict]:
    """Return available seva donation plans."""
    return SEVA_OPTIONS


def get_payment(payment_id: str) -> dict | None:
    return _payment_links.get(payment_id)


def get_all_payments() -> list[dict]:
    return sorted(_payment_links.values(), key=lambda p: p.get("created_at", ""), reverse=True)


def mark_paid(payment_id: str) -> bool:
    """Mark a payment as completed (called by webhook or manual)."""
    if payment_id in _payment_links:
        _payment_links[payment_id]["status"] = "paid"
        _payment_links[payment_id]["paid_at"] = datetime.now().isoformat()
        _sync_payment(_payment_links[payment_id])
        return True
    return False


def get_payment_stats() -> dict:
    total = len(_payment_links)
    paid = sum(1 for p in _payment_links.values() if p["status"] == "paid")
    room_revenue = sum(p["amount"] for p in _payment_links.values()
                       if p["type"] == "room_booking" and p["status"] == "paid")
    donation_total = sum(p["amount"] for p in _payment_links.values()
                         if p["type"] == "donation" and p["status"] == "paid")
    return {
        "total_links": total,
        "paid": paid,
        "pending": total - paid,
        "room_revenue": room_revenue,
        "donation_total": donation_total,
        "mode": "mock" if _mock_mode else "live",
    }


# === HELPERS ===

def _mock_link(kind: str, ref_id: str, amount: int) -> str:
    """Generate a fake but realistic-looking payment link for demos."""
    return f"https://rzp.io/i/MOCK-{kind}-{ref_id[-6:]}"


def _sync_payment(record: dict):
    """Persist payment record to Firebase."""
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("payments").document(record["payment_id"]).set(record)
    except Exception:
        pass


# Initialize on import
init_razorpay()
