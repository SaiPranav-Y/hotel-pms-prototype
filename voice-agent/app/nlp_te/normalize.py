# -*- coding: utf-8 -*-
"""
Telugu number + date normalization.

Two directions:
  1. PARSE caller input (Telugu script, English digits, or mixed) into machine
     values: integers and ISO dates (using Asia/Kolkata "today").
  2. RENDER machine values into spoken Telugu words for TTS (raw digits are
     mispronounced by TTS, so we spell them out).

Also provides the Telugu-script guard used to reject non-Telugu output.
"""

import re
import unicodedata
from datetime import date, timedelta

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    _TZ = None

# ── Telugu-script guard ───────────────────────────────────────────────────
_TELUGU_RANGE = (0x0C00, 0x0C7F)


def is_telugu(text: str) -> bool:
    """True if the text contains at least one Telugu character."""
    return any(_TELUGU_RANGE[0] <= ord(ch) <= _TELUGU_RANGE[1] for ch in (text or ""))


def mostly_latin(text: str) -> bool:
    """True if the text is mostly Latin letters (used to discard bad LLM output)."""
    letters = [c for c in (text or "") if c.isalpha()]
    if not letters:
        return False
    latin = sum(1 for c in letters if "a" <= c.lower() <= "z")
    return latin / len(letters) > 0.5


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


# ── Today (Asia/Kolkata) ──────────────────────────────────────────────────
def today() -> date:
    if _TZ is not None:
        from datetime import datetime
        return datetime.now(_TZ).date()
    return date.today()


# ── Number: digits -> Telugu words (0..99999 covers our needs) ────────────
_TE_ONES = [
    "సున్నా", "ఒకటి", "రెండు", "మూడు", "నాలుగు", "ఐదు", "ఆరు", "ఏడు",
    "ఎనిమిది", "తొమ్మిది", "పది", "పదకొండు", "పన్నెండు", "పదమూడు",
    "పద్నాలుగు", "పదిహేను", "పదహారు", "పదిహేడు", "పద్దెనిమిది", "పంతొమ్మిది",
]
_TE_TENS = {
    20: "ఇరవై", 30: "ముప్పై", 40: "నలభై", 50: "యాభై",
    60: "అరవై", 70: "డెబ్బై", 80: "ఎనభై", 90: "తొంభై",
}


