# Branch: `karivena-voice-ai`

**AI voice + WhatsApp booking engine for Karivena Satram pilgrim accommodation.**

This branch adds a self-hosted, Ollama-powered voice assistant ("Kaveri") and a
Twilio telephony gateway to the hotel-pms-prototype. Bookings sync to the same
Firebase `reservations` collection as the Flutter PMS and WhatsApp bot.

## What's in this branch

| Folder | Description |
|--------|-------------|
| `voice-ai/` | Python/FastAPI platform — browser voice calls, full dashboard, all business logic |
| `voice-gateway/` | Node.js/Express — Twilio phone-call gateway (STT → Ollama → TTS) |
| `STEERING.md` | Architecture + phased roadmap (all 5 phases complete) |

## Capabilities

- **Voice booking** in English/Telugu via browser or real phone (Twilio)
- **Gotram eligibility** — mandatory community check on every booking
- **Mandatory fields** — name, gotram, location, room type, stay span, phone
- **Razorpay payments** — fixed room amount, sent via WhatsApp
- **Donations** — flexible amount + 6 fixed seva plans (Annadanam, Nitya Pooja, etc.)
- **WhatsApp confirmation** — booking summary + payment link + donation option
- **10 locations, 360+ rooms** loaded from Excel
- **Campaigns** (50/day), **escalation** (3 numbers), **analytics**, **search**
- **Conversation intelligence** — auto summary/intent/sentiment/tags
- **90-day retention**, **PDF knowledge base** (50 pages)

## Suggested GitHub Branch Description (paste in repo settings)

> AI voice + WhatsApp booking engine (Kaveri) for Karivena Satram. Ollama LLM,
> Twilio telephony, Gotram eligibility, Razorpay payments + donations, Firebase
> PMS sync. 100% local LLM. 39 tests passing.

## Status: v3.0 — 39 automated tests passing
