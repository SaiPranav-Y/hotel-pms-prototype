"""
Human Escalation Workflow — escalate calls to human agents.
Supports up to 3 configurable escalation numbers.
Triggers on: keywords, explicit request, repeated failures, or manual.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Configurable escalation numbers (set via API or .env)
_escalation_config = {
    "numbers": [
        {"name": "Front Desk", "phone": "9133654248", "priority": 1},
        {"name": "Manager", "phone": "9490860245", "priority": 2},
        {"name": "Emergency", "phone": "9533335245", "priority": 3},
    ],
    "trigger_keywords": [
        "speak to someone", "human", "manager", "complaint",
        "not working", "emergency", "help me", "connect me",
        "real person", "transfer", "escalate",
    ],
    "max_ai_failures": 3,  # Escalate after N consecutive misunderstandings
}

# Escalation log
_escalation_log: list[dict] = []


def get_escalation_config() -> dict:
    """Get current escalation configuration."""
    return _escalation_config


def set_escalation_numbers(numbers: list[dict]) -> bool:
    """
    Set escalation numbers. Max 3.
    Each: {"name": "Label", "phone": "number", "priority": 1-3}
    """
    if len(numbers) > 3:
        return False
    _escalation_config["numbers"] = numbers[:3]
    return True


def set_trigger_keywords(keywords: list[str]) -> bool:
    """Set keywords that trigger escalation."""
    _escalation_config["trigger_keywords"] = keywords
    return True


def check_escalation_needed(user_text: str, failure_count: int = 0) -> dict:
    """
    Check if a call should be escalated based on user input and failure count.
    Returns: {"escalate": bool, "reason": str, "target": dict|None}
    """
    text_lower = user_text.lower()

    # Check keywords
    for keyword in _escalation_config["trigger_keywords"]:
        if keyword in text_lower:
            target = _escalation_config["numbers"][0] if _escalation_config["numbers"] else None
            return {
                "escalate": True,
                "reason": f"Keyword detected: '{keyword}'",
                "target": target,
            }

    # Check failure threshold
    if failure_count >= _escalation_config["max_ai_failures"]:
        target = _escalation_config["numbers"][0] if _escalation_config["numbers"] else None
        return {
            "escalate": True,
            "reason": f"AI failures exceeded threshold ({failure_count})",
            "target": target,
        }

    return {"escalate": False, "reason": None, "target": None}


def create_escalation(
    call_id: str,
    reason: str,
    target_number: dict = None,
    customer_phone: str = "",
    customer_name: str = "",
    transcript_summary: str = "",
) -> dict:
    """Log an escalation event."""
    escalation = {
        "id": f"ESC-{len(_escalation_log)+1:04d}",
        "call_id": call_id,
        "reason": reason,
        "target": target_number or _escalation_config["numbers"][0],
        "customer_phone": customer_phone,
        "customer_name": customer_name,
        "transcript_summary": transcript_summary,
        "status": "pending",  # pending | contacted | resolved
        "created_at": datetime.now().isoformat(),
        "resolved_at": None,
    }
    _escalation_log.append(escalation)
    logger.info(f"Escalation created: {escalation['id']} → {escalation['target'].get('name', '?')}")

    # Firebase sync
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("escalations").document(escalation["id"]).set(escalation)
    except Exception:
        pass

    return escalation


def resolve_escalation(escalation_id: str) -> bool:
    """Mark an escalation as resolved."""
    for esc in _escalation_log:
        if esc["id"] == escalation_id:
            esc["status"] = "resolved"
            esc["resolved_at"] = datetime.now().isoformat()
            return True
    return False


def get_all_escalations() -> list[dict]:
    return list(reversed(_escalation_log))


def get_pending_escalations() -> list[dict]:
    return [e for e in _escalation_log if e["status"] == "pending"]


def get_escalation_stats() -> dict:
    total = len(_escalation_log)
    pending = sum(1 for e in _escalation_log if e["status"] == "pending")
    resolved = sum(1 for e in _escalation_log if e["status"] == "resolved")
    return {"total": total, "pending": pending, "resolved": resolved}
