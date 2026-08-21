"""
AI Conversation Engine — Kaveri for Karivena Satram.
Handles pilgrim accommodation booking across 10 locations.
Supports Telugu responses via Ollama multilingual model.
"""

import json
import logging
import re
from datetime import date
import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from app.knowledge_base import (
    ORG_INFO,
    get_locations_summary,
    check_availability,
    create_booking,
    cancel_booking,
    get_booking,
    get_customer,
)

logger = logging.getLogger(__name__)

# --- SYSTEM PROMPT ---

SYSTEM_PROMPT = f"""You are Kaveri, a professional receptionist for Karivena Satram (Akhila Bharatheeya Brahmana Karivena Nityannadana Satram). You handle room bookings for pilgrims at temple locations across India. You are on a phone call.

IMPORTANT: If the caller speaks Telugu, respond in Telugu. If they speak English, respond in English. Match the caller's language.

RULES:
- Professional, polite, efficient. No filler.
- Keep EVERY response to 1-2 sentences MAX.
- Never use markdown, bullets, asterisks, or formatting.
- Never say "ji".
- Say prices naturally: "twelve hundred rupees per night"

LOCATIONS (with rooms):
{get_locations_summary()}

Check-in: {ORG_INFO['check_in_time']}, Check-out: {ORG_INFO['check_out_time']}
ID required at check-in. Free cancellation up to 24 hours before.

BOOKING FLOW — ask ONE question at a time:
1. Which location they want to stay at
2. Check-in and check-out dates
3. AC or Non-AC room
4. Number of rooms
5. Full name
6. Phone number
7. Age
8. Confirm and book

TOOLS — use this exact format:
TOOL_CALL: check_availability(location="name", room_type="ac|nonac", check_in="YYYY-MM-DD", check_out="YYYY-MM-DD", num_rooms=1)
TOOL_CALL: create_booking(customer_name="Name", customer_phone="Phone", location="name", room_type="ac|nonac", check_in="YYYY-MM-DD", check_out="YYYY-MM-DD", num_rooms=1, num_guests=1, customer_age="Age")
TOOL_CALL: cancel_booking(booking_id="BK-XXXXXXXX")

Today is {date.today().isoformat()}. Keep responses SHORT."""

# --- CACHED GREETING (instant) ---

CACHED_GREETING = "Namaste! Karivena Satram accommodations. This is Kaveri. How may I help you with your booking today?"


def _parse_tool_call(text: str) -> tuple[str, dict] | None:
    """Parse TOOL_CALL from AI response."""
    match = re.search(r'TOOL_CALL:\s*(\w+)\(([^)]*)\)', text)
    if not match:
        return None
    func_name = match.group(1)
    params_str = match.group(2)
    params = {}
    if params_str.strip():
        for pm in re.finditer(r'(\w+)=(?:"([^"]*)"|([\d]+))', params_str):
            key = pm.group(1)
            value = pm.group(2) if pm.group(2) is not None else int(pm.group(3))
            params[key] = value
    return func_name, params


def _execute_tool(func_name: str, params: dict) -> str:
    """Execute a tool call."""
    try:
        if func_name == "check_availability":
            result = check_availability(
                location=params.get("location", "srisailam"),
                room_type=params.get("room_type", "ac"),
                check_in=date.fromisoformat(params["check_in"]) if params.get("check_in") else None,
                check_out=date.fromisoformat(params["check_out"]) if params.get("check_out") else None,
                num_rooms=int(params.get("num_rooms", 1)),
            )
        elif func_name == "create_booking":
            result = create_booking(
                customer_name=params.get("customer_name", ""),
                customer_phone=params.get("customer_phone", ""),
                location=params.get("location", "srisailam"),
                room_type=params.get("room_type", "ac"),
                check_in=date.fromisoformat(params["check_in"]) if params.get("check_in") else None,
                check_out=date.fromisoformat(params["check_out"]) if params.get("check_out") else None,
                num_rooms=int(params.get("num_rooms", 1)),
                num_guests=int(params.get("num_guests", 1)),
                customer_age=params.get("customer_age", ""),
            )
        elif func_name == "cancel_booking":
            result = cancel_booking(params.get("booking_id", ""))
        else:
            result = {"error": f"Unknown tool: {func_name}"}
        return json.dumps(result)
    except Exception as e:
        logger.error(f"Tool error ({func_name}): {e}")
        return json.dumps({"error": str(e)})


