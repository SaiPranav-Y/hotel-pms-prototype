# Karivena Satram — Voice AI Booking Platform

A voice + WhatsApp AI assistant for pilgrim-accommodation booking. It answers calls, greets guests, checks room availability across locations, validates community eligibility (gotram), takes bookings, offers donations/sevas, and sends confirmations, payment links, invoices, and 80G certificates over WhatsApp.

Runs **100% locally and free** by default — a local LLM (Ollama), in-memory storage, and mock payments/WhatsApp. Add real credentials only when you want to go live.

> **This `working-app` branch** contains the complete, runnable backend application at the repo root. Clone it, install, and run. It shares history with `karivena-voice-ai` (the full monorepo with the Flutter PMS app and Twilio voice-gateway), so you can diff/PR between them.

---

## What it does

- **Voice assistant (Kaveri)** — natural phone conversations for booking rooms
- **Gotram eligibility** — every booking validates the guest's gotram against an approved list
- **10 locations, 360 rooms** — Srisailam, Shiridi, Kasi, Tirupathi, and more
- **Rate management** — room rates by location × room type × season (admin-editable)
- **3 payment types** — fixed room · room + donation · seva donation (80G eligible)
- **Automated documents** — invoice + 80G certificate PDFs generated and pushed to WhatsApp
- **WhatsApp checkout** — end-of-stay payment + invoice, always over WhatsApp
- **Payment automation** — a confirmed donation auto-issues its 80G certificate (Razorpay webhook)
- **Role-based access** — Supervisor / Admin / Super Admin
- **Web dashboard** — bookings, calls, payments, donations, gotrams, analytics

---

## Quick Start (Windows — one click)

```bat
setup_and_run.bat
```

Checks Python + Ollama, installs dependencies, pulls the AI model, and starts the server. Then open **http://localhost:8000**.

---

## Quick Start (manual — any OS)

### 1. Prerequisites

- **Python 3.9+** — https://www.python.org/downloads/
- **Ollama** (free local AI) — https://ollama.com/download

### 2. Install the Ollama model (one-time, ~2 GB)

```bash
ollama serve          # start Ollama (keep running)
ollama pull llama3.2  # download the model
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure integrations

Everything runs in local/mock mode with no config. To enable persistence or live payments/WhatsApp:

```bash
cp .env.example .env    # then edit .env
```

See `.env.example` for every option (Firebase, Razorpay, WhatsApp). All are optional.

### 5. Run

```bash
python run.py
```

Open **http://localhost:8000**.

---

## Using the app

| URL | What it is |
|-----|-----------|
| http://localhost:8000 | Voice call page — click the phone, allow the mic, and speak |
| http://localhost:8000/dashboard | Operations dashboard (bookings, payments, donations, gotrams) |
| http://localhost:8000/docs | Interactive API documentation (Swagger) |
| http://localhost:8000/health | Health check + version |

**Try it:** open the call page in Chrome/Edge, click the green phone button, allow microphone access, and say _"I'd like to book a room for this weekend."_ Watch the dashboard update.

---

## Run the tests

```bash
python test_all.py       # 27 core tests
python test_phase5.py    # gotram / payments / WhatsApp
python test_phase6.py    # roles / rates / payment types / invoice / 80G / checkout
python test_phase7.py    # payment automation / relative dates / consent
```

> Note: the single "Firebase connection" test in `test_all.py` fails unless you've added `firebase-key.json` and set `FIREBASE_ENABLED=true`. That is expected — without it the app uses in-memory storage.

---

## Project layout

```
app/
  main.py            FastAPI app + all API routes
  ai_engine.py       Kaveri's LLM brain (Ollama) + tool calling
  knowledge_base.py  Availability + booking logic
  gotram.py          Community-eligibility validation
  rates.py           Rate management (location x room_type x season)
  payments.py        Razorpay links + 3 payment types + 80G + webhook automation
  invoice.py         Invoice PDF generator
  certificate_80g.py 80G certificate PDF generator
  checkout.py        WhatsApp-driven end-of-stay checkout
  whatsapp.py        WhatsApp message + document composer/dispatcher
  roles.py           Role-based access control
  firebase_store.py  Firestore persistence (optional; in-memory fallback)
  normalizer.py      Speech + relative-date parsing ("next weekend", etc.)
  local_stt.py       Whisper STT     local_tts.py  Piper TTS
  pages/             Web dashboard + call page (HTML)
  room_data.json     Room inventory   allowed_gotrams.json  Approved gotrams
run.py               Start the server (checks Ollama first)
requirements.txt     Python dependencies
.env.example         All configuration options (copy to .env)
```

---

## Configuration modes

| Integration | Without config | With config |
|-------------|---------------|-------------|
| **LLM** | Local Ollama (required) | — |
| **Storage** | In-memory (resets on restart) | Firestore (persistent) |
| **Payments** | Mock links (functional for demos) | Live Razorpay |
| **WhatsApp** | Logged to console (mock) | Meta Cloud API or webhook |

To go live, fill the relevant values in `.env` and add `firebase-key.json` for persistence. The payment webhook (`/api/payments/webhook`) then closes the automation loop: a confirmed donation auto-issues its 80G certificate to WhatsApp.

---

## Notes for production

- Fill real org/trust details in `app/invoice.py` (`ORG`) and `app/certificate_80g.py` (`TRUST_80G`, including the 80G registration number + PAN — until then certificates print in DRAFT mode).
- Replace `app/allowed_gotrams.json` placeholders with the real approved list.
- Provide real rates via `app/rate_config.json` (see `app/rate_config.example.json`) or the `/api/rates` admin endpoints.
- The greeting discloses AI identity + call-recording consent (India compliance).

---

## Security

- **Never commit** `.env` or `firebase-key.json` — both are git-ignored.
- Keep Razorpay and WhatsApp secrets out of version control.
- Permission-gated API routes expect an `X-User-Email` header identifying a provisioned staff user.
