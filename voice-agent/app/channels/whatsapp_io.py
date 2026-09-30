# -*- coding: utf-8 -*-
"""
WhatsApp outbound send + inbound payload parsing.

Send providers (first configured one wins):
  1. Meta WhatsApp Cloud API   — WHATSAPP_TOKEN + WHATSAPP_PHONE_ID
  2. Generic webhook to your bot — WHATSAPP_WEBHOOK_URL
  3. MOCK (default)             — logs the message; nothing leaves the machine

`parse_incoming(body)` accepts either a simple `{"from": "...", "text": "..."}`
shape or the Meta Cloud API webhook shape and returns `(phone, text)`.
"""

import logging
from datetime import datetime

from app import config

logger = logging.getLogger(__name__)

_sent_log: list[dict] = []


def normalize_phone(phone: str) -> str:
    """Ensure an Indian number carries its country code (default +91)."""
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def parse_incoming(body: dict) -> tuple[str, str]:
    """
    Extract (phone, text) from a webhook body. Supports:
      * simple:  {"from": "+91...", "text": "..."}  (or "message"/"body")
      * Meta:    entry[].changes[].value.messages[0].from / .text.body
    Returns ("", "") if nothing usable is found.
    """
    if not isinstance(body, dict):
        return "", ""

    # Simple shape.
    phone = body.get("from") or body.get("phone") or body.get("sender") or ""
    text = body.get("text") or body.get("message") or body.get("body") or ""
    if phone and text:
        return str(phone), str(text)

    # Meta Cloud API shape.
    try:
        entry = (body.get("entry") or [])[0]
        change = (entry.get("changes") or [])[0]
        value = change.get("value") or {}
        msg = (value.get("messages") or [])[0]
        phone = msg.get("from", "")
        text = (msg.get("text") or {}).get("body", "")
        if phone and text:
            return str(phone), str(text)
    except (IndexError, KeyError, TypeError, AttributeError):
        pass

    return str(phone or ""), str(text or "")


def send(to_phone: str, message: str) -> dict:
    """Send a WhatsApp message via the configured provider (or MOCK)."""
    to_phone = normalize_phone(to_phone)
    entry = {"to": to_phone, "message": message,
             "sent_at": datetime.now().isoformat(), "provider": None,
             "success": False}

    if config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_ID:
        result = _send_meta(to_phone, message)
    elif config.WHATSAPP_WEBHOOK_URL:
        result = _send_webhook(to_phone, message)
    else:
        logger.info(f"[WhatsApp MOCK] → {to_phone}:\n{message}\n")
        result = {"success": True, "provider": "mock", "error": None}

    entry.update(result)
    _sent_log.append(entry)
    return result


def _send_meta(to_phone: str, message: str) -> dict:
    try:
        import httpx
        url = f"https://graph.facebook.com/v18.0/{config.WHATSAPP_PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
                   "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": to_phone,
                   "type": "text", "text": {"body": message}}
        resp = httpx.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        return {"success": True, "provider": "meta", "error": None}
    except Exception as e:
        logger.error(f"[WhatsApp] Meta send failed: {e}")
        return {"success": False, "provider": "meta", "error": str(e)}


def _send_webhook(to_phone: str, message: str) -> dict:
    try:
        import httpx
        resp = httpx.post(config.WHATSAPP_WEBHOOK_URL,
                          json={"to": to_phone, "message": message}, timeout=15)
        resp.raise_for_status()
        return {"success": True, "provider": "webhook", "error": None}
    except Exception as e:
        logger.error(f"[WhatsApp] Webhook send failed: {e}")
        return {"success": False, "provider": "webhook", "error": str(e)}


def sent_log() -> list[dict]:
    return list(reversed(_sent_log))
