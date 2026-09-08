"""
Gotram Module — community eligibility validation.

Karivena Satram serves a specific Hindu community. Only members with an
approved Gotram may reserve/book rooms. Gotram is a MANDATORY field for
all reservations and bookings.

The allowed gotram list loads from:
  1. app/allowed_gotrams.json  (if present)
  2. Firestore 'allowed_gotrams' collection (if present)
  3. A built-in default list (fallback)

Supported allowed_gotrams.json formats:
  A) Simple:  {"gotrams": ["Bharadwaja", "Kashyapa", ...]}
  B) Rich:    {"gotrams": [
                 {"canonical": "Bharadwaja", "telugu": "భారద్వాజ",
                  "aliases": ["Bharadwaj", "Bharadhwaja", ...]},
                 ...
              ]}

Matching is robust:
  - Case / space / punctuation insensitive
  - Strips trailing "gotram/gothram/gotra/sa" suffixes
  - Works on English transliterations AND Telugu Unicode
  - Matches canonical names, Telugu spellings, and every alias
  - Fuzzy fallback (edit-distance) for minor ASR / spelling slips,
    guarded by length so short inputs don't false-match
"""

import json
import logging
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

_GOTRAM_FILE = Path(__file__).parent / "allowed_gotrams.json"

# Fallback default list (used only if file + Firestore are unavailable)
_DEFAULT_GOTRAMS = [
    "Bharadwaja", "Kashyapa", "Vasishta", "Vishwamitra", "Gautama",
    "Atreya", "Bhrigu", "Angirasa", "Agastya", "Koundinya",
    "Shandilya", "Srivatsa", "Harita", "Gargya", "Koutsa",
    "Jamadagni", "Kaushika", "Moudgalya", "Sankhyayana", "Parashara",
]

# norm(alias/telugu/canonical) -> canonical display name
_lookup: dict[str, str] = {}
# set of canonical display names
_canonical_names: set[str] = set()
_loaded = False


def _normalize(g: str) -> str:
    """
    Normalize a gotram string for comparison.
    - Unicode NFC (so Telugu combines consistently)
    - Lowercase, strip
    - Remove trailing 'gotram/gothram/gotra/sa/vamsa'
    - Keep only letters (Latin a-z AND Telugu block); drop spaces/punctuation
    """
    if not g:
        return ""
    g = unicodedata.normalize("NFC", str(g)).strip().lower()
    # strip common spoken/written suffixes
    g = re.sub(r'\s*(gotram|gothram|gotra|gothra|vamsa|vamsam)\s*$', '', g)
    # keep Latin letters and Telugu unicode range (0C00–0C7F); drop the rest
    kept = []
    for ch in g:
        if "a" <= ch <= "z":
            kept.append(ch)
        elif "\u0c00" <= ch <= "\u0c7f":
            kept.append(ch)
    out = "".join(kept)
    # drop a trailing bare 'sa' only for Latin (e.g. "Bharadwajasa" -> "bharadwaja")
    if out.isascii() and out.endswith("sa") and len(out) > 5:
        out = out[:-2]
    return out


def _register(canonical: str, variants: list[str]):
    """Register a canonical name and all of its variant spellings."""
    canonical = (canonical or "").strip()
    if not canonical:
        return
    _canonical_names.add(canonical)
    all_forms = [canonical] + list(variants or [])
    for form in all_forms:
        norm = _normalize(form)
        if norm:
            # first registration wins for a given normalized key
            _lookup.setdefault(norm, canonical)


