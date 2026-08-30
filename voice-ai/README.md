# Karivena Satram — Kaveri AI Voice Caller

AI-powered voice + WhatsApp booking assistant for pilgrim accommodation across
10 locations, with community (Gotram) eligibility, Razorpay payments, and donations.

## Quick Start

```bash
cd voice-ai
pip install -r requirements.txt
py start.py
```

Opens http://localhost:8000 automatically.

## Requirements

- Python 3.9+
- Ollama (https://ollama.com/download) with `ollama pull llama3.2`
- Chrome or Edge browser
- Firebase service account key (as `firebase-key.json`)
- (Optional) Razorpay keys for live payments
- (Optional) WhatsApp Business API for message dispatch

## Core Features

- 10 pilgrimage locations (Srisailam, Tirupathi, Kasi, Shirdi, Rameswaram, etc.)
- 360+ rooms from Excel knowledge base
- Telugu vernacular dictionary (53 locations, 62 terms)
- Call workflow management (Pending → Needs Review → Completed)
- Campaign scheduling (50 calls/day, 3 retries)
- Human escalation (3 configurable numbers)
- Analytics dashboard (date-wise volume, conversion rate)
- Keyword search across all transcripts
- PDF knowledge base ingestion (50 pages)
- 90-day data retention policy
- Conversation intelligence (auto-summary, intent, sentiment, tags)
- Full Firebase sync to `hotel-pms-prototype` Firestore

## Community, Payments & Donations (v3.0)

### Gotram Eligibility (mandatory)
This satram serves a specific Hindu community. Every reservation and booking
**requires an approved Gotram**. The system:
- Loads the approved list from `app/allowed_gotrams.json` (or Firestore `allowed_gotrams`)
- Fuzzy-matches spoken/typed gotrams (case, spacing, and "gotram" suffix insensitive)
- Rejects bookings from gotrams not in the approved community list
- **Replace `app/allowed_gotrams.json` with your finalized gotram list.**

### Razorpay Payments (room — fixed amount)
On booking, a Razorpay payment link for the exact room total is generated and
sent to the guest via WhatsApp. Set live keys in `.env`:
```
RAZORPAY_KEY_ID=rzp_live_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
```
Without keys, runs in MOCK mode (demo links) so the full pipeline still works.

### Donations (flexible + seva plans)
- **Flexible**: donate any amount
- **Fixed seva plans**: Annadanam (₹1116), Nitya Pooja (₹516), Deeparadhana (₹251),
  Special Seva (₹2116), Gau Seva (₹1008), Vidya Danam (₹5001)
- Donation links can be sent standalone or included in the booking WhatsApp message

### WhatsApp Confirmation
Every booking triggers a warm WhatsApp message containing:
- Booking summary (name, gotram, location, room, dates, amount)
- Razorpay payment link
- Donation option (flexible + seva)

Configure your provider in `.env`:
```
# Meta WhatsApp Cloud API
WHATSAPP_TOKEN=xxxxx
WHATSAPP_PHONE_ID=xxxxx
# OR route to your existing bot
WHATSAPP_WEBHOOK_URL=https://your-bot/webhook
```
Without config, runs in MOCK mode (logs the message).

## Mandatory Booking Fields

Every booking (voice, WhatsApp, or web) validates:
1. **Name**
2. **Gotram** (must be in approved community list)
3. **Location** (city / temple)
4. **Room type** (AC / Non-AC)
5. **Span of stay** (check-in + check-out)
6. **Phone** (for WhatsApp + payment)

## Firebase Integration

Writes to `reservations` collection with `reservation_mode: "Voice Assistant"` —
appears alongside WhatsApp and Walk-In bookings in the Flutter PMS dashboard.
New fields synced: `gotram`, `total_price`, `payment_status`, `payment_link`, `donation_link`.

## API Endpoints (35+)

| Group | Routes |
|-------|--------|
| Voice | `WS /voice` |
| Bookings | `GET /api/bookings` |
| Calls | `GET /api/calls`, `POST /api/calls/{id}/workflow` |
| Gotrams | `GET/POST /api/gotrams`, `GET /api/gotrams/check` |
| Payments | `GET /api/payments`, `POST /api/payments/room`, `POST /api/payments/{id}/paid` |
| Donations | `GET /api/donations/sevas`, `POST /api/donations` |
| WhatsApp | `GET /api/whatsapp/log` |
| Contacts | `GET/POST /api/contacts`, notes, status |
| Campaigns | `GET/POST /api/campaigns` |
| Escalation | `GET /api/escalations`, config, resolve |
| Analytics | `GET /api/analytics` |
| Search | `GET /api/search?q=` |

## Project Structure

```
voice-ai/
├── app/
│   ├── main.py              # FastAPI server (35+ routes)
│   ├── ai_engine.py         # Kaveri LLM brain (Ollama) — gotram-aware
│   ├── knowledge_base.py    # Room inventory + booking (mandatory fields)
│   ├── gotram.py            # Community eligibility validation
│   ├── payments.py          # Razorpay room + donation links
│   ├── whatsapp.py          # Message composer + dispatcher
│   ├── allowed_gotrams.json # Approved gotram list (REPLACE with yours)
│   ├── call_handler.py      # WebSocket voice handler
│   ├── vernacular.py        # Telugu dictionary
│   ├── normalizer.py        # Query pre-processing
│   ├── pronunciation.py     # TTS pronunciation rules
│   ├── kb_ingestion.py      # PDF knowledge base
│   ├── intelligence.py      # Post-call analysis
│   ├── contacts.py          # Customer profiles
│   ├── campaigns.py         # Campaign scheduling
│   ├── campaign_runner.py   # Rate-limited execution
│   ├── escalation.py        # Human handoff
│   ├── analytics.py         # Call volume metrics
│   ├── search.py            # Full-text search
│   ├── retention.py         # 90-day cleanup
│   ├── firebase_store.py    # Firestore sync
│   ├── recorder.py          # Call recording
│   ├── local_tts.py         # Edge-TTS (Indian English)
│   ├── local_stt.py         # Browser STT fallback
│   └── pages/               # HTML dashboards
├── recordings/              # Saved call audio
├── start.py                 # One-click launcher
├── test_all.py              # Core test suite (27 tests)
├── test_phase5.py           # Gotram/payments/donations tests (12 tests)
├── parse_excel.py           # Excel → JSON parser
├── requirements.txt
└── .env.example
```

## Tests

```bash
py test_all.py      # 27 core tests
py test_phase5.py   # 12 gotram/payment/donation/WhatsApp tests
```

All 39 tests pass.
