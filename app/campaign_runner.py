"""
High-Volume Campaign Execution Engine — runs outreach campaigns.
Rate-limited to 50 calls/day. Time-slot scheduling. Retry with backoff.
Designed to work with the browser-based voice system.
"""

import logging
import time
import asyncio
from datetime import datetime, date, timedelta
from typing import Optional

from app.campaigns import (
    get_campaign, get_all_campaigns, update_campaign_status,
    get_next_contact, record_call_attempt,
)

logger = logging.getLogger(__name__)

# Rate limiting
_daily_call_count: dict[str, int] = {}  # date_str → count
MAX_CALLS_PER_DAY = 50
MIN_DELAY_BETWEEN_CALLS = 60  # seconds (1 minute minimum between calls)

# Campaign runner state
_runner_state = {
    "is_running": False,
    "current_campaign": None,
    "current_contact": None,
    "calls_today": 0,
    "last_call_time": None,
}


def get_runner_state() -> dict:
    """Get current campaign runner status."""
    today = date.today().isoformat()
    return {
        **_runner_state,
        "calls_today": _daily_call_count.get(today, 0),
        "max_calls_per_day": MAX_CALLS_PER_DAY,
        "can_make_call": can_make_call(),
    }


def can_make_call() -> bool:
    """Check if we're within rate limits."""
    today = date.today().isoformat()
    today_count = _daily_call_count.get(today, 0)
    if today_count >= MAX_CALLS_PER_DAY:
        return False

    # Check time since last call
    if _runner_state["last_call_time"]:
        elapsed = time.time() - _runner_state["last_call_time"]
        if elapsed < MIN_DELAY_BETWEEN_CALLS:
            return False

    return True


def increment_call_count():
    """Track a call was made."""
    today = date.today().isoformat()
    _daily_call_count[today] = _daily_call_count.get(today, 0) + 1
    _runner_state["calls_today"] = _daily_call_count[today]
    _runner_state["last_call_time"] = time.time()


def get_next_scheduled_call(campaign_id: str) -> dict | None:
    """
    Get the next contact to call in a campaign.
    Returns None if rate-limited or no pending contacts.
    """
    if not can_make_call():
        return {"error": "Rate limited. Max 50 calls/day.", "retry_after": MIN_DELAY_BETWEEN_CALLS}

    contact = get_next_contact(campaign_id)
    if not contact:
        return None

    _runner_state["current_campaign"] = campaign_id
    _runner_state["current_contact"] = contact["phone"]

    return {
        "campaign_id": campaign_id,
        "phone": contact["phone"],
        "attempt": contact["attempts"] + 1,
        "max_retries": contact["max_retries"],
    }


def complete_campaign_call(campaign_id: str, phone: str, call_id: str, success: bool):
    """Mark a campaign call as completed."""
    record_call_attempt(campaign_id, phone, call_id, success)
    increment_call_count()
    _runner_state["current_contact"] = None

    logger.info(f"Campaign call completed: {campaign_id}/{phone} success={success}")


def get_campaign_schedule() -> list[dict]:
    """Get all scheduled campaigns with their next run times."""
    campaigns = get_all_campaigns()
    schedule = []

    for c in campaigns:
        if c["status"] in ("scheduled", "running"):
            pending = [ct for ct in c["contacts"] if ct["status"] == "pending"]
            schedule.append({
                "campaign_id": c["campaign_id"],
                "name": c["name"],
                "status": c["status"],
                "scheduled_date": c["scheduled_date"],
                "scheduled_time": c["scheduled_time"],
                "pending_contacts": len(pending),
                "total_contacts": c["total_contacts"],
                "completed": c["completed_count"],
            })

    return schedule


def get_daily_stats() -> dict:
    """Get today's call stats."""
    today = date.today().isoformat()
    return {
        "date": today,
        "calls_made": _daily_call_count.get(today, 0),
        "calls_remaining": MAX_CALLS_PER_DAY - _daily_call_count.get(today, 0),
        "max_per_day": MAX_CALLS_PER_DAY,
    }
