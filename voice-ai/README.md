# Hotel Voice Booking Demo

A working AI-powered voice receptionist that answers phone calls, greets guests warmly, and books hotel rooms — all through a natural conversation over the phone.

**Call the number → AI greets you → you tell it your dates → it checks availability → confirms the booking → done.**

Built with: Twilio (telephony) + Deepgram (speech-to-text & text-to-speech) + Claude (AI brain) + FastAPI (server)

---

## Quick Start (15 minutes to a working demo)

### Prerequisites

- Python 3.9+ installed
- A Twilio account (free trial: https://www.twilio.com/try-twilio — gives you $15 credit)
- A Deepgram account (free: https://console.deepgram.com — 45,000 minutes free)
- An Anthropic account (https://console.anthropic.com — trial credits for Claude)
- ngrok installed (free: https://ngrok.com/download — exposes your local server to the internet)

### Step 1: Install dependencies

```bash
cd hotel-voice-booking-demo
pip install -r requirements.txt
```

### Step 2: Set up environment variables

```bash
copy .env.example .env
```

Edit `.env` with your actual API keys:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1234567890
DEEPGRAM_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
PUBLIC_URL=https://your-ngrok-url.ngrok-free.app
```

### Step 3: Start ngrok (in a separate terminal)

```bash
ngrok http 8000
```

Copy the HTTPS URL it gives you (e.g., `https://abc123.ngrok-free.app`) and put it in your `.env` as `PUBLIC_URL`.

### Step 4: Start the server

```bash
python -m app.main
```

You should see:
```
Starting Hotel Voice Booking Demo on 0.0.0.0:8000
Dashboard: http://0.0.0.0:8000/
Twilio webhook: https://your-ngrok-url.ngrok-free.app/incoming-call
```

### Step 5: Configure Twilio

1. Go to your Twilio Console → Phone Numbers → Active Numbers
2. Click your number
3. Under "Voice & Fax" → "A Call Comes In":
   - Set to **Webhook**
   - URL: `https://your-ngrok-url.ngrok-free.app/incoming-call`
   - Method: **POST**
4. Save

### Step 6: Call your Twilio number!

Dial the number from your phone. Maya (the AI receptionist) will greet you and help you book a room.

Open `http://localhost:8000` in your browser to see the live dashboard — bookings appear in real-time as calls happen.

---

## How It Works

```
You dial the Twilio number
        │
        ▼
Twilio receives call → hits POST /incoming-call
        │
        ▼
Server returns TwiML → "Connect this call to my WebSocket"
        │
        ▼
Twilio opens WebSocket to /media-stream → streams your voice audio
        │
        ▼
Audio → Deepgram STT (real-time transcription) → text
        │
        ▼
Text → Claude AI (with hotel booking tools) → response text
        │
        ▼
Response → Deepgram TTS (text-to-speech) → audio
        │
        ▼
Audio streamed back through WebSocket → Twilio → you hear it
        │
        ▼
(Loop continues until call ends or booking is made)
```

---

## Project Structure

```
hotel-voice-booking-demo/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, routes, dashboard
│   ├── config.py          # Environment variables
│   ├── hotel_data.py      # Room types, pricing, booking functions (in-memory DB)
│   ├── ai_engine.py       # Claude conversation engine with tool calling
│   ├── call_handler.py    # WebSocket handler orchestrating STT→AI→TTS
│   ├── deepgram_stt.py    # Speech-to-text (Deepgram streaming)
│   └── deepgram_tts.py    # Text-to-speech (Deepgram Aura)
├── .env.example
├── requirements.txt
└── README.md
```

---

## What the AI Can Do

During a call, the AI (Maya) can:

- **Describe room types** — Standard, Deluxe, Executive Suite with pricing
- **Check availability** — for specific dates and guest counts
- **Create bookings** — collects name, phone, dates, room preference
- **Look up bookings** — by booking ID
- **Cancel bookings** — with policy explanation
- **Suggest add-ons** — breakfast, airport pickup, spa, late checkout
- **Answer questions** — check-in/out times, cancellation policy, pet policy, etc.

---

## Demo Tips

When presenting to your team:

1. Open the dashboard (`http://localhost:8000`) on a big screen
2. Call the number on speakerphone so everyone can hear
3. Try: "Hi, I'd like to book a room for this weekend for two people"
4. Watch the booking appear on the dashboard in real-time
5. Try edge cases: "What's your cheapest room?", "Can I bring my dog?", "I need to cancel"

---

## Customization

**Change hotel details**: Edit `HOTEL_INFO`, `ROOM_TYPES`, and `ADDONS` in `app/hotel_data.py`

**Change AI personality**: Edit `SYSTEM_PROMPT` in `app/ai_engine.py`

**Change voice**: Edit `TTS_PARAMS["model"]` in `app/deepgram_tts.py`. Options:
- `aura-asteria-en` — Female, warm (default)
- `aura-luna-en` — Female, soft
- `aura-orion-en` — Male, professional
- `aura-arcas-en` — Male, warm

---

## Using Your Existing Phone Number

You don't need customers to dial a Twilio number directly. Set up **call forwarding** from your existing hotel number:

**Airtel**: Dial `*21*<twilio_number>#` to activate, `##21#` to deactivate
**Jio**: Use MyJio app → Settings → Call Forwarding
**Vi**: Dial `*21*<twilio_number>#`

This way, customers dial your normal hotel number and get connected to the AI.

---

## Costs (Free Tier Limits)

| Service | Free Allowance |
|---------|---------------|
| Twilio | $15 trial credit (~500 min calls) |
| Deepgram STT | 45,000 minutes |
| Deepgram TTS | Included with STT credits |
| Claude API | Trial credits (varies) |
| ngrok | Free tier (sessions reset every few hours) |

For a team demo, these free tiers are more than enough.

---

## Troubleshooting

**No audio / AI doesn't respond**: Check that ngrok is running and PUBLIC_URL in .env matches the ngrok URL exactly.

**"Connection refused"**: Make sure the server is running (`python -m app.main`) before making a call.

**Twilio says "application error"**: Check your server logs — usually means the webhook URL is wrong or ngrok session expired.

**AI is slow to respond**: First response is slower (Claude cold start). Subsequent responses should be 1-2 seconds. If consistently slow, check your internet connection to the APIs.

**Echo / hearing yourself**: The echo prevention in call_handler.py should handle this. If it persists, check that the `_is_speaking` flag is working correctly in logs.

---

## Karivena Satram Platform — v4.0 (Role Workspaces, Rates, 80G, WhatsApp Checkout)

Building on the voice/WhatsApp booking core, v4.0 adds staff role management, admin-editable rates, three payment types with 80G tax-exemption tracking, automated invoice + 80G certificate PDFs, and a WhatsApp-driven checkout flow.

### Role-Based Workspaces

Three staff roles with an ascending permission matrix (`app/roles.py`):

| Role | Can do |
|------|--------|
| **Supervisor** | Walk-in bookings, view bookings/calls/customers/availability, generate invoices, trigger checkout |
| **Admin** | Everything above + edit room rates, set seva amounts, edit gotrams, view analytics, manage campaigns/escalation |
| **Super Admin** | Everything above + manage staff users, assign roles, delete bookings, system config |

Users live in the Firestore `users` collection (keyed by lowercased email). The Flutter PMS app (`lib/`) has a login screen and role-filtered navigation; the FastAPI backend gates routes via an `X-User-Email` header and `roles.check_access(email, permission)`.

### Rate Management (`app/rates.py`)

Rates are `location × room_type × season`. Base rate applies unless a dated season override matches. Only Admin/Super Admin can edit.

- Loads from `app/rate_config.json` → Firestore `rates` → Excel fallback.
- Copy `app/rate_config.example.json` to `app/rate_config.json` and fill your real rates.
- Booking price computation auto-uses configured rates when present.

### Three Payment Types (`app/payments.py`)

1. **Fixed room** — Razorpay link for the room total.
2. **Fixed room + donation** — customer enters any donation amount; 80G certificate issued for the donation portion only.
3. **Seva donation** — predefined seva amounts (Admin-editable) or a custom amount; always 80G eligible.

All donations carry `is_80g` + `certificate_80g_issued` flags. `get_payment_stats()` reports `donation_80g_total` and certificates issued.

### Automated PDFs

- **Invoice** (`app/invoice.py`) — tax invoice with room + optional donation line, rupees-in-words, written to `app/generated/invoices/`.
- **80G Certificate** (`app/certificate_80g.py`) — donation receipt under Section 80G, written to `app/generated/certificates/`. Runs in DRAFT mode until the trust's 80G registration number + PAN are filled into `TRUST_80G`.

Both use `reportlab`.

### WhatsApp Checkout (`app/checkout.py`)

Checkout is always handled over WhatsApp. `process_checkout(booking, donation_payment_id)`:

1. Creates the Razorpay checkout payment link.
2. Generates the invoice PDF.
3. Generates the 80G certificate PDF (if a donation was made).
4. Pushes the checkout message + payment link + documents to the guest's WhatsApp.
5. Marks the reservation `checked_out` in Firestore.

`run_due_checkouts(date)` is the end-of-stay scheduler entry point (processes reservations whose `check_out` has passed).

### New API Routes

```
GET  /api/roles                       list roles + permissions
GET  /api/users                       list staff            (manage_users)
POST /api/users                       create staff          (manage_users)
POST /api/users/{email}/role          change role           (assign_roles)
GET  /api/rates                       full rate table
GET  /api/rates/quote                 price quote for a stay
POST /api/rates                       set base rate         (edit_rates)
POST /api/rates/season                add season override   (edit_rates)
POST /api/sevas                       set seva amount       (set_seva_amounts)
POST /api/payments/room-donation      type 2 link
POST /api/payments/seva               type 3 link
POST /api/invoice                     generate invoice PDF  (generate_invoice)
GET  /api/invoice/{id}/download       download invoice PDF
GET  /api/certificates/80g            list 80G-eligible donations
POST /api/certificates/80g            generate 80G PDF      (generate_invoice)
GET  /api/certificates/80g/{id}/download
POST /api/checkout                    run checkout          (trigger_checkout)
POST /api/checkout/run-due            run all due checkouts (trigger_checkout)
```

Permission-gated routes require an `X-User-Email` header identifying a provisioned staff user; they return 401 (no/unknown user) or 403 (insufficient role) otherwise.

### What to provide later

- Firebase Auth staff credentials (create users in `users` collection with roles).
- Real room rates (`rate_config.json` or via `/api/rates`).
- Trust 80G registration number + PAN (in `certificate_80g.TRUST_80G`) and org details (in `invoice.ORG`).
- Razorpay live keys (`RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`) and WhatsApp provider config — otherwise the platform runs in graceful MOCK mode.

### Tests

```bash
py test_all.py       # 27 core tests
py test_phase5.py    # 12 gotram/payment/whatsapp tests
py test_phase6.py    # 24 roles/rates/payment-types/invoice/80G/checkout tests
```

---

## v4.1 — Automation + Compliance Gaps Closed

### Razorpay Payment Webhook → Auto 80G Certificate

The automation loop is now closed end-to-end: when a donation payment is confirmed (either via the Razorpay webhook or manual mark-paid), the system:

1. Marks the payment as paid
2. Auto-generates the 80G certificate PDF (if it's a donation with `is_80g`)
3. Pushes the certificate to the donor's WhatsApp
4. Flags `certificate_80g_issued` to prevent duplicates (idempotent)

Configure the webhook in Razorpay dashboard → Settings → Webhooks:
- URL: `https://<your-host>/api/payments/webhook`
- Secret: same as `RAZORPAY_WEBHOOK_SECRET` in your `.env`
- Events: `payment_link.paid`, `payment.captured`

Signature verification uses HMAC-SHA256. In mock mode (no secret configured) verification is skipped for local testing.

### Relative Date Parsing

The normalizer now handles natural-language dates:

- `tomorrow`, `day after tomorrow`, `today`, `tonight`
- `this weekend`, `next weekend` (returns distinct Saturdays)
- All weekdays: `this friday`, `next monday`, etc.
- `next week`, `next month`
- Date ranges: `June 28 to June 30` (both captured)
- Duration: `3 nights`, `2 rojulu`
- ISO and slash formats: `2026-09-01`, `28/06/2026`

The AI prompt also instructs the LLM to resolve relative dates to exact YYYY-MM-DD and confirm ambiguous ones before booking.

### Call-Recording Consent (India Compliance)

The greeting now discloses AI identity and recording consent per Indian telecom regulations:

> _"This is Kaveri, your AI assistant. Please note this call may be recorded for quality and confirmation purposes."_

Both the Python (ai_engine.py) and Node.js (voice-gateway) prompts include a rule to disclose this on the first turn only, and offer transfer to a staff member if the caller objects.

### Tests

```bash
py test_phase7.py    # 19 tests: automation, webhook, date parsing, consent
# Total: 82 tests across all suites (27 + 12 + 24 + 19)
```
