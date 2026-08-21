# Karivena Satram — Kaveri AI Voice Caller

AI-powered voice booking assistant for pilgrim accommodation across 10 locations.

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

## Features

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

## Firebase Integration

Writes to `reservations` collection with `reservation_mode: "Voice Assistant"` — 
appears alongside WhatsApp and Walk-In bookings in the Flutter PMS dashboard.

## Project Structure

```
voice-ai/
├── app/
│   ├── main.py              # FastAPI server (28 routes)
│   ├── ai_engine.py         # Kaveri LLM brain (Ollama)
│   ├── knowledge_base.py    # Room inventory + booking logic
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
├── test_all.py              # Full test suite
├── parse_excel.py           # Excel → JSON parser
├── requirements.txt
└── .env.example
```

## Tests

```bash
py test_all.py
```

All 22 tests pass. 10/10 API endpoints verified.
