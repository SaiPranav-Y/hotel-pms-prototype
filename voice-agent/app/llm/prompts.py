# -*- coding: utf-8 -*-
"""Prompts + JSON schema for the Telugu NLU (steering §8)."""

# System prompt is in ENGLISH (for the model); the user's utterance is Telugu.
NLU_SYSTEM = """You are the language-understanding module of a Telugu hotel-booking phone assistant.
The user's utterance is in Telugu (it may include English words like "room", "AC", "check-in", "booking").
Extract the caller's INTENT and any booking DETAILS (slots).

Output JSON ONLY, matching the given schema. Rules:
- If a value is NOT stated, omit it (leave it null). NEVER guess names, dates, numbers, or prices.
- Do NOT do date arithmetic. Copy any date/day expression VERBATIM into check_in_date
  (e.g. "రేపు", "ఎల్లుండి", "వచ్చే శుక్రవారం", "2026-10-12"); the application resolves it.
- room_type: use "AC" or "Non-AC" if clearly stated, else null.
- num_guests and nights: integers only if clearly stated.
- intent must be one of: book_room, check_availability, cancel_booking, booking_status,
  ask_price, ask_facilities, talk_to_human, goodbye, unknown.
- confidence: 0.0-1.0, your certainty about the intent.
Return ONLY the JSON object, no prose, no markdown."""

# JSON schema passed to Ollama's `format` for structured output.
NLU_FORMAT = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "slots": {
            "type": "object",
            "properties": {
                "location": {"type": ["string", "null"]},
                "check_in_date": {"type": ["string", "null"]},
                "check_out_date": {"type": ["string", "null"]},
                "nights": {"type": ["integer", "null"]},
                "num_guests": {"type": ["integer", "null"]},
                "room_type": {"type": ["string", "null"]},
                "guest_name": {"type": ["string", "null"]},
                "callback_number": {"type": ["string", "null"]},
                "booking_id": {"type": ["string", "null"]},
            },
        },
        "confidence": {"type": "number"},
    },
    "required": ["intent"],
}


def build_nlu_messages(user_text: str, context: dict) -> list[dict]:
    """Compose the chat messages. Keep context tiny (state + known slots)."""
    state = context.get("state", "")
    known = context.get("known_slots", {})
    locations = context.get("locations", [])
    ctx_lines = []
    if state:
        ctx_lines.append(f"Current dialogue state: {state}")
    if known:
        ctx_lines.append(f"Already-collected slots: {known}")
    if locations:
        ctx_lines.append(f"Valid locations: {', '.join(locations)}")
    ctx = ("\n".join(ctx_lines) + "\n\n") if ctx_lines else ""

    return [
        {"role": "system", "content": NLU_SYSTEM},
        {"role": "user", "content": f"{ctx}Caller said (Telugu): {user_text}"},
    ]


# Free-form Telugu reply (FAQ only) — used sparingly.
REPHRASE_SYSTEM = """Reply ONLY in polite, simple spoken Telugu using Telugu script.
Maximum two short sentences. Use the 'మీరు' polite form. Use ONLY the facts provided.
Do not add any English or Hindi words. Do not invent facts."""
