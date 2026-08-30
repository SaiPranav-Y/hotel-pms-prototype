"""
WhatsApp Message Composer + Dispatcher.

Composes the booking confirmation message with:
  - Warm greeting
  - Booking summary (name, city, room, dates, gotram)
  - Razorpay payment link (fixed room amount)
  - Donation option (flexible + seva plans)

Sends via your existing WhatsApp API. Configure the send integration in
send_whatsapp() — currently supports:
  - Meta WhatsApp Cloud API (set WHATSAPP_TOKEN + WHATSAPP_PHONE_ID)
  - Generic webhook (set WHATSAPP_WEBHOOK_URL)
  - MOCK mode (logs the message) if nothing configured
"""

import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

# Meta WhatsApp Cloud API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
# Generic webhook alternative (e.g., your existing bot)
WHATSAPP_WEBHOOK_URL = os.getenv("WHATSAPP_WEBHOOK_URL", "")

_sent_log: list[dict] = []


def compose_booking_message(booking: dict, payment_link: str, donation_link: str) -> str:
    """
    Compose a warm WhatsApp confirmation message with payment + donation links.
    """
    name = booking.get("customer_name", "Guest")
    location = booking.get("location", booking.get("temple_name", ""))
    room_type = booking.get("room_type", "")
    check_in = booking.get("check_in", "")
    check_out = booking.get("check_out", "")
    num_rooms = booking.get("num_rooms", booking.get("no_of_rooms", 1))
    gotram = booking.get("gotram", "")
    total = booking.get("total_price", 0)
    booking_id = booking.get("booking_id", "")

    msg = (
        f"🙏 Namaste {name}!\n\n"
        f"Your booking at *Karivena Satram, {location}* is confirmed.\n\n"
        f"📋 *Booking Details*\n"
        f"Booking ID: {booking_id}\n"
        f"Gotram: {gotram}\n"
        f"Room: {room_type} ({num_rooms} room(s))\n"
        f"Check-in: {check_in}\n"
        f"Check-out: {check_out}\n"
        f"Amount: ₹{total:,}\n\n"
        f"💳 *Complete your payment*\n{payment_link}\n\n"
        f"🙏 *Support the Satram*\n"
        f"Your generous donation helps us serve pilgrims. Donate any amount or choose a seva:\n{donation_link}\n\n"
        f"Please carry a valid ID at check-in. Check-in from 12 PM.\n"
        f"We look forward to welcoming you. Om Namah Shivaya 🕉️"
    )
    return msg


def compose_donation_only_message(name: str, donation_link: str) -> str:
    """Compose a standalone donation message."""
    return (
        f"🙏 Namaste {name}!\n\n"
        f"Thank you for your interest in supporting *Karivena Satram*.\n\n"
        f"Your contribution helps provide accommodation, Annadanam, and daily "
        f"sevas for pilgrims.\n\n"
        f"🙏 *Donate here* (any amount or choose a seva):\n{donation_link}\n\n"
        f"May you be blessed. Om Namah Shivaya 🕉️"
    )


def send_whatsapp(to_phone: str, message: str) -> dict:
    """
    Send a WhatsApp message via configured provider.
    Returns {"success": bool, "provider": str, "error": str|None}
    """
    to_phone = _normalize_phone(to_phone)

    # Log the attempt
    log_entry = {
        "to": to_phone,
        "message": message,
        "sent_at": datetime.now().isoformat(),
        "success": False,
        "provider": None,
    }

    # 1. Meta WhatsApp Cloud API
    if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
        result = _send_meta(to_phone, message)
        log_entry.update(result)
        _sent_log.append(log_entry)
        return result

    # 2. Generic webhook (your existing bot)
    if WHATSAPP_WEBHOOK_URL:
        result = _send_webhook(to_phone, message)
        log_entry.update(result)
        _sent_log.append(log_entry)
        return result

    # 3. MOCK mode
    logger.info(f"[WhatsApp MOCK] To {to_phone}:\n{message}\n")
    log_entry.update({"success": True, "provider": "mock"})
    _sent_log.append(log_entry)
    return {"success": True, "provider": "mock", "error": None}


def _send_meta(to_phone: str, message: str) -> dict:
    """Send via Meta WhatsApp Cloud API."""
    try:
        url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message},
        }
        resp = httpx.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        logger.info(f"[WhatsApp] Sent via Meta to {to_phone}")
        return {"success": True, "provider": "meta", "error": None}
    except Exception as e:
        logger.error(f"[WhatsApp] Meta send failed: {e}")
        return {"success": False, "provider": "meta", "error": str(e)}


def _send_webhook(to_phone: str, message: str) -> dict:
    """Send via a generic webhook to your existing WhatsApp bot."""
    try:
        resp = httpx.post(
            WHATSAPP_WEBHOOK_URL,
            json={"to": to_phone, "message": message},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f"[WhatsApp] Sent via webhook to {to_phone}")
        return {"success": True, "provider": "webhook", "error": None}
    except Exception as e:
        logger.error(f"[WhatsApp] Webhook send failed: {e}")
        return {"success": False, "provider": "webhook", "error": str(e)}


def _normalize_phone(phone: str) -> str:
    """Ensure phone has country code (default +91 for India)."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def get_sent_log() -> list[dict]:
    return list(reversed(_sent_log))
