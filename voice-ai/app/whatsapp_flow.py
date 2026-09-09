"""
WhatsApp Booking Conversation Flow.

A lightweight, stateful question-and-answer flow that collects the mandatory
booking details over WhatsApp, then creates the reservation. The sender's phone
number is used automatically (never asked).

Mandatory fields collected (in order):
  1. Name
  2. Gotram        (validated against approved list)
  3. Email         (Mail ID — validated)
  4. Location      (place they want to book)
  5. Room type     (AC / Non-AC — offered by availability)
  6. Stay span     (check-in + check-out)
  7. Number of rooms

Phone number is taken from the WhatsApp sender ("from") and NOT asked.

Usage:
  reply = handle_incoming("+919000000001", "Hi")       # starts the flow
  reply = handle_incoming("+919000000001", "Ravi")     # answers name, asks next
  ...
On completion it calls knowledge_base.create_booking and returns a confirmation
message plus the payment options (see build_payment_options_message).
"""

import re
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Per-phone conversation state: phone -> {"step": str, "data": {...}}
_sessions: dict[str, dict] = {}

# Ordered steps of the flow
_STEPS = ["name", "gotram", "email", "location", "room_type", "dates", "rooms", "confirm"]

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _reset(phone: str):
    _sessions[phone] = {"step": "name", "data": {"customer_phone": phone}}


def get_session(phone: str) -> dict | None:
    return _sessions.get(phone)