def load_gotrams():
    """Load allowed gotrams from file, then Firestore, then default."""
    global _loaded, _lookup, _canonical_names
    _lookup = {}
    _canonical_names = set()

    raw = None

    # 1. Local JSON file
    if _GOTRAM_FILE.exists():
        try:
            with open(_GOTRAM_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw = data.get("gotrams", [])
                logger.info(f"Gotrams loaded from file: {len(raw)}")
        except Exception as e:
            logger.error(f"Failed to read gotram file: {e}")

    # 2. Firestore
    if not raw:
        try:
            from app.firebase_store import is_firebase_active, _db
            if is_firebase_active() and _db:
                docs = list(_db.collection("allowed_gotrams").stream())
                raw = []
                for d in docs:
                    dd = d.to_dict()
                    raw.append(dd if "canonical" in dd else dd.get("name", ""))
                if raw:
                    logger.info(f"Gotrams loaded from Firestore: {len(raw)}")
        except Exception as e:
            logger.debug(f"Firestore gotram load skipped: {e}")

    # 3. Default
    if not raw:
        raw = _DEFAULT_GOTRAMS
        logger.info(f"Using default gotram list: {len(raw)}")

    # Parse both simple (str) and rich (dict) entries
    for entry in raw:
        if isinstance(entry, str):
            _register(entry, [])
        elif isinstance(entry, dict):
            canonical = entry.get("canonical") or entry.get("name") or ""
            variants = []
            if entry.get("telugu"):
                variants.append(entry["telugu"])
            variants.extend(entry.get("aliases", []) or [])
            _register(canonical, variants)

    _loaded = True
    logger.info(f"Gotram lookup ready: {len(_canonical_names)} canonical, "
                f"{len(_lookup)} match keys")


def _fuzzy_best(norm: str) -> str | None:
    """
    Fuzzy-match a normalized input against known keys using edit-distance
    ratio. Guarded so short strings don't false-match. Returns canonical or None.
    """
    if len(norm) < 4:
        return None
    best_ratio = 0.0
    best_canon = None
    for key, canon in _lookup.items():
        if abs(len(key) - len(norm)) > 3:
            continue
        r = SequenceMatcher(None, norm, key).ratio()
        if r > best_ratio:
            best_ratio = r
            best_canon = canon
    # Require a strong similarity to accept
    return best_canon if best_ratio >= 0.86 else None


def is_allowed(gotram: str) -> bool:
    """Check if a gotram is in the approved community list."""
    return match_gotram(gotram) is not None


def match_gotram(spoken: str) -> str | None:
    """
    Match a spoken/typed gotram to the canonical approved name.
    Handles 'bharadwaja gotram', 'Kashyap', Telugu text, minor misspellings.
    Returns the canonical display name or None.
    """
    if not _loaded:
        load_gotrams()
    norm = _normalize(spoken)
    if not norm:
        return None

    # 1. Exact normalized match (canonical / telugu / alias)
    if norm in _lookup:
        return _lookup[norm]

    # 2. Whole-token prefix match (input is a clean prefix of a known key,
    #    or a known key is a prefix of the input) — length-guarded to avoid
    #    e.g. "ka" matching "kashyapa".
    for key, canon in _lookup.items():
        if len(norm) >= 4 and len(key) >= 4:
            if norm.startswith(key) or key.startswith(norm):
                return canon

    # 3. Fuzzy fallback for small ASR/spelling slips
    return _fuzzy_best(norm)


def get_all_gotrams() -> list[str]:
    """Return the sorted list of canonical approved gotram names."""
    if not _loaded:
        load_gotrams()
    return sorted(_canonical_names)


def add_gotram(name: str, telugu: str = "", aliases: list[str] | None = None) -> bool:
    """Add a gotram to the allowed list (runtime + Firestore)."""
    if not name or not name.strip():
        return False
    if not _loaded:
        load_gotrams()
    _register(name, ([telugu] if telugu else []) + (aliases or []))
    # Persist to Firestore
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("allowed_gotrams").document(_normalize(name)).set({
                "canonical": name.strip(),
                "telugu": telugu.strip() if telugu else "",
                "aliases": aliases or [],
                "name": name.strip(),
            })
    except Exception:
        pass
    return True


def get_gotram_count() -> int:
    """Number of distinct canonical gotrams."""
    if not _loaded:
        load_gotrams()
    return len(_canonical_names)


# Load on import
load_gotrams()
