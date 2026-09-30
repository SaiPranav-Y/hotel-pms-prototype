"""
Rate Management — room rates by (location x room_type x season).

Only ADMIN and SUPER_ADMIN can edit rates (enforced at route level).
Rates load from:
  1. app/rate_config.json  (if present — you'll provide the finalized rates later)
  2. Firestore 'rates' collection
  3. Fallback: prices already parsed from the Excel (room_data.json)

Season support: rates can have date-range overrides (e.g., festival pricing).
Base rate applies when no season matches.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_RATE_FILE = Path(__file__).parent / "rate_config.json"

# Structure:
# {
#   "srisailam": {
#     "ac":    {"base": 1200, "seasons": [{"name":"Festival","from":"2026-02-01","to":"2026-02-28","rate":1800}]},
#     "nonac": {"base": 600,  "seasons": []}
#   }, ...
# }
_rates: dict = {}
_loaded = False


def load_rates():
    """Load rates from file → Firestore → Excel fallback."""
    global _rates, _loaded

    # 1. Local JSON
    if _RATE_FILE.exists():
        try:
            with open(_RATE_FILE, "r", encoding="utf-8") as f:
                _rates = json.load(f)
            logger.info(f"Rates loaded from file: {len(_rates)} locations")
            _loaded = True
            return
        except Exception as e:
            logger.error(f"Rate file read failed: {e}")

    # 2. Firestore
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            docs = list(_db.collection("rates").stream())
            if docs:
                for d in docs:
                    _rates[d.id] = d.to_dict()
                logger.info(f"Rates loaded from Firestore: {len(_rates)} locations")
                _loaded = True
                return
    except Exception:
        pass

    # 3. Fallback: derive from Excel-parsed room_data.json
    try:
        from app.knowledge_base import get_all_locations
        for key, loc in get_all_locations().items():
            ac_price = loc["prices_ac"][0] if loc.get("prices_ac") else 0
            nonac_price = loc["prices_nonac"][0] if loc.get("prices_nonac") else 0
            _rates[key] = {
                "ac": {"base": ac_price, "seasons": []},
                "nonac": {"base": nonac_price, "seasons": []},
            }
        logger.info(f"Rates derived from Excel: {len(_rates)} locations")
    except Exception as e:
        logger.error(f"Rate fallback failed: {e}")

    _loaded = True


def get_rate(location: str, room_type: str, on_date: date = None) -> int:
    """
    Get the nightly rate for a location + room type on a given date.
    Applies season override if a matching date-range season exists.
    """
    if not _loaded:
        load_rates()
    if not on_date:
        on_date = date.today()

    key = location.lower().replace(" ", "_")
    rt = "nonac" if "non" in room_type.lower() else "ac"

    loc_rates = _rates.get(key, {})
    room_rates = loc_rates.get(rt, {})
    base = room_rates.get("base", 0)

    # Check seasons
    for season in room_rates.get("seasons", []):
        try:
            s_from = date.fromisoformat(season["from"])
            s_to = date.fromisoformat(season["to"])
            if s_from <= on_date <= s_to:
                return season["rate"]
        except Exception:
            continue

    return base


def get_all_rates() -> dict:
    """Return the full rate table (for admin UI)."""
    if not _loaded:
        load_rates()
    return _rates


def set_rate(location: str, room_type: str, base_rate: int) -> dict:
    """Set the base rate for a location + room type (ADMIN only)."""
    if not _loaded:
        load_rates()
    key = location.lower().replace(" ", "_")
    rt = "nonac" if "non" in room_type.lower() else "ac"

    if key not in _rates:
        _rates[key] = {}
    if rt not in _rates[key]:
        _rates[key][rt] = {"base": 0, "seasons": []}

    _rates[key][rt]["base"] = int(base_rate)
    _persist(key)
    logger.info(f"Rate set: {key}/{rt} = {base_rate}")
    return {"success": True, "location": key, "room_type": rt, "base": base_rate}


def add_season_rate(location: str, room_type: str, name: str, from_date: str, to_date: str, rate: int) -> dict:
    """Add a seasonal rate override (ADMIN only)."""
    if not _loaded:
        load_rates()
    key = location.lower().replace(" ", "_")
    rt = "nonac" if "non" in room_type.lower() else "ac"

    if key not in _rates:
        _rates[key] = {}
    if rt not in _rates[key]:
        _rates[key][rt] = {"base": 0, "seasons": []}

    _rates[key][rt].setdefault("seasons", []).append({
        "name": name, "from": from_date, "to": to_date, "rate": int(rate),
    })
    _persist(key)
    return {"success": True, "season": name}


def compute_total(location: str, room_type: str, check_in: date, check_out: date, num_rooms: int = 1) -> dict:
    """Compute total price across the stay, applying per-night season rates."""
    if not _loaded:
        load_rates()
    from datetime import timedelta

    total = 0
    nights = 0
    current = check_in
    while current < check_out:
        total += get_rate(location, room_type, current)
        nights += 1
        current += timedelta(days=1)

    total *= num_rooms
    return {
        "location": location,
        "room_type": room_type,
        "nights": nights,
        "num_rooms": num_rooms,
        "total": total,
        "currency": "INR",
    }


def _persist(location_key: str):
    """Save a location's rates to Firestore."""
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("rates").document(location_key).set(_rates[location_key])
    except Exception:
        pass


load_rates()
