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


_WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


def _next_weekday(today: date, weekday: int, next_week: bool = False) -> date:
    """Date of the coming `weekday`. If next_week, skip to the following week."""
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # always future, not today
    d = today + timedelta(days=days_ahead)
    if next_week:
        d += timedelta(days=7)
    return d


def _resolve_relative(text_lower: str, today: date) -> str | None:
    """Resolve a single relative-date phrase to an ISO date, or None."""
    # Explicit day offsets first (most specific)
    if "day after tomorrow" in text_lower or "day after" in text_lower:
        return (today + timedelta(days=2)).isoformat()
    if "today" in text_lower or "eeroju" in text_lower or "tonight" in text_lower:
        return today.isoformat()
    if "tomorrow" in text_lower or "repu" in text_lower:
        return (today + timedelta(days=1)).isoformat()

    # Weekend handling ("next weekend" vs "this weekend"/"this saturday")
    if "next weekend" in text_lower:
        return _next_weekday(today, 5, next_week=True).isoformat()
    if "this weekend" in text_lower or "weekend" in text_lower:
        return _next_weekday(today, 5).isoformat()

    # Named weekday ("next friday", "this monday", "on thursday")
    for name, wd in _WEEKDAYS.items():
        if re.search(rf'\b{name}\b', text_lower):
            nxt = "next" in text_lower
            return _next_weekday(today, wd, next_week=nxt).isoformat()

    # Week / month offsets
    if "next month" in text_lower:
        month = today.month + 1
        year = today.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        try:
            return date(year, month, 1).isoformat()
        except ValueError:
            return None
    if "next week" in text_lower:
        return (today + timedelta(days=7)).isoformat()

    return None


def _extract_dates(text: str) -> dict:
    """Extract and resolve dates from natural language (relative + explicit)."""
    today = date.today()
    result = {}
    text_lower = text.lower()

    # 1. Relative check-in date
    relative = _resolve_relative(text_lower, today)
    if relative:
        result["check_in"] = relative

    # 2. Explicit dates — collect ALL matches so ranges ("June 28 to 30") work
    month_map = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    explicit: list[str] = []

    # "28th June" / "June 28" style (day + month name, either order)
    for m in re.finditer(
        r'(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*',
        text_lower,
    ):
        day = int(m.group(1))
        month = month_map.get(m.group(2)[:3], today.month)
        year = today.year + (1 if month < today.month else 0)
        try:
            explicit.append(date(year, month, day).isoformat())
        except ValueError:
            pass
    for m in re.finditer(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*(\d{1,2})',
        text_lower,
    ):
        month = month_map.get(m.group(1)[:3], today.month)
        day = int(m.group(2))
        year = today.year + (1 if month < today.month else 0)
        iso = None
        try:
            iso = date(year, month, day).isoformat()
        except ValueError:
            pass
        if iso and iso not in explicit:
            explicit.append(iso)

    # ISO and slash formats
    for m in re.finditer(r'(\d{4})-(\d{2})-(\d{2})', text):
        explicit.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    for m in re.finditer(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            explicit.append(date(y, mo, d).isoformat())
        except ValueError:
            pass

    # Deduplicate preserving order, then sort chronologically for range logic
    explicit = sorted(dict.fromkeys(explicit))

    if explicit:
        if "check_in" not in result:
            result["check_in"] = explicit[0]
            if len(explicit) > 1:
                result["check_out"] = explicit[1]
        else:
            # relative gave check_in; explicit dates fill check_out
            later = [e for e in explicit if e > result["check_in"]]
            if later:
                result["check_out"] = later[0]

    # 3. Duration → check_out (e.g. "3 nights", "2 rojulu")
    duration_match = re.search(r'(\d+)\s*(night|day|rojulu|din)', text_lower)
    if duration_match and "check_in" in result:
        nights = int(duration_match.group(1))
        check_in = date.fromisoformat(result["check_in"])
        result["check_out"] = (check_in + timedelta(days=nights)).isoformat()
        result["num_nights"] = nights

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
