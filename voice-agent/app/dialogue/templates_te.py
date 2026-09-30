# -*- coding: utf-8 -*-
"""
Telugu spoken-output templates (Telugu script only).

Single source of truth for every phrase the agent speaks. Phrases are taken
from the reviewed steering table (§6.3). Uses the polite "మీరు" form.

!!! NATIVE-SPEAKER REVIEW REQUIRED before any demo to real callers. !!!
Some dynamically-composed lines (availability, confirmation, receipt) are
assembled here and should be reviewed for natural phrasing.

All output MUST contain Telugu characters — the state machine runs a
Telugu-script guard (see nlp_te.normalize.is_telugu) before "speaking".
"""

from app import config

HOTEL = config.HOTEL_NAME  # "Karivena Satram" — kept in Latin as a proper noun

# ── Static phrases ────────────────────────────────────────────────────────
GREETING = (
    f"నమస్కారం! {HOTEL}కు స్వాగతం. "
    "నేను మీకు గది బుక్ చేయడంలో సహాయం చేస్తాను. "
    "మీకు ఏ తేదీల్లో గది కావాలి?"
)

ASK_CHECKIN = "మీరు ఏ తేదీన రావాలనుకుంటున్నారు?"
ASK_NIGHTS = "ఎన్ని రోజులు ఉంటారు?"
ASK_GUESTS = "ఎంత మంది అతిథులు వస్తారు?"
ASK_ROOM_TYPE = "మీకు ఏసీ గది కావాలా, నాన్-ఏసీ గది కావాలా?"
ASK_LOCATION = "మీకు ఏ ప్రాంతంలో గది కావాలి?"
ASK_NAME = "దయచేసి మీ పేరు చెప్పగలరా?"
ASK_PHONE = "దయచేసి మీ ఫోన్ నంబర్ చెప్పగలరా?"

NOT_UNDERSTOOD = "క్షమించండి, నాకు సరిగ్గా వినిపించలేదు. దయచేసి మళ్ళీ చెప్పగలరా?"
PLEASE_HOLD = "ఒక్క నిమిషం, వివరాలు చూస్తున్నాను."
NOT_AVAILABLE = "క్షమించండి, ఆ తేదీల్లో గదులు అందుబాటులో లేవు. మరో తేదీ చూడమంటారా?"
CONFIRM_PROMPT = "సరిగ్గా ఉందా? బుక్ చేయమంటారా?"
TRANSFER = "ఒక్క నిమిషం, మిమ్మల్ని మా సిబ్బందికి కలుపుతున్నాను."
GOODBYE = "ధన్యవాదాలు! మీ రోజు శుభంగా ఉండాలి."
CANCELLED = "మీ బుకింగ్ రద్దు చేయబడింది."
CANCEL_NOT_FOUND = "క్షమించండి, ఆ నంబర్‌తో బుకింగ్ కనిపించలేదు."
ASK_BOOKING_NUMBER = "దయచేసి మీ బుకింగ్ నంబర్ చెప్పగలరా?"
YES_NO_RETRY = "దయచేసి 'అవును' లేదా 'కాదు' అని చెప్పగలరా?"

# Room-type words in Telugu (for read-back)
ROOM_TYPE_TE = {"AC": "ఏసీ", "Non-AC": "నాన్-ఏసీ"}


# ── Dynamic phrases ───────────────────────────────────────────────────────
def available(location_te: str, room_type: str, price_words: str) -> str:
    """Rooms are available — quote the per-night price (already in Telugu words)."""
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return (
        f"{location_te}లో {rt} గది అందుబాటులో ఉంది. "
        f"ఒక్క రాత్రికి {price_words} రూపాయలు."
    )


def confirm_summary(location_te: str, room_type: str, checkin_words: str,
                    nights_words: str, guests_words: str, price_words: str) -> str:
    """Read the whole booking back before committing."""
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return (
        f"{location_te}లో {rt} గది, {checkin_words} నుండి {nights_words}, "
        f"{guests_words} అతిథులు, మొత్తం {price_words} రూపాయలు. "
        "సరిగ్గా ఉందా? బుక్ చేయమంటారా?"
    )


def booking_done(booking_id_words: str) -> str:
    """Confirmation with the (Telugu-spoken) booking number."""
    return (
        "మీ బుకింగ్ ధృవీకరించబడింది. "
        f"మీ బుకింగ్ నంబర్ {booking_id_words}. "
        "ధన్యవాదాలు!"
    )


def read_back_name(name: str) -> str:
    return f"మీ పేరు {name}, సరిగ్గా ఉందా?"


def read_back_phone(phone_words: str) -> str:
    """phone_words: digits already grouped + converted to Telugu words."""
    return f"మీ ఫోన్ నంబర్ {phone_words}, సరిగ్గా ఉందా?"


def status_found(location_te: str, checkin_words: str, status_te: str) -> str:
    return f"{location_te}లో {checkin_words} తేదీన మీ బుకింగ్ {status_te}గా ఉంది."


def price_answer(location_te: str, room_type: str, price_words: str) -> str:
    rt = ROOM_TYPE_TE.get(room_type, room_type)
    return f"{location_te}లో {rt} గది ధర ఒక్క రాత్రికి {price_words} రూపాయలు."


# Booking status words
STATUS_TE = {
    "confirmed": "ధృవీకరించబడింది",
    "cancelled": "రద్దు చేయబడింది",
}
