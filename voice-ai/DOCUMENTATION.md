# Hotel Voice Booking Demo — Kaveri AI Receptionist

## Complete Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation & Setup](#installation--setup)
4. [How to Run](#how-to-run)
5. [Features](#features)
6. [Architecture](#architecture)
7. [Rules & Behavior](#rules--behavior)
8. [Limitations](#limitations)
9. [How to Add Features](#how-to-add-features)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)
12. [Project Structure](#project-structure)

---

## Overview

This is a **100% free, locally-running** AI voice receptionist demo for hotel bookings. The agent is named **Kaveri** — she speaks English with a warm Indian style, greets guests with "Namaste", and patiently gathers all booking details through natural conversation.

**What it does:**
- Guest opens a browser page and clicks "Call"
- Kaveri greets them warmly in Indian English style
- She asks questions one at a time: name, phone, city, dates, room preference, age
- She checks availability, quotes pricing, and confirms the booking
- The entire call is recorded and available for playback on the dashboard
- All gathered data appears as columns on a live dashboard

**Cost: $0** — Everything runs on your machine. No API keys, no subscriptions.

---

## Prerequisites

### Required Software

| Software | Version | Purpose | Download |
|----------|---------|---------|----------|
| Python | 3.9+ | Backend server | https://www.python.org/downloads/ |
| Ollama | Latest | Local AI engine (the brain) | https://ollama.com/download |
| Chrome or Edge | Latest | Browser with Speech API support | Already installed |
| Microphone | Any | For voice input | Hardware |

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4 GB free | 8 GB free |
| Disk | 3 GB free | 5 GB free |
| CPU | 4 cores | 8 cores |
| GPU | Not required | NVIDIA GPU (faster AI responses) |
| Internet | Required for first setup only | Required for Edge-TTS voice |

### Python Packages (auto-installed)

- fastapi — Web server
- uvicorn — ASGI server
- websockets — Real-time communication
- httpx — HTTP client for Ollama
- edge-tts — Free text-to-speech (Indian English voice)
- ollama — Ollama Python client
- python-dotenv — Environment config
- pydantic — Data validation
- jinja2 — Template engine

---

## Installation & Setup

### Step 1: Install Ollama

**Windows:**
```
winget install Ollama.Ollama
```
Or download from https://ollama.com/download and run the installer.

**Mac:**
```
brew install ollama
```

**Linux:**
```
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull the AI Model

Open a terminal and run:
```
ollama pull llama3.2
```
This downloads the 2GB model (one-time download).

### Step 3: Install Python Dependencies

```
cd hotel-voice-booking-demo
py -m pip install fastapi uvicorn[standard] websockets python-dotenv pydantic httpx jinja2 edge-tts ollama
```

### Step 4: Verify Setup

```
ollama --version
py -c "import fastapi, edge_tts, ollama; print('All packages OK')"
```

---

## How to Run

### Quick Start (3 commands)

```bash
# Terminal 1: Start Ollama (if not already running)
ollama serve

# Terminal 2: Start the demo server
cd hotel-voice-booking-demo
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Then open in your browser:

| Page | URL | Description |
|------|-----|-------------|
| Voice Call | http://localhost:8000 | Talk to Kaveri |
| Dashboard | http://localhost:8000/dashboard | View calls, bookings, recordings |
| API Docs | http://localhost:8000/docs | Interactive API documentation |

### Using the Voice Call

1. Open http://localhost:8000 in **Chrome** or **Edge**
2. Click the green phone button
3. Allow microphone access when prompted
4. Wait for Kaveri's "Namaste" greeting
5. Speak naturally: "I'd like to book a room for this weekend"
6. Kaveri will ask follow-up questions one by one
7. When done, click the red button to end the call
8. The recording is automatically saved

### Using the Dashboard

1. Open http://localhost:8000/dashboard
2. The page auto-refreshes every 3 seconds
3. **Call Activity table** shows all call details and gathered info
4. Click **"Play"** to listen to any call recording
5. Click **"View"** to read the full transcript
6. **Bookings table** shows confirmed reservations

### One-Click Start (Windows)

Double-click `setup_and_run.bat` — it checks everything and starts the server automatically.

---

## Features

### Kaveri AI Agent

| Feature | Description |
|---------|-------------|
| Indian personality | Greets with "Namaste", uses "ji", "bilkul", respectful tone |
| Indian English TTS | Uses Microsoft's `en-IN-NeerjaNeural` voice |
| Patient questioning | Asks one question at a time, never rushes |
| Smart data gathering | Collects: name, phone, city, age, dates, room type, guests |
| Availability checking | Real-time room availability lookup |
| Pricing | Quotes prices in natural Indian English |
| Booking confirmation | Summarizes details before confirming |
| Error recovery | Politely asks to repeat if unclear |

### Information Gathered Per Call

Kaveri attempts to collect all of the following during each call:

1. **Guest Name** — Full name for booking
2. **Phone Number** — Contact number
3. **City** — Where they want to stay
4. **Age** — Primary guest age (for records)
5. **Check-in Date** — Arrival date
6. **Check-out Date** — Departure date (or number of nights)
7. **Number of Guests** — How many people
8. **Room Type** — Standard / Deluxe / Suite (or helps them choose)
9. **Special Requirements** — Breakfast, airport pickup, etc.

### Dashboard

| Feature | Description |
|---------|-------------|
| Live call tracking | See active and completed calls |
| Guest detail columns | Name, phone, city, age, dates, room — all in table view |
| Recording playback | Click "Play" to listen to any past call |
| Transcript viewer | Click "View" to read the full conversation |
| Booking history | All confirmed bookings with full details |
| Revenue tracking | Total revenue from confirmed bookings |
| Auto-refresh | Updates every 3 seconds |

### Audio Recording

| Feature | Description |
|---------|-------------|
| Full call recording | Records entire call (both sides via browser mic) |
| Automatic save | Recording saved when call ends |
| Playback on dashboard | Play button next to each call |
| File storage | WebM files stored in `/recordings` directory |
| Persistent | Recordings survive server restarts (files on disk) |

### Room Types

| Room | Price/Night | Max Guests | Highlights |
|------|-------------|------------|------------|
| Standard | INR 3,500 | 2 | City view, Wi-Fi, tea/coffee maker |
| Deluxe | INR 5,500 | 3 | Lake view, minibar, premium toiletries |
| Executive Suite | INR 9,500 | 4 | Panoramic view, jacuzzi, butler service |

### Add-ons

| Add-on | Price | Per |
|--------|-------|-----|
| Breakfast Buffet | INR 800 | per person/day |
| Airport Pickup | INR 1,500 | one-time |
| Airport Drop | INR 1,500 | one-time |
| Spa Package | INR 2,500 | per person |
| Late Checkout | INR 1,000 | one-time |
| Extra Bed | INR 1,500 | per night |

---

## Architecture

```
Browser (Chrome/Edge)
    │
    ├── Web Speech API (STT) ─── speech → text
    ├── MediaRecorder ─────────── records full call audio
    │
    └── WebSocket (/voice)
            │
            ▼
    FastAPI Server (Python)
        │
        ├── call_handler.py ──── manages call session
        ├── ai_engine.py ─────── Kaveri's brain (Ollama + tools)
        ├── local_tts.py ─────── Edge-TTS (Indian English voice)
        ├── hotel_data.py ────── rooms, pricing, bookings (in-memory)
        └── recorder.py ──────── saves audio files to /recordings
            │
            ▼
    Ollama (localhost:11434)
        │
        └── llama3.2 model ──── generates Kaveri's responses
```

### Data Flow (per utterance)

1. Guest speaks → browser's Web Speech API transcribes to text
2. Text sent via WebSocket to server
3. Server sends text to Ollama (with conversation history + tools)
4. Ollama generates Kaveri's response (may call booking tools)
5. Response text sent to Edge-TTS → audio generated
6. Audio sent back via WebSocket → browser plays it
7. Browser resumes listening for next utterance

---

## Rules & Behavior

### Kaveri's Conversation Rules

1. **Always greets with "Namaste"** — first thing every caller hears
2. **One question at a time** — never asks multiple things at once
3. **Acknowledges every answer** — "Thank you ji", "Perfect", "Noted"
4. **Never invents data** — always uses tools to check availability/pricing
5. **Summarizes before confirming** — reads back all details before booking
6. **Suggests alternatives** — if no availability, offers other dates/rooms
7. **Escalates gracefully** — "Let me connect you with the front desk" for unsupported requests
8. **Respects patience** — if guest pauses, Kaveri waits. Never rushes.

### Booking Rules

- Bookings require: name, phone, room type, check-in, check-out
- Check-in date must be today or future
- Check-out must be after check-in
- Guest count cannot exceed room max occupancy
- Cancellation: free up to 24 hours before check-in

### Recording Rules

- Recording starts when the call connects
- Recording stops and saves when the call ends
- Recordings are stored as `.webm` files in the `recordings/` folder
- No recording is made if the call is less than 1 second
- Recordings persist across server restarts (file-based storage)

---

## Limitations

### Current Limitations

| Limitation | Reason | Workaround |
|------------|--------|------------|
| Browser-only (no phone calls) | Phone requires Twilio (paid) | Use browser mic — same experience |
| English only | Ollama model + STT are English | Future: add Hindi/multilingual model |
| In-memory bookings | No database persistence | Restart loses bookings (recordings persist) |
| Single user at a time | Ollama processes sequentially | Works fine for demos; add queue for production |
| Internet needed for TTS | Edge-TTS is cloud-based (free) | Fallback: browser's built-in TTS (offline) |
| Chrome/Edge required | Web Speech API not in Firefox/Safari | Use Chrome or Edge |
| AI response time 3-8 seconds | Ollama runs on CPU | Use GPU or smaller model (llama3.2:1b) |
| Recording is mic-only | Cannot capture Kaveri's audio output in recording | Browser limitation |

### Not Supported (Out of Scope for Demo)

- Payment processing
- Real phone line (PSTN) integration
- Multi-language conversations
- Multiple simultaneous calls
- Database persistence (Firestore/PostgreSQL)
- User authentication on dashboard
- Email/SMS confirmations

---

## How to Add Features

### Adding a New Room Type

Edit `app/hotel_data.py`, add to the `ROOM_TYPES` dict:

```python
ROOM_TYPES = {
    # ... existing rooms ...
    "presidential": {
        "name": "Presidential Suite",
        "description": "Our finest suite with private terrace and personal chef.",
        "base_price": 25000,
        "max_occupancy": 6,
        "total_rooms": 2,
        "amenities": ["Private terrace", "Personal chef", "Jacuzzi", "Butler"],
    },
}
```

### Adding a New Add-on

Edit `app/hotel_data.py`, add to `ADDONS`:

```python
ADDONS = {
    # ... existing addons ...
    "dinner": {"name": "Dinner Buffet", "price": 1200, "per": "per person per day"},
}
```

### Changing Kaveri's Personality

Edit the `SYSTEM_PROMPT` in `app/ai_engine.py`. Key sections:
- `YOUR PERSONALITY AND STYLE` — tone, expressions, formality
- `INFORMATION GATHERING` — what data to collect
- `CONVERSATION FLOW` — step-by-step call structure

### Changing the Voice

Edit `app/local_tts.py`, change the voice parameter:

```python
# Indian English voices available:
voice="en-IN-NeerjaNeural"    # Female (default - Kaveri)
voice="en-IN-PrabhatNeural"   # Male
```

Full list of voices: run `edge-tts --list-voices | findstr en-IN`

### Adding a New Data Field to Collect

1. Add the field to the system prompt in `app/ai_engine.py` under "Required information"
2. Add the parameter to `create_booking()` in `app/hotel_data.py`
3. Add a column to the dashboard table in `app/pages/dashboard_page.py`

### Changing Hotel Information

Edit the `HOTEL_INFO` dict at the top of `app/hotel_data.py`:

```python
HOTEL_INFO = {
    "name": "Your Hotel Name",
    "tagline": "Your tagline",
    "address": "Your address",
    # ...
}
```

### Adding Database Persistence

Replace the in-memory `bookings` dict in `hotel_data.py` with:
- **SQLite** (simple, file-based): use `sqlite3` module
- **Firestore** (cloud, free tier): use `firebase-admin` SDK
- **PostgreSQL** (production): use `asyncpg` or `sqlalchemy`

### Adding Phone Call Support (Twilio)

See the original architecture in the README. Requires:
1. Twilio account ($15 free trial credit)
2. ngrok for public URL
3. Replace browser WebSocket with Twilio Media Streams

---

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Voice call page (HTML) |
| GET | `/dashboard` | Dashboard page (HTML) |
| GET | `/health` | Health check |
| GET | `/api/bookings` | List all bookings |
| GET | `/api/calls` | List all calls with gathered info |
| GET | `/api/recordings` | List all recording metadata |
| GET | `/api/recordings/{call_id}` | Stream recording audio file |
| GET | `/api/hotel-info` | Hotel info and room types |
| GET | `/docs` | Interactive API documentation (Swagger) |

### WebSocket Endpoint

**`WS /voice`** — Real-time voice communication

Messages from browser to server:
```json
{"type": "transcript", "text": "I want to book a room"}
{"type": "recording", "audio": "<base64>", "mimeType": "audio/webm"}
{"type": "end_call"}
```

Messages from server to browser:
```json
{"type": "audio_response", "text": "Namaste! ...", "audio": "<base64 mp3>"}
{"type": "text_response", "text": "Namaste! ..."}
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Cannot connect to server" | Server not running | Run `py -m uvicorn app.main:app --port 8000` |
| "Ollama connection error" | Ollama not running | Run `ollama serve` in separate terminal |
| No AI response | Model not pulled | Run `ollama pull llama3.2` |
| Mic not working | Permission denied | Click lock icon in browser address bar → allow mic |
| No speech recognition | Wrong browser | Use Chrome or Edge (Firefox doesn't support Web Speech API) |
| Slow responses (>10s) | CPU-only inference | Normal on CPU. Use `llama3.2:1b` for faster (less smart) |
| "Edge-TTS error" | No internet | TTS needs internet. Fallback: browser speaks the text |
| Recording not saving | Call too short | Recording only saves if >1KB of audio data |
| Dashboard empty | No calls made yet | Make a call first — data appears in real-time |
| Port 8000 in use | Another server running | Kill it or use `--port 8001` |

### Faster AI Responses

If Kaveri is too slow on your machine:

```bash
# Use the smaller 1B model (faster, slightly less smart)
ollama pull llama3.2:1b
```

Then edit `.env`:
```
OLLAMA_MODEL=llama3.2:1b
```

### Check Everything is Working

```bash
# Check Ollama
curl http://localhost:11434/api/version

# Check server
curl http://localhost:8000/health

# Check model loaded
ollama list
```

---

## Project Structure

```
hotel-voice-booking-demo/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, routes, static mounts
│   ├── config.py            # Environment variables
│   ├── ai_engine.py         # Kaveri's brain — Ollama conversation + tools
│   ├── call_handler.py      # WebSocket session manager
│   ├── hotel_data.py        # Rooms, pricing, booking logic (in-memory)
│   ├── local_tts.py         # Edge-TTS (Indian English voice)
│   ├── local_stt.py         # Fallback STT (browser handles primary)
│   ├── recorder.py          # Audio recording save/retrieve
│   └── pages/
│       ├── __init__.py
│       ├── call_page.py     # Voice call UI (HTML/JS)
│       └── dashboard_page.py # Dashboard UI (HTML/JS)
├── recordings/              # Saved call audio files (.webm)
├── .env                     # Configuration (model, port)
├── requirements.txt         # Python dependencies
├── setup_and_run.bat        # One-click Windows launcher
├── run.py                   # Python entry point with checks
├── README.md                # Quick start guide
└── DOCUMENTATION.md         # This file
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | June 2026 | Initial demo — browser voice call + booking |
| 1.1 | June 2026 | Added Kaveri personality, Indian voice, recording, dashboard columns |

---

## Credits

- **AI Model**: Meta Llama 3.2 (via Ollama)
- **TTS Voice**: Microsoft Edge Neural TTS (en-IN-NeerjaNeural)
- **Speech Recognition**: Browser Web Speech API
- **Framework**: FastAPI + Uvicorn
- **Cost**: $0 — entirely free and open tools
