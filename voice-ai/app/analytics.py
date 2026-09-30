"""
Analytics — date-wise call volume, duration insights, booking conversion.
Computes metrics from call logs stored in knowledge_base.
"""

import logging
from datetime import date, datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


def compute_analytics(call_logs: list[dict], bookings: list[dict]) -> dict:
    """
    Compute full analytics from call logs and bookings.
    Returns date-wise breakdown + aggregate metrics.
    """
    if not call_logs:
        return _empty_analytics()

    # Date-wise aggregation
    daily = defaultdict(lambda: {"calls": 0, "total_duration": 0, "bookings": 0, "escalations": 0})

    total_duration = 0
    total_calls = len(call_logs)
    statuses = defaultdict(int)

    for call in call_logs:
        call_date = call.get("date", "")
        if not call_date:
            # Try to extract from created_at
            created = call.get("created_at", call.get("start_time_readable", ""))
            if created:
                call_date = created[:10]  # YYYY-MM-DD
            else:
                call_date = date.today().isoformat()

        duration = call.get("duration_seconds", call.get("duration", 0))
        if isinstance(duration, float):
            duration = int(duration)

        daily[call_date]["calls"] += 1
        daily[call_date]["total_duration"] += duration
        total_duration += duration

        wf = call.get("workflow_status", "pending")
        statuses[wf] += 1

    # Bookings per date
    for booking in bookings:
        b_date = booking.get("created_at", "")[:10]
        if b_date:
            daily[b_date]["bookings"] += 1

    # Convert to sorted list
    daily_list = []
    for d in sorted(daily.keys(), reverse=True):
        entry = daily[d]
        avg_dur = entry["total_duration"] / entry["calls"] if entry["calls"] > 0 else 0
        daily_list.append({
            "date": d,
            "calls": entry["calls"],
            "total_duration_seconds": entry["total_duration"],
            "avg_duration_seconds": round(avg_dur),
            "bookings": entry["bookings"],
        })

    # Aggregate
    avg_duration = total_duration / total_calls if total_calls > 0 else 0
    conversion_rate = (len(bookings) / total_calls * 100) if total_calls > 0 else 0

    return {
        "summary": {
            "total_calls": total_calls,
            "total_duration_seconds": total_duration,
            "total_duration_minutes": round(total_duration / 60, 1),
            "avg_duration_seconds": round(avg_duration),
            "total_bookings": len(bookings),
            "conversion_rate_percent": round(conversion_rate, 1),
            "calls_pending": statuses.get("pending", 0),
            "calls_needs_review": statuses.get("needs_review", 0),
            "calls_completed": statuses.get("completed", 0),
        },
        "daily": daily_list,
        "last_updated": datetime.now().isoformat(),
    }


def compute_location_analytics(bookings: list[dict]) -> list[dict]:
    """Bookings breakdown by location."""
    by_location = defaultdict(int)
    for b in bookings:
        loc = b.get("location", b.get("temple_name", "Unknown"))
        by_location[loc] += 1
    return [{"location": k, "bookings": v} for k, v in sorted(by_location.items(), key=lambda x: -x[1])]


def compute_source_analytics(bookings: list[dict]) -> list[dict]:
    """Bookings breakdown by source (Voice Assistant, WhatsApp, Walk-In)."""
    by_source = defaultdict(int)
    for b in bookings:
        source = b.get("source", b.get("reservation_mode", "Unknown"))
        by_source[source] += 1
    return [{"source": k, "count": v} for k, v in sorted(by_source.items(), key=lambda x: -x[1])]


def _empty_analytics() -> dict:
    return {
        "summary": {
            "total_calls": 0,
            "total_duration_seconds": 0,
            "total_duration_minutes": 0,
            "avg_duration_seconds": 0,
            "total_bookings": 0,
            "conversion_rate_percent": 0,
            "calls_pending": 0,
            "calls_needs_review": 0,
            "calls_completed": 0,
        },
        "daily": [],
        "last_updated": datetime.now().isoformat(),
    }