def handle_incoming(phone: str, text: str) -> str:
    """
    Process one inbound WhatsApp message from `phone` and return the reply text.
    Drives the booking Q&A. Phone is the sender's number (never asked).
    """
    text = (text or "").strip()
    low = text.lower()

    # (Re)start triggers
    if low in ("hi", "hello", "namaste", "start", "book", "booking", "menu") \
            or phone not in _sessions:
        _reset(phone)
        return (
            "🙏 Namaste! Welcome to Karivena Satram.\n"
            "I'll help you book your stay. May I know your *full name*?"
        )

    session = _sessions[phone]
    step = session["step"]
    data = session["data"]

    if low in ("cancel", "reset", "restart"):
        _reset(phone)
        return "No problem, let's start over. May I know your *full name*?"

    # --- NAME ---
    if step == "name":
        if len(text) < 2:
            return "Please share your full name to continue."
        data["customer_name"] = text
        session["step"] = "gotram"
        return f"Thank you, {text}. What is your *Gotram*? (required for community eligibility)"

    # --- GOTRAM ---
    if step == "gotram":
        from app.gotram import match_gotram
        matched = match_gotram(text)
        if not matched:
            return (
                f"Sorry, '{text}' is not in our approved gotram list. "
                "Karivena accommodation is reserved for our community. "
                "Please re-enter your gotram, or type 'cancel'."
            )
        data["gotram"] = matched
        session["step"] = "email"
        return f"Gotram {matched} confirmed. What is your *email (Mail ID)*? (for receipt & 80G certificate)"

    # --- EMAIL ---
    if step == "email":
        if not _EMAIL_RE.match(text):
            return "That doesn't look like a valid email. Please enter a valid Mail ID."
        data["customer_email"] = text
        session["step"] = "location"
        return "Which *place / location* would you like to stay at? (e.g. Srisailam, Tirupathi, Kasi)"

    # --- LOCATION ---
    if step == "location":
        from app.knowledge_base import get_all_locations
        locs = get_all_locations()
        key = text.lower().replace(" ", "_")
        match = None
        for k, v in locs.items():
            if key in k or k in key or text.lower() in v.get("name", "").lower():
                match = v.get("name", text)
                break
        if not match:
            available = ", ".join(sorted({v.get("name", k) for k, v in locs.items()
                                          if v.get("total_rooms", 0) > 0}))
            return f"We don't have that location. Available: {available}. Please pick one."
        data["location"] = match
        session["step"] = "room_type"
        return f"Great — {match}. Which *room type*: AC or Non-AC?"

    # --- ROOM TYPE ---
    if step == "room_type":
        rt = "Non-AC" if "non" in low else ("AC" if "ac" in low else "")
        if not rt:
            return "Please reply *AC* or *Non-AC*."
        data["room_type"] = rt
        session["step"] = "dates"
        return ("For how long? Share your *check-in and check-out dates* "
                "(e.g. 2026-07-01 to 2026-07-03), or say 'tomorrow for 2 nights'.")

    # --- DATES ---
    if step == "dates":
        from app.normalizer import normalize_query
        ex = normalize_query(text).get("extracted", {})
        ci, co = ex.get("check_in"), ex.get("check_out")
        if not ci:
            return ("I couldn't read those dates. Please share check-in and check-out, "
                    "e.g. '2026-07-01 to 2026-07-03'.")
        if not co:
            # default 1 night if only check-in given
            from datetime import timedelta
            co = (date.fromisoformat(ci) + timedelta(days=1)).isoformat()
        data["check_in"] = ci
        data["check_out"] = co
        session["step"] = "rooms"
        return f"Noted: {ci} to {co}. How many *rooms* do you need?"

    # --- ROOMS ---
    if step == "rooms":
        m = re.search(r"\d+", text)
        rooms = int(m.group()) if m else 1
        data["num_rooms"] = max(rooms, 1)

        # Check availability + price before confirming
        from app.knowledge_base import check_availability
        avail = check_availability(
            data["location"], data["room_type"],
            date.fromisoformat(data["check_in"]),
            date.fromisoformat(data["check_out"]),
            data["num_rooms"],
        )
        if not avail.get("available"):
            session["step"] = "room_type"
            return (f"Sorry, no {data['room_type']} rooms available for those dates at "
                    f"{data['location']}. Try a different room type (AC/Non-AC)?")
        data["_quote_total"] = avail.get("total_price", 0)
        session["step"] = "confirm"
        return (
            "Please confirm your booking:\n"
            f"• Name: {data['customer_name']}\n"
            f"• Gotram: {data['gotram']}\n"
            f"• Location: {data['location']}\n"
            f"• Room: {data['room_type']} x {data['num_rooms']}\n"
            f"• Stay: {data['check_in']} to {data['check_out']}\n"
            f"• Amount: ₹{avail.get('total_price', 0):,}\n\n"
            "Reply *YES* to confirm, or *cancel*."
        )

    # --- CONFIRM ---
    if step == "confirm":
        if low not in ("yes", "y", "confirm", "ok", "okay"):
            return "Reply *YES* to confirm the booking, or *cancel* to stop."
        from app.knowledge_base import create_booking
        result = create_booking(
            customer_name=data["customer_name"],
            customer_phone=data["customer_phone"],
            customer_email=data["customer_email"],
            location=data["location"],
            room_type=data["room_type"],
            check_in=date.fromisoformat(data["check_in"]),
            check_out=date.fromisoformat(data["check_out"]),
            num_rooms=data["num_rooms"],
            gotram=data["gotram"],
            send_whatsapp=False,  # we compose the reply here
        )
        _sessions.pop(phone, None)
        if not result.get("success"):
            return f"Booking could not be completed: {result.get('error', 'unknown error')}"
        return build_payment_options_message(result)

    # Fallback
    _reset(phone)
    return "Let's start again. May I know your *full name*?"


def build_payment_options_message(booking: dict) -> str:
    """Compose the confirmation + payment-options message after a booking."""
    bid = booking.get("booking_id", "")
    total = booking.get("total_price", 0)
    pay_link = booking.get("payment_link", "")
    don_link = booking.get("donation_link", "")

    lines = [
        "✅ Your reservation is confirmed!",
        f"Booking ID: {bid}",
        f"Amount: ₹{total:,}",
        "",
        "💳 *Choose a payment method:*",
        "You can pay online instantly via the secure UPI / card link below:",
        pay_link or "(payment link will be sent shortly)",
        "",
        "You may also pay by Cash, Card, UPI, or Cheque at the counter.",
        "",
        "🙏 *Support the Satram (optional):*",
        "Donate any amount or choose a seva — you'll receive an 80G certificate:",
        don_link or "",
        "",
        "Your *receipt* will be shared here once payment is confirmed"
        " (with the 80G certificate if you donate). Om Namah Shivaya 🕉️",
    ]
    return "\n".join(l for l in lines if l is not None)
