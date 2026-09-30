# -*- coding: utf-8 -*-
"""
English spoken-output templates.

Mirror of templates_te.py with the SAME public names + function signatures, so
the dialogue state machine can swap between languages by swapping the module.
English confirmations use plain numbers and readable dates (no Telugu-word
conversion), so the dynamic functions ignore any pre-formatted "_words" strings
and format the raw values themselves where needed.
"""

from app import config

HOTEL = config.HOTEL_NAME  # "Karivena Satram"

# ── Static phrases ────────────────────────────────────────────────────────
GREETING = (
    f"Namaste! Welcome to {HOTEL}. "
    "I can help you book a room. "
    "Which place would you like to stay at?"
)

ASK_CHECKIN = "What date would you like to check in?"
ASK_NIGHTS = "How many nights will you stay?"
ASK_GUESTS = "How many guests will be staying?"
ASK_ROOM_TYPE = "Would you like an AC room or a Non-AC room?"
ASK_LOCATION = "Which place would you like to stay at?"
ASK_NAME = "May I have your name, please?"
ASK_PHONE = "Please share your 10-digit phone number."
# Live-booking-only slots (Karivena requires gotram + email + phone).
ASK_GOTRAM = "Please tell me your Gotram."
ASK_EMAIL = "Please share your email address."
GOTRAM_REJECTED = (
    "Sorry, the gotram you gave is not in our approved list. "
    "Could you please tell me your gotram again?"
)

NOT_UNDERSTOOD = "Sorry, I didn't quite catch that. Could you please say it again?"
PLEASE_HOLD = "One moment, I'm checking the details."
NOT_AVAILABLE = "Sorry, no rooms are available for those dates. Shall I try other dates?"
CONFIRM_PROMPT = "Is that correct? Shall I book it?"
TRANSFER = "One moment, I'm connecting you to our staff."
GOODBYE = "Thank you! Have a pleasant day."
CANCELLED = "Your booking has been cancelled."
CANCEL_NOT_FOUND = "Sorry, I couldn't find a booking with that number."
ASK_BOOKING_NUMBER = "Please tell me your booking number."
YES_NO_RETRY = "Please reply 'yes' or 'no'."

# Room-type words (for read-back). Kept identical to canonical values.
ROOM_TYPE_TE = {"AC": "AC", "Non-AC": "Non-AC"}


# ── Dynamic phrases ───────────────────────────────────────────────────────
def available(location_te: str, room_type: str, price_words: str) -> str:
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return (f"An {rt} room is available at {location_te}. "
            f"It is {price_words} rupees per night.")


def confirm_summary(location_te: str, room_type: str, checkin_words: str,
                    nights_words: str, guests_words: str, price_words: str) -> str:
    """Read the whole booking back before committing (English)."""
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return (
        f"{rt} room at {location_te}, from {checkin_words} for {nights_words}, "
        f"{guests_words} guests, total {price_words} rupees. "
        "Is that correct? Shall I book it?"
    )


def booking_done(booking_id_words: str) -> str:
    return (f"Your booking is confirmed. "
            f"Your booking number is {booking_id_words}. Thank you!")


def read_back_name(name: str) -> str:
    return f"Your name is {name}, is that correct?"


def booking_done_live(booking_id: str) -> str:
    return (
        "Your booking is confirmed. "
        f"Your booking number is {booking_id}. "
        "The payment link and details have been sent to your WhatsApp. "
        "Thank you!"
    )


def read_back_phone(phone_words: str) -> str:
    return f"Your phone number is {phone_words}, is that correct?"


def status_found(location_te: str, checkin_words: str, status_te: str) -> str:
    return f"Your booking at {location_te} on {checkin_words} is {status_te}."


def price_answer(location_te: str, room_type: str, price_words: str) -> str:
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return f"An {rt} room at {location_te} is {price_words} rupees per night."


# Booking status words
STATUS_TE = {
    "confirmed": "confirmed",
    "cancelled": "cancelled",
}