class ConversationEngine:
    """Manages one call conversation. Optimized for speed."""

    def __init__(self):
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self.client = httpx.Client(base_url=OLLAMA_BASE_URL, timeout=30.0)
        self.gathered_info: dict = {}

    def _call_ollama(self, messages: list[dict]) -> str:
        """Call Ollama with speed-optimized settings."""
        try:
            response = self.client.post(
                "/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 100,
                        "num_ctx": 2048,
                        "top_p": 0.8,
                        "repeat_penalty": 1.1,
                    },
                },
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama.")
            return "I apologize, please hold for a moment."
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return "Could you please repeat that?"

    def get_greeting(self) -> str:
        """Instant cached greeting."""
        self.messages.append({"role": "assistant", "content": CACHED_GREETING})
        return CACHED_GREETING

    def process_input(self, user_text: str) -> str:
        """Process guest speech, return response."""
        if not user_text.strip():
            return ""

        # === PRE-PROCESSING: Normalize + Vernacular enrichment ===
        from app.normalizer import normalize_query
        normalized = normalize_query(user_text)
        enriched_text = normalized["normalized_text"]

        # Merge extracted entities into gathered_info
        for key, val in normalized.get("extracted", {}).items():
            if val:
                self.gathered_info[key] = val

        # === ESCALATION CHECK ===
        from app.escalation import check_escalation_needed
        esc = check_escalation_needed(user_text)
        if esc["escalate"]:
            self.gathered_info["_escalation_triggered"] = True
            self.gathered_info["_escalation_reason"] = esc["reason"]
            self.messages.append({"role": "user", "content": user_text})
            response = "I understand. Let me connect you to our team who can help you better. Please hold for a moment."
            self.messages.append({"role": "assistant", "content": response})
            return response

        # === KNOWLEDGE BASE GUARDRAIL ===
        from app.kb_ingestion import search_knowledge_base
        kb_context = ""
        kb_results = search_knowledge_base(user_text, top_k=2)
        if kb_results:
            kb_context = "\n[KNOWLEDGE BASE CONTEXT: " + " | ".join(r["text"][:200] for r in kb_results) + "]"

        # === LLM CALL ===
        self.messages.append({"role": "user", "content": enriched_text + kb_context})
        response = self._call_ollama(self.messages)

        # Handle tool calls (max 2)
        attempts = 0
        while "TOOL_CALL:" in response and attempts < 2:
            attempts += 1
            tool_result = _parse_tool_call(response)
            if tool_result:
                func_name, params = tool_result
                logger.info(f"Tool: {func_name}({params})")
                if func_name == "create_booking":
                    self.gathered_info.update(params)
                result = _execute_tool(func_name, params)
                logger.info(f"Result: {result}")
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append({
                    "role": "user",
                    "content": f"[TOOL_RESULT: {result}] Respond in 1-2 sentences."
                })
                response = self._call_ollama(self.messages)
            else:
                break

        response = self._clean(response)
        self.messages.append({"role": "assistant", "content": response})
        self._extract_info(user_text)
        return response

    def _extract_info(self, text: str):
        """Auto-extract customer details from speech."""
        # Phone number
        phone_match = re.search(r'\b(\d{10})\b', text)
        if phone_match:
            self.gathered_info["customer_phone"] = phone_match.group(1)

        # Age
        age_match = re.search(r'\b(\d{1,2})\s*(years?|yrs?)\b', text.lower())
        if age_match:
            self.gathered_info["customer_age"] = age_match.group(1)

        # Location detection
        locations = ["srisailam", "tirupati", "tirupathi", "shirdi", "shiridi",
                     "kasi", "mahanandi", "rameswaram", "brundavanam",
                     "naimisaranyam", "arunachalam", "vruddasramam"]
        for loc in locations:
            if loc in text.lower():
                self.gathered_info["location"] = loc
                break

    def get_gathered_info(self) -> dict:
        return self.gathered_info

    def _clean(self, text: str) -> str:
        """Strip formatting."""
        text = re.sub(r'TOOL_CALL:.*', '', text)
        text = text.replace('**', '').replace('*', '').replace('#', '')
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\bji\b', '', text, flags=re.IGNORECASE).strip()
        text = re.sub(r'\s{2,}', ' ', text)
        return text
