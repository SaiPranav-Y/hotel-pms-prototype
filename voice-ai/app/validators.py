"""
Shared input validation + sanitization.

Used by the booking creation path and API routes so that dates, phone numbers,
names and emails are consistently checked and cleaned on the backend — never
trusting client input. Mirrors the Flutter `lib/utils/validators.dart` rules so
both channels behave the same.
"""

import re
from datetime import date

# --- patterns ---
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Indian mobile after normalisation: 10 digits starting 6-9 (optionally +91)
_PHONE_DIGITS_RE = re.compile(r"\d")
_NAME_ALLOWED_RE = re.compile(r"[^A-Za-z\u0C00-\u0C7F .'\-]")  # letters (+Telugu), space, . ' -
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_text(value: str, max_len: int = 200) -> str:
    """Trim, collapse whitespace, strip control chars. Never returns None."""
    if value is None:
        return ""
    s = _CONTROL_RE.sub("", str(value)).strip()
    s = re.sub(r"\s+", " ", s)
    return s[:max_len]


def sanitize_name(value: str, max_len: int = 100) -> str:
    """Sanitize a person/place name: allowed chars only, collapsed spaces."""
    s = sanitize_text(value, max_len)
    return _NAME_ALLOWED_RE.sub("", s).strip()


def is_valid_name(value: str) -> bool:
    s = sanitize_name(value)
    return len(s) >= 2


def is_valid_email(value: str) -> bool:
    return bool(_EMAIL_RE.match((value or "").strip()))


def normalize_phone(value: str) -> str:
    """
    Normalise an Indian phone to +91XXXXXXXXXX when possible.
    Keeps only digits; drops a leading 0 or 91 country prefix, re-adds +91.
    Returns the cleaned string (may be unchanged if it isn't a 10-digit mobile).
    """
    if not value:
        return ""
    digits = "".join(_PHONE_DIGITS_RE.findall(str(value)))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    # Fall back: return the raw digits (validation will flag it)
    return "+" + digits if digits else ""


def is_valid_phone(value: str) -> bool:
    """A valid Indian mobile: 10 digits starting 6-9 (after normalisation)."""
    digits = "".join(_PHONE_DIGITS_RE.findall(str(value or "")))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return len(digits) == 10 and digits[0] in "6789"


def validate_stay(check_in: date, check_out: date) -> tuple[bool, str]:
    """Validate a stay date range. Returns (ok, error_message)."""
    if not check_in or not check_out:
        return False, "Both check-in and check-out dates are required."
    if check_out <= check_in:
        return False, "Check-out must be after check-in."
    if check_in < date.today():
        return False, "Check-in cannot be in the past."
    if (check_out - check_in).days > 60:
        return False, "Stay cannot exceed 60 nights."
    return True, ""


def validate_rooms(num_rooms) -> tuple[bool, str]:
    try:
        n = int(num_rooms)
    except (TypeError, ValueError):
        return False, "Number of rooms must be a whole number."
    if n < 1:
        return False, "At least 1 room is required."
    if n > 100:
        return False, "Cannot book more than 100 rooms at once."
    return True, ""