def _two_digit_te(n: int) -> str:
    if n < 20:
        return _TE_ONES[n]
    tens = (n // 10) * 10
    ones = n % 10
    if ones == 0:
        return _TE_TENS[tens]
    return f"{_TE_TENS[tens]} {_TE_ONES[ones]}"


def number_to_telugu(n: int) -> str:
    """Convert a non-negative integer to Telugu words (up to lakhs)."""
    if n < 0:
        return "మైనస్ " + number_to_telugu(-n)
    if n < 20:
        return _TE_ONES[n]
    if n < 100:
        return _two_digit_te(n)
    if n < 1000:
        h, rem = divmod(n, 100)
        s = f"{_TE_ONES[h]} వందల" if h > 1 else "వంద"
        return s if rem == 0 else f"{s} {_two_digit_te(rem) if rem >= 20 or rem < 20 else _TE_ONES[rem]}".replace("  ", " ")
    if n < 100000:
        th, rem = divmod(n, 1000)
        s = f"{number_to_telugu(th)} వేల" if th > 1 else "వెయ్యి"
        return s if rem == 0 else f"{s} {number_to_telugu(rem)}"
    lakh, rem = divmod(n, 100000)
    s = f"{number_to_telugu(lakh)} లక్షల" if lakh > 1 else "లక్ష"
    return s if rem == 0 else f"{s} {number_to_telugu(rem)}"


def digits_to_telugu_grouped(digits: str, group: int = 3) -> str:
    """
    Read a phone/booking number digit-by-digit in Telugu, in groups of `group`.
    e.g. "9876543210" -> "తొమ్మిది ఎనిమిది ఏడు, ఆరు ఐదు నాలుగు, మూడు రెండు ఒకటి, సున్నా"
    """
    only = re.sub(r"\D", "", digits or "")
    words = [_TE_ONES[int(d)] for d in only]
    chunks = [" ".join(words[i:i + group]) for i in range(0, len(words), group)]
    return ", ".join(chunks)


# ── Number: parse Telugu/English words+digits -> int ──────────────────────
_TE_WORD_NUM = {
    # cardinal counting words
    "సున్నా": 0, "ఒకటి": 1, "ఒక": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4,
    "ఐదు": 5, "అయిదు": 5, "ఆరు": 6, "ఏడు": 7, "ఎనిమిది": 8, "తొమ్మిది": 9,
    "పది": 10, "పదకొండు": 11, "పన్నెండు": 12,
    # human-counting forms (people) — common in "how many guests?" answers
    "ఒక్కరు": 1, "ఒకరు": 1, "ఇద్దరు": 2, "ఇద్దరం": 2, "ముగ్గురు": 3,
    "నలుగురు": 4, "ఐదుగురు": 5, "అయిదుగురు": 5, "ఆరుగురు": 6,
    "ఏడుగురు": 7, "ఎనిమిదిమంది": 8, "తొమ్మిదిమంది": 9, "పదిమంది": 10,
}
# English number words that callers may code-mix
_EN_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def parse_number(text: str, default: int | None = None) -> int | None:
    """Extract the first integer from text: digits, Telugu words, or English words."""
    if not text:
        return default
    t = nfc(text).lower()
    m = re.search(r"\d+", t)
    if m:
        return int(m.group())
    for w, v in _TE_WORD_NUM.items():
        if w in t:
            return v
    for w, v in _EN_WORD_NUM.items():
        if re.search(rf"\b{w}\b", t):
            return v
    return default


# ── Dates ─────────────────────────────────────────────────────────────────
_TE_MONTHS = [
    "జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్",
    "జూలై", "ఆగస్టు", "సెప్టెంబర్", "అక్టోబర్", "నవంబర్", "డిసెంబర్",
]
# weekday name (Telugu) -> Python weekday() (Mon=0)
_TE_WEEKDAYS = {
    "సోమవారం": 0, "మంగళవారం": 1, "బుధవారం": 2, "గురువారం": 3,
    "శుక్రవారం": 4, "శనివారం": 5, "ఆదివారం": 6,
}


def date_to_telugu(d: date) -> str:
    """Render a date as spoken Telugu, e.g. 'అక్టోబర్ పన్నెండు'."""
    return f"{_TE_MONTHS[d.month - 1]} {number_to_telugu(d.day)}"


def parse_relative_date(text: str, base: date | None = None) -> date | None:
    """
    Parse a Telugu (or mixed) date expression into an absolute date.

    Handles: రేపు (tomorrow), ఎల్లుండి (day after), ఈరోజు/నేడు (today),
    వచ్చే <weekday> (next weekday), ఈ <weekday> (this coming weekday),
    ISO (2026-10-12), dd/mm(/yyyy), and "<day> <telugu-month>".
    Returns None if nothing recognised.
    """
    if not text:
        return None
    base = base or today()
    t = nfc(text).strip().lower()

    # explicit ISO
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # dd/mm or dd/mm/yyyy
    m = re.search(r"\b(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?\b", t)
    if m:
        d_, mo = int(m.group(1)), int(m.group(2))
        yr = int(m.group(3)) if m.group(3) else base.year
        if yr < 100:
            yr += 2000
        try:
            cand = date(yr, mo, d_)
            if not m.group(3) and cand < base:
                cand = date(yr + 1, mo, d_)
            return cand
        except ValueError:
            pass

    # relative keywords
    if "ఎల్లుండి" in t:
        return base + timedelta(days=2)
    if "రేపు" in t:
        return base + timedelta(days=1)
    if "ఈరోజు" in t or "నేడు" in t or "ఇవాళ" in t:
        return base

    # "వచ్చే <weekday>" / "ఈ <weekday>" / bare weekday -> next occurrence
    for name, wd in _TE_WEEKDAYS.items():
        if name in t:
            ahead = (wd - base.weekday()) % 7
            if ahead == 0:
                ahead = 7  # always a future day
            if "వచ్చే" in t and ahead <= 0:
                ahead += 7
            return base + timedelta(days=ahead)

    # "<day> <telugu-month>"  e.g. "పన్నెండు అక్టోబర్" or "12 అక్టోబర్"
    for i, mon in enumerate(_TE_MONTHS, start=1):
        if mon.lower() in t:
            day = parse_number(t, default=None)
            if day and 1 <= day <= 31:
                yr = base.year
                try:
                    cand = date(yr, i, day)
                    if cand < base:
                        cand = date(yr + 1, i, day)
                    return cand
                except ValueError:
                    pass
    return None


def parse_nights(text: str) -> int | None:
    """
    Parse a stay length: "రెండు రోజులు" -> 2, "3 nights" -> 3, "ఒక రాత్రి" -> 1.
    """
    if not text:
        return None
    t = nfc(text).lower()
    if re.search(r"రోజు|రాత్రి|night|day", t):
        n = parse_number(t)
        if n:
            return n
    return parse_number(t)  # fall back to any bare number
