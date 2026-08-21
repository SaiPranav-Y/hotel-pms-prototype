"""
Campaign Scheduling — outreach campaigns with configurable date, time, retry logic.
Supports up to 50 customers per campaign. Tracks attempt count and status per contact.
"""

import logging
import uuid
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory store
_campaigns: dict[str, dict] = {}

CAMPAIGN_STATUSES = ["draft", "scheduled", "running", "paused", "completed"]
CONTACT_STATUSES = ["pending", "in_progress", "completed", "failed", "skipped"]


def create_campaign(
    name: str,
    contacts: list[str],  # List of phone numbers
    scheduled_date: str = "",
    scheduled_time: str = "",
    max_retries: int = 3,
    message_template: str = "",
    notes: str = "",
) -> dict:
    """
    Create a new outreach campaign.
    Max 50 contacts per campaign. Configurable retry attempts.
    """
    campaign_id = f"CMP-{uuid.uuid4().hex[:6].upper()}"

    # Cap at 50 contacts
    contacts = contacts[:50]

    # Build contact queue with status tracking
    contact_queue = []
    for phone in contacts:
        contact_queue.append({
            "phone": phone,
            "status": "pending",
            "attempts": 0,
            "max_retries": max_retries,
            "last_attempt": None,
            "call_id": None,
            "result": None,
        })

    campaign = {
        "campaign_id": campaign_id,
        "name": name,
        "status": "draft",
        "scheduled_date": scheduled_date or date.today().isoformat(),
        "scheduled_time": scheduled_time or "09:00",
        "max_retries": max_retries,
        "message_template": message_template,
        "notes": notes,
        "contacts": contact_queue,
        "total_contacts": len(contact_queue),
        "completed_count": 0,
        "failed_count": 0,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }

    _campaigns[campaign_id] = campaign
    logger.info(f"Campaign created: {campaign_id} ({len(contact_queue)} contacts)")

    # Sync to Firebase
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("campaigns").document(campaign_id).set(campaign)
    except Exception:
        pass

    return campaign


def get_campaign(campaign_id: str) -> dict | None:
    return _campaigns.get(campaign_id)


def get_all_campaigns() -> list[dict]:
    campaigns = list(_campaigns.values())
    campaigns.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return campaigns


def update_campaign_status(campaign_id: str, status: str) -> bool:
    """Update campaign status: draft, scheduled, running, paused, completed."""
    if campaign_id not in _campaigns:
        return False
    if status not in CAMPAIGN_STATUSES:
        return False
    _campaigns[campaign_id]["status"] = status
    _campaigns[campaign_id]["updated_at"] = datetime.now().isoformat()
    return True


def record_call_attempt(campaign_id: str, phone: str, call_id: str, success: bool) -> bool:
    """Record a call attempt for a contact in a campaign."""
    if campaign_id not in _campaigns:
        return False

    campaign = _campaigns[campaign_id]
    for contact in campaign["contacts"]:
        if contact["phone"] == phone:
            contact["attempts"] += 1
            contact["last_attempt"] = datetime.now().isoformat()
            contact["call_id"] = call_id

            if success:
                contact["status"] = "completed"
                contact["result"] = "success"
                campaign["completed_count"] += 1
            elif contact["attempts"] >= contact["max_retries"]:
                contact["status"] = "failed"
                contact["result"] = "max_retries_reached"
                campaign["failed_count"] += 1
            else:
                contact["status"] = "pending"  # Will retry
                contact["result"] = "retry_scheduled"

            campaign["updated_at"] = datetime.now().isoformat()

            # Check if campaign is done
            pending = [c for c in campaign["contacts"] if c["status"] == "pending"]
            if not pending:
                campaign["status"] = "completed"

            return True
    return False


def get_next_contact(campaign_id: str) -> dict | None:
    """Get the next pending contact to call in a campaign."""
    if campaign_id not in _campaigns:
        return None
    campaign = _campaigns[campaign_id]
    for contact in campaign["contacts"]:
        if contact["status"] == "pending":
            return contact
    return None


def get_campaign_stats() -> dict:
    """Get aggregate campaign statistics."""
    total = len(_campaigns)
    running = sum(1 for c in _campaigns.values() if c["status"] == "running")
    scheduled = sum(1 for c in _campaigns.values() if c["status"] == "scheduled")
    completed = sum(1 for c in _campaigns.values() if c["status"] == "completed")
    return {
        "total_campaigns": total,
        "running": running,
        "scheduled": scheduled,
        "completed": completed,
    }
