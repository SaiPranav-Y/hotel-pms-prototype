"""
Telugu Vernacular Dictionary — maps colloquial Telugu/English speech to system terms.
Bidirectional: Telugu → English (for understanding) and English → Telugu (for responses).
Covers: temple names, room types, pilgrim terms, dates, numbers, common phrases.
"""

import re
import logging

logger = logging.getLogger(__name__)


# === LOCATION MAPPINGS ===
# Colloquial/misspelled/Telugu → canonical system name

LOCATION_MAP = {
    # Srisailam variants
    "srisailam": "Srisailam", "sri sailam": "Srisailam", "srishailam": "Srisailam",
    "శ్రీశైలం": "Srisailam", "srisailam gudi": "Srisailam", "mallikarjuna": "Srisailam",
    "mallanna gudi": "Srisailam", "shri shailam": "Srisailam",
    # Tirupathi variants
    "tirupati": "Tirupathi", "tirupathi": "Tirupathi", "tirumala": "Tirupathi",
    "తిరుపతి": "Tirupathi", "balaji": "Tirupathi", "venkateswara": "Tirupathi",
    "govinda": "Tirupathi", "tirpati": "Tirupathi", "tirupti": "Tirupathi",
    # Shirdi variants
    "shirdi": "Shiridi", "shiridi": "Shiridi", "షిర్డి": "Shiridi",
    "sai baba": "Shiridi", "sai temple": "Shiridi", "saibaba": "Shiridi",
    # Kasi variants
    "kasi": "Kasi", "kashi": "Kasi", "varanasi": "Kasi", "banaras": "Kasi",
    "కాశీ": "Kasi", "benares": "Kasi",
    # Mahanandi variants
    "mahanandi": "Mahanandi", "mahanandiswara": "Mahanandi", "మహానంది": "Mahanandi",
    "nandi": "Mahanandi",
    # Rameswaram variants
    "rameswaram": "Rameswaram", "rameshwaram": "Rameswaram", "రామేశ్వరం": "Rameswaram",
    "rameshwar": "Rameswaram", "dhanushkodi": "Rameswaram",
    # Brundavanam
    "brundavanam": "Brundavanam", "బృందావనం": "Brundavanam", "vrindavan": "Brundavanam",
    # Naimisaranyam
    "naimisaranyam": "Naimisaranyam", "naimisharanya": "Naimisaranyam",
    "నైమిశారణ్యం": "Naimisaranyam", "nimsar": "Naimisaranyam",
    # Arunachalam
    "arunachalam": "Arunachalam", "tiruvannamalai": "Arunachalam",
    "అరుణాచలం": "Arunachalam", "arunachala": "Arunachalam",
    # Vruddasramam
    "vruddasramam": "Vruddasramam", "vruddashramam": "Vruddasramam",
    "వృద్ధాశ్రమం": "Vruddasramam", "old age home": "Vruddasramam",
}


# === ROOM TYPE MAPPINGS ===

ROOM_TYPE_MAP = {
    # AC variants
    "ac": "ac", "a c": "ac", "ac room": "ac", "air condition": "ac",
    "air conditioned": "ac", "ac gadi": "ac", "ఎసి": "ac", "ఏసీ రూమ్": "ac",
    "cool room": "ac", "ac wala": "ac",
    # Non-AC variants
    "non ac": "nonac", "non-ac": "nonac", "without ac": "nonac",
    "fan room": "nonac", "normal room": "nonac", "non a c": "nonac",
    "నాన్ ఎసి": "nonac", "ఫ్యాన్ రూమ్": "nonac", "plain room": "nonac",
    "ordinary": "nonac", "fan only": "nonac",
}


# === PILGRIM VOCABULARY ===
# Telugu pilgrim terms → English meaning

PILGRIM_TERMS = {
    # Accommodation
    "room": "room", "gadi": "room", "గది": "room",
    "satram": "accommodation", "సత్రం": "accommodation",
    "viడidi": "stay", "విడిది": "stay", "stay": "stay",
    "booking": "booking", "బుకింగ్": "booking", "reserve": "booking",
    # Time
    "repu": "tomorrow", "రేపు": "tomorrow",
    "eeroju": "today", "ఈరోజు": "today",
    "ninna": "yesterday", "నిన్న": "yesterday",
    "vaaram": "week", "వారం": "week",
    "nelaa": "month", "నెల": "month",
    "rojulu": "days", "రోజులు": "days",
    # Numbers (Telugu → digit)
    "okati": "1", "ఒకటి": "1", "one": "1",
    "rendu": "2", "రెండు": "2", "two": "2",
    "moodu": "3", "మూడు": "3", "three": "3",
    "naalu": "4", "నాలుగు": "4", "four": "4",
    "aidu": "5", "ఐదు": "5", "five": "5",
    # Common phrases
    "darshan": "temple visit", "దర్శనం": "temple visit",
    "pooja": "prayer", "పూజ": "prayer",
    "prasadam": "blessed food", "ప్రసాదం": "blessed food",
    "yatra": "pilgrimage", "యాత్ర": "pilgrimage",
    "bhaktulu": "devotees", "భక్తులు": "devotees",
    # Actions
    "book cheyyi": "make a booking", "బుక్ చెయ్యి": "make a booking",
    "cancel cheyyi": "cancel", "క్యాన్సిల్ చెయ్యి": "cancel",
    "check cheyyi": "check availability", "చెక్ చెయ్యి": "check availability",
    "entha": "how much", "ఎంత": "how much",
    "evaru": "who", "ఎవరు": "who",
    "eppudu": "when", "ఎప్పుడు": "when",
    "ekkada": "where", "ఎక్కడ": "where",
}


# === ENGLISH → TELUGU (for AI responses in Telugu) ===

ENGLISH_TO_TELUGU = {
    "welcome": "సుస్వాగతం",
    "thank you": "ధన్యవాదాలు",
    "room is available": "గది అందుబాటులో ఉంది",
    "room not available": "గది అందుబాటులో లేదు",
    "booking confirmed": "బుకింగ్ కన్ఫర్మ్ అయింది",
    "booking cancelled": "బుకింగ్ క్యాన్సిల్ అయింది",
    "check-in": "చెక్-ఇన్",
    "check-out": "చెక్-అవుట్",
    "per night": "ఒక రాత్రికి",
    "rupees": "రూపాయలు",
    "how can I help": "నేను మీకు ఎలా సహాయం చేయగలను",
    "please wait": "దయచేసి వేచి ఉండండి",
    "your booking id is": "మీ బుకింగ్ ఐడి",
    "which location": "ఏ ప్రదేశం",
    "how many rooms": "ఎన్ని గదులు",
    "what dates": "ఏ తేదీలు",
}


# === LOOKUP FUNCTIONS ===

def normalize_location(text: str) -> str | None:
    """Map any colloquial/Telugu location reference to canonical name."""
    text_lower = text.lower().strip()
    # Direct match
    if text_lower in LOCATION_MAP:
        return LOCATION_MAP[text_lower]
    # Substring match
    for key, val in LOCATION_MAP.items():
        if key in text_lower:
            return val
    return None


def normalize_room_type(text: str) -> str | None:
    """Map colloquial room type reference to 'ac' or 'nonac'."""
    text_lower = text.lower().strip()
    if text_lower in ROOM_TYPE_MAP:
        return ROOM_TYPE_MAP[text_lower]
    for key, val in ROOM_TYPE_MAP.items():
        if key in text_lower:
            return val
    return None


def translate_term(text: str) -> str | None:
    """Translate a Telugu/colloquial term to English meaning."""
    text_lower = text.lower().strip()
    if text_lower in PILGRIM_TERMS:
        return PILGRIM_TERMS[text_lower]
    for key, val in PILGRIM_TERMS.items():
        if key in text_lower:
            return val
    return None


def get_telugu_phrase(english: str) -> str:
    """Get Telugu translation for an English phrase (for AI Telugu responses)."""
    return ENGLISH_TO_TELUGU.get(english.lower(), english)


def enrich_text(text: str) -> str:
    """
    Process input text: normalize locations, room types, and translate terms.
    Returns enriched English text suitable for the LLM.
    """
    result = text

    # Normalize locations
    loc = normalize_location(text)
    if loc:
        result += f" [LOCATION: {loc}]"

    # Normalize room types
    rt = normalize_room_type(text)
    if rt:
        result += f" [ROOM_TYPE: {rt}]"

    # Translate Telugu terms
    for key, val in PILGRIM_TERMS.items():
        if key in text.lower() and key != val:
            result = result + f" [MEANS: {val}]"
            break

    return result


def detect_language(text: str) -> str:
    """Simple detection: Telugu script present → telugu, else english."""
    telugu_range = re.compile(r'[\u0C00-\u0C7F]')
    if telugu_range.search(text):
        return "telugu"
    return "english"


def get_dictionary_stats() -> dict:
    """Stats about the dictionary."""
    return {
        "locations": len(LOCATION_MAP),
        "room_types": len(ROOM_TYPE_MAP),
        "pilgrim_terms": len(PILGRIM_TERMS),
        "telugu_phrases": len(ENGLISH_TO_TELUGU),
    }
