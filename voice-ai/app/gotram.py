"""
Gotram Module — community eligibility validation.

Karivena Satram serves a specific Hindu community. Only members with an
approved Gotram may reserve/book rooms. Gotram is a MANDATORY field for
all reservations and bookings.

The allowed gotram list loads from:
  1. app/allowed_gotrams.json  (if present)
  2. Firestore 'allowed_gotrams' collection (if present)
  3. A built-in default list (fallback)

Drop your finalized gotram list into app/allowed_gotrams.json as:
  {"gotrams": ["Bharadwaja", "Kashyapa", ...]}
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_GOTRAM_FILE = Path(__file__).parent / "allowed_gotrams.json"

# Fallback default list of common Brahmin gotrams (replace with your finalized list)
_DEFAULT_GOTRAMS = [
    "Bharadwaja", "Kashyapa", "Vasishta", "Vishwamitra", "Gautama",
    "Atri", "Bhrigu", "Angirasa", "Agastya", "Kaundinya",
    "Shandilya", "Srivatsa", "Harita", "Garga", "Kutsa",
    "Jamadagni", "Kaushika", "Mudgala", "Sankhyayana", "Parashara",
]

_allowed_gotrams: set[str] = set()
_loaded = False


def _normalize(g: str) -> str:
    """Normalize a gotram string for comparison (case/space/suffix-insensitive)."""
    g = g.strip().lower()
    # Remove common suffixes people add: "gotram", "gothram", "sa"
    g = re.sub(r'\s*(gotram|gothram|gotra)\s*$', '', g)
    g = re.sub(r'[^a-z]', '', g)  # keep letters only
    return g


def load_gotrams():
    """Load allowed gotrams from file, then Firestore, then default."""
    global _allowed_gotrams, _loaded

    raw_list = []

    # 1. Try local JSON file
    if _GOTRAM_FILE.exists():
        try:
            with open(_GOTRAM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_list = data.get("gotrams", [])
                logger.info(f"Gotrams loaded from file: {len(raw_list)}")
        except Exception as e:
            logger.error(f"Failed to read gotram file: {e}")

    # 2. Try Firestore
    if not raw_list:
        try:
            from app.firebase_store import is_firebase_active, _db
            if is_firebase_active() and _db:
                docs = _db.collection("allowed_gotrams").stream()
                raw_list = [d.to_dict().get("name", "") for d in docs]
                if raw_list:
                    logger.info(f"Gotrams loaded from Firestore: {len(raw_list)}")
        except Exception as e:
            logger.debug(f"Firestore gotram load skipped: {e}")

    # 3. Fallback to default
    if not raw_list:
        raw_list = _DEFAULT_GOTRAMS
        logger.info(f"Using default gotram list: {len(raw_list)}")

    # Build normalized lookup set (store original name mapping too)
    global _gotram_display
    _gotram_display = {}
    _allowed_gotrams = set()
    for g in raw_list:
        norm = _normalize(g)
        if norm:
            _allowed_gotrams.add(norm)
            _gotram_display[norm] = g.strip()

    _loaded = True


def is_allowed(gotram: str) -> bool:
    """Check if a gotram is in the approved community list."""
    if not _loaded:
        load_gotrams()
    if not gotram:
        return False
    return _normalize(gotram) in _allowed_gotrams


def match_gotram(spoken: str) -> str | None:
    """
    Try to match a spoken/typed gotram to the canonical approved name.
    Handles fuzzy input like 'bharadwaja gotram', 'Kashyap', etc.
    Returns the canonical display name or None.
    """
    if not _loaded:
        load_gotrams()
    norm = _normalize(spoken)
    if not norm:
        return None
    # Exact normalized match
    if norm in _allowed_gotrams:
        return _gotram_display.get(norm, spoken.strip())
    # Prefix / contains match (handles partial ASR)
    for allowed_norm, display in _gotram_display.items():
        if norm in allowed_norm or allowed_norm in norm:
            return display
    return None


def get_all_gotrams() -> list[str]:
    """Return the list of allowed gotram display names."""
    if not _loaded:
        load_gotrams()
    return sorted(_gotram_display.values())


def add_gotram(name: str) -> bool:
    """Add a gotram to the allowed list (runtime + Firestore)."""
    if not name.strip():
        return False
    norm = _normalize(name)
    _allowed_gotrams.add(norm)
    _gotram_display[norm] = name.strip()
    # Persist to Firestore
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("allowed_gotrams").document(norm).set({"name": name.strip()})
    except Exception:
        pass
    return True


def get_gotram_count() -> int:
    if not _loaded:
        load_gotrams()
    return len(_allowed_gotrams)


# module-level display map
_gotram_display: dict[str, str] = {}

# Load on import
load_gotrams()
