"""
Query Normalization Layer — cleans ASR output before it hits the LLM.
Handles: misspellings, date resolution, number parsing, intent extraction.
Uses the vernacular dictionary for Telugu term resolution.
"""

import re
import logging
from datetime import date, timedelta

from app.vernacular import normalize_location, normalize_room_type, enrich_text, detect_language

logger = logging.getLogger(__name__)


def normalize_query(text: str) -> dict:
    """
    Full normalization pipeline on user speech input.
    Returns: {"normalized_text": str, "extracted": dict, "language": str}
    """
    original = text.strip()
    if not original:
        return {"normalized_text": "", "extracted": {}, "language": "english"}

    language = detect_language(original)
    normalized = original
    extracted = {}

    # Step 1: Fix common ASR errors
    normalized = _fix_asr_errors(normalized)

    # Step 2: Normalize dates ("tomorrow", "next week", "28th June")
    date_info = _extract_dates(normalized)
    if date_info:
        extracted.update(date_info)

    # Step 3: Extract numbers (rooms, guests, age)
    numbers = _extract_numbers(normalized)
    if numbers:
        extracted.update(numbers)

    # Step 4: Normalize location via vernacular dictionary
    loc = normalize_location(normalized)
    if loc:
        extracted["location"] = loc

    # Step 5: Normalize room type
    rt = normalize_room_type(normalized)
    if rt:
        extracted["room_type"] = rt

    # Step 6: Detect phone number
    phone = _extract_phone(normalized)
    if phone:
        extracted["phone"] = phone

    # Step 7: Enrich with vernacular annotations
    enriched = enrich_text(normalized)

    return {
        "normalized_text": enriched,
        "original_text": original,
        "extracted": extracted,
        "language": language,
    }


def _fix_asr_errors(text: str) -> str:
    """Fix common speech-to-text recognition errors."""
    fixes = {
        # Common ASR mishearings
        r'\bsri sailam\b': 'srisailam',
        r'\btiru pati\b': 'tirupathi',
        r'\bshir dee\b': 'shirdi',
        r'\bka shi\b': 'kasi',
        r'\broom book\b': 'room booking',
        r'\ba see\b': 'AC',
        r'\bnon a see\b': 'Non AC',
        r'\bair condition\b': 'AC',
        r'\bcheck in\b': 'check-in',
        r'\bcheck out\b': 'check-out',
        # Number words to digits
        r'\bone room\b': '1 room',
        r'\btwo rooms?\b': '2 rooms',
        r'\bthree rooms?\b': '3 rooms',
        r'\bfour rooms?\b': '4 rooms',
        r'\bfive rooms?\b': '5 rooms',
        r'\bone night\b': '1 night',
        r'\btwo nights?\b': '2 nights',
        r'\bthree nights?\b': '3 nights',
        r'\bfour nights?\b': '4 nights',
        r'\bfive nights?\b': '5 nights',
    }

    result = text
    for pattern, replacement in fixes.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _extract_dates(text: str) -> dict:
    """Extract and resolve dates from natural language."""
    today = date.today()
    result = {}
    text_lower = text.lower()

    # Relative dates
    if "today" in text_lower or "eeroju" in text_lower:
        result["check_in"] = today.isoformat()
    elif "tomorrow" in text_lower or "repu" in text_lower:
        result["check_in"] = (today + timedelta(days=1)).isoformat()
    elif "day after" in text_lower:
        result["check_in"] = (today + timedelta(days=2)).isoformat()
    elif "next week" in text_lower:
        result["check_in"] = (today + timedelta(days=7)).isoformat()
    elif "this weekend" in text_lower or "this saturday" in text_lower:
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        result["check_in"] = (today + timedelta(days=days_until_saturday)).isoformat()

    # Duration → check_out
    duration_match = re.search(r'(\d+)\s*(night|day|rojulu|din)', text_lower)
    if duration_match and "check_in" in result:
        nights = int(duration_match.group(1))
        check_in = date.fromisoformat(result["check_in"])
        result["check_out"] = (check_in + timedelta(days=nights)).isoformat()
        result["num_nights"] = nights

    # Explicit date patterns (28th June, June 28, 28/06/2026)
    date_patterns = [
        r'(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*',
        r'(\d{4})-(\d{2})-(\d{2})',
        r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
    ]
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

    match = re.search(date_patterns[0], text_lower)
    if match:
        day = int(match.group(1))
        month = month_map.get(match.group(2)[:3], today.month)
        year = today.year
        if month < today.month:
            year += 1
        try:
            parsed = date(year, month, day)
            if "check_in" not in result:
                result["check_in"] = parsed.isoformat()
            else:
                result["check_out"] = parsed.isoformat()
        except ValueError:
            pass

    return result


def _extract_numbers(text: str) -> dict:
    """Extract room count, guest count, age from text."""
    result = {}

    # Rooms
    room_match = re.search(r'(\d+)\s*room', text.lower())
    if room_match:
        result["num_rooms"] = int(room_match.group(1))

    # Guests/persons
    guest_match = re.search(r'(\d+)\s*(person|guest|people|member)', text.lower())
    if guest_match:
        result["num_guests"] = int(guest_match.group(1))

    # Age
    age_match = re.search(r'(\d{1,2})\s*(years?\s*old|yrs?\s*old|age)', text.lower())
    if age_match:
        result["age"] = age_match.group(1)

    return result


def _extract_phone(text: str) -> str | None:
    """Extract 10-digit Indian phone number."""
    match = re.search(r'\b([6-9]\d{9})\b', text)
    return match.group(1) if match else None
