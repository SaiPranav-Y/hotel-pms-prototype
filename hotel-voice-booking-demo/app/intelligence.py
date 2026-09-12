"""
Conversation Intelligence — post-call analysis using Ollama.
Generates: summary, intent classification, sentiment, auto-tags.
Runs after each call ends to enrich the call log.
"""

import logging
import json
import re
import httpx
from typing import Optional

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def analyze_call(transcript: list[dict], gathered_info: dict = None) -> dict:
    """
    Run post-call intelligence on a completed transcript.
    Returns: summary, intent, sentiment, tags, key_entities.
    """
    if not transcript:
        return _empty_analysis()

    # Build transcript text
    text = "\n".join(f"{t['role']}: {t['text']}" for t in transcript)

    # Use Ollama for analysis
    prompt = f"""Analyze this phone call transcript. Return ONLY a JSON object with these fields:
- "summary": 1-2 sentence summary of what happened in the call
- "intent": one of ["booking", "inquiry", "cancellation", "complaint", "general"]
- "sentiment": one of ["positive", "neutral", "negative"]  
- "tags": list of 2-4 relevant tags (e.g., "srisailam", "ac_room", "family_trip", "2_rooms")
- "booking_completed": true or false
- "key_entities": object with any detected name, phone, location, dates

Transcript:
{text[:2000]}

Return ONLY valid JSON, nothing else."""

    try:
        client = httpx.Client(base_url=OLLAMA_BASE_URL, timeout=30.0)
        response = client.post(
            "/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 300},
            },
        )
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "")
        client.close()

        # Parse JSON from response
        analysis = _parse_json_response(content)
        if analysis:
            return analysis

    except Exception as e:
        logger.error(f"Intelligence analysis failed: {e}")

    # Fallback: rule-based analysis
    return _rule_based_analysis(transcript, gathered_info)


def _parse_json_response(content: str) -> dict | None:
    """Try to extract JSON from LLM response."""
    try:
        # Try direct parse
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in response
    match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None


def _rule_based_analysis(transcript: list[dict], gathered_info: dict = None) -> dict:
    """Fallback rule-based analysis when Ollama is unavailable."""
    full_text = " ".join(t["text"] for t in transcript).lower()
    info = gathered_info or {}

    # Intent detection
    intent = "general"
    if any(w in full_text for w in ["book", "reserve", "room", "stay"]):
        intent = "booking"
    elif any(w in full_text for w in ["cancel", "refund"]):
        intent = "cancellation"
    elif any(w in full_text for w in ["complaint", "problem", "issue", "bad"]):
        intent = "complaint"
    elif any(w in full_text for w in ["price", "available", "how much", "which"]):
        intent = "inquiry"

    # Sentiment
    sentiment = "neutral"
    positive_words = ["thank", "good", "great", "nice", "perfect", "wonderful"]
    negative_words = ["bad", "terrible", "worst", "angry", "upset", "complaint"]
    pos_count = sum(1 for w in positive_words if w in full_text)
    neg_count = sum(1 for w in negative_words if w in full_text)
    if pos_count > neg_count:
        sentiment = "positive"
    elif neg_count > pos_count:
        sentiment = "negative"

    # Tags
    tags = []
    if info.get("location"):
        tags.append(info["location"].lower())
    if info.get("room_type"):
        tags.append(info["room_type"])
    if "booking" in intent:
        tags.append("booking_attempt")
    if info.get("customer_name"):
        tags.append("identified_customer")

    # Summary
    summary = f"Call about {intent}."
    if info.get("location"):
        summary += f" Location: {info['location']}."
    if info.get("customer_name"):
        summary += f" Guest: {info['customer_name']}."

    return {
        "summary": summary,
        "intent": intent,
        "sentiment": sentiment,
        "tags": tags[:4],
        "booking_completed": bool(info.get("customer_name") and info.get("check_in")),
        "key_entities": {
            "name": info.get("customer_name"),
            "phone": info.get("customer_phone"),
            "location": info.get("location"),
        },
    }


def _empty_analysis() -> dict:
    return {
        "summary": "No transcript available.",
        "intent": "general",
        "sentiment": "neutral",
        "tags": [],
        "booking_completed": False,
        "key_entities": {},
    }
