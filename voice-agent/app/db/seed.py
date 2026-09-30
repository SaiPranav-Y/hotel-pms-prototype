"""Seed the SQLite `rooms` table from the Karivena room/rate data.

Reads room_data.json (per-location AC/Non-AC counts + base prices) and, when
available, rate_config.json (admin base rates) — reusing the same source of
truth as the main PMS backend. Idempotent: clears + reseeds `rooms`.
"""

import json
import logging

from app import config
from app.db.models import Room, init_db, get_session

logger = logging.getLogger(__name__)


def _load_json(path: str) -> dict:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not read {path}: {e}")
        return {}


def _rate_for(rate_cfg: dict, loc_key: str, room_type: str, fallback: int) -> int:
    """Prefer rate_config.json base rate; fall back to room_data price."""
    entry = rate_cfg.get(loc_key, {})
    rt = "nonac" if "non" in room_type.lower() else "ac"
    base = (entry.get(rt) or {}).get("base", 0)
    return int(base) if base else int(fallback or 0)


def seed(db_path: str = None) -> int:
    """(Re)seed rooms. Returns the number of room rows written."""
    db_path = db_path or config.DB_PATH
    init_db(db_path)

    room_data = _load_json(config.ROOM_DATA_PATH)
    rate_cfg = _load_json(config.RATE_CONFIG_PATH)

    if not room_data:
        logger.warning("No room_data.json found — seeding a tiny demo fallback.")
        room_data = {
            "srisailam": {"name": "Srisailam", "ac_rooms": 10, "nonac_rooms": 5,
                          "prices_ac": [1500], "prices_nonac": [500]},
        }

    session = get_session()
    written = 0
    try:
        session.query(Room).delete()
        for loc_key, loc in room_data.items():
            name = loc.get("name", loc_key.title())
            ac = int(loc.get("ac_rooms", 0) or 0)
            nonac = int(loc.get("nonac_rooms", 0) or 0)
            ac_price = (loc.get("prices_ac") or [0])
            nonac_price = (loc.get("prices_nonac") or [0])
            ac_price = ac_price[0] if ac_price else 0
            nonac_price = nonac_price[0] if nonac_price else 0

            if ac > 0:
                session.add(Room(
                    location=name, type="AC", capacity=ac,
                    price_per_night=_rate_for(rate_cfg, loc_key, "ac", ac_price),
                    active=True,
                ))
                written += 1
            if nonac > 0:
                session.add(Room(
                    location=name, type="Non-AC", capacity=nonac,
                    price_per_night=_rate_for(rate_cfg, loc_key, "nonac", nonac_price),
                    active=True,
                ))
                written += 1
        session.commit()
        logger.info(f"Seeded {written} room rows from Karivena data.")
    finally:
        session.close()
    return written


def all_locations() -> list[str]:
    """Distinct active location names (for the dialogue + templates)."""
    session = get_session()
    try:
        rows = session.query(Room.location).filter(Room.active == True).distinct().all()  # noqa: E712
        return sorted({r[0] for r in rows})
    finally:
        session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    n = seed()
    print(f"Seeded {n} room rows into {config.DB_PATH}")
    print("Locations:", ", ".join(all_locations()))
