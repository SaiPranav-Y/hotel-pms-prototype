"""
Keyword Search — find customers/calls by conversation context, location, or any term.
Searches across: transcripts, customer names, phone numbers, locations, notes, tags.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def search_transcripts(call_logs: list[dict], query: str) -> list[dict]:
    """
    Search call transcripts for a keyword/phrase.
    Returns matching calls with highlighted context.
    """
    query_lower = query.lower()
    results = []

    for call in call_logs:
        transcript = call.get("transcript", [])
        matches = []

        for entry in transcript:
            text = entry.get("text", "")
            if query_lower in text.lower():
                matches.append({
                    "role": entry.get("role", ""),
                    "text": text,
                    "match": _highlight_match(text, query),
                })

        if matches:
            results.append({
                "call_id": call.get("call_id", ""),
                "date": call.get("date", call.get("created_at", "")[:10]),
                "customer_name": call.get("gathered_info", {}).get("customer_name", "Unknown"),
                "customer_phone": call.get("gathered_info", {}).get("customer_phone", ""),
                "workflow_status": call.get("workflow_status", ""),
                "matches": matches,
                "match_count": len(matches),
            })

    # Sort by match count (most relevant first)
    results.sort(key=lambda r: r["match_count"], reverse=True)
    return results


def search_contacts(contacts: list[dict], query: str) -> list[dict]:
    """Search contacts by name, phone, location, tags."""
    query_lower = query.lower()
    results = []

    for c in contacts:
        score = 0
        if query_lower in c.get("name", "").lower():
            score += 3
        if query_lower in c.get("phone", ""):
            score += 3
        if any(query_lower in loc.lower() for loc in c.get("preferred_locations", [])):
            score += 2
        if any(query_lower in tag.lower() for tag in c.get("tags", [])):
            score += 2
        # Search notes
        for note in c.get("notes", []):
            if query_lower in note.get("text", "").lower():
                score += 1

        if score > 0:
            results.append({**c, "_search_score": score})

    results.sort(key=lambda r: r["_search_score"], reverse=True)
    return results


def global_search(call_logs: list[dict], contacts: list[dict], query: str) -> dict:
    """
    Global search across all data.
    Returns categorized results: calls, contacts.
    """
    return {
        "query": query,
        "calls": search_transcripts(call_logs, query),
        "contacts": search_contacts(contacts, query),
        "total_results": 0,  # Updated below
    }


def _highlight_match(text: str, query: str) -> str:
    """Create a text snippet showing the match in context."""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:100]

    start = max(0, idx - 40)
    end = min(len(text), idx + len(query) + 40)
    snippet = text[start:end]

    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet
