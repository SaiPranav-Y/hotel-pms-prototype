"""
Audit trail — append-only log of who changed what and when.

Every create / update / delete / status-change on a reservation (and other
sensitive entities) writes an immutable entry to the Firestore `audit_logs`
collection. The Firestore security rules make this collection append-only
(create allowed, update/delete forbidden).

Entry schema:
  {
    "entity_type": "reservation",
    "entity_id":   "<booking id or doc id>",
    "action":      "create" | "update" | "delete" | "status_change" | "cancel",
    "actor":       "<user email or system channel>",   # who
    "actor_role":  "<role or 'system'>",
    "source":      "walk_in" | "voice_ai" | "whatsapp" | "system",
    "previous_state": { ... } | None,                  # what it was
    "new_state":      { ... } | None,                  # what it became
    "timestamp":   ISO8601,
    "notes":       "<optional>"
  }
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory ring buffer so audit works even without Firebase (and for tests).
_recent: list[dict] = []
_MAX_RECENT = 500


def log_event(
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str = "system",
    actor_role: str = "system",
    source: str = "system",
    previous_state: dict | None = None,
    new_state: dict | None = None,
    notes: str = "",
) -> dict:
    """Record an audit entry. Never raises — auditing must not block the action."""
    entry = {
        "entity_type": entity_type,
        "entity_id": str(entity_id or ""),
        "action": action,
        "actor": actor or "system",
        "actor_role": actor_role or "system",
        "source": source or "system",
        "previous_state": _clean(previous_state),
        "new_state": _clean(new_state),
        "timestamp": datetime.now().isoformat(),
        "notes": notes or "",
    }

    _recent.append(entry)
    if len(_recent) > _MAX_RECENT:
        del _recent[: len(_recent) - _MAX_RECENT]

    # Persist to Firestore (best effort)
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("audit_logs").add(entry)
    except Exception as e:
        logger.debug(f"Audit persist skipped: {e}")

    logger.info(f"[AUDIT] {action} {entity_type}:{entity_id} by {actor} ({source})")
    return entry


def get_recent(limit: int = 100, entity_id: str = "") -> list[dict]:
    """Return recent audit entries (newest first), optionally for one entity."""
    items = _recent
    if entity_id:
        items = [e for e in items if e["entity_id"] == entity_id]
    return list(reversed(items))[:limit]


def _clean(state: dict | None) -> dict | None:
    """Strip large / sensitive fields from a state snapshot before logging."""
    if not state:
        return None
    drop = {"password_hash", "transcript", "payment_link", "donation_link"}
    return {k: v for k, v in state.items() if k not in drop}
