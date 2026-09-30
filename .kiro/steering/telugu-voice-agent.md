---
title: Telugu Voice Agent for Room Booking
scope: voice-agent/
inclusion: manual
---

# Steering File: Telugu Voice Agent for Room Booking (Phone, Local Ollama)

> Governs the `voice-agent/` project. Locked decisions for this build:
> - HOTEL_NAME = **Karivena Satram**
> - Hardware = **CPU-only** → small models, expect multi-second pauses + filler phrases
> - LLM = **Ollama `llama3.2`** (already pulled locally; configurable via `OLLAMA_MODEL`)
> - Storage = **SQLite** (self-contained, offline), seeded from Karivena room/rate data
> - Telephony = **dev-only**; Phase 1 is TEXT-MODE, then local mic/speaker. No real number.
>
> REMAINING PLACEHOLDERS to confirm before go-live:
> - `<ROOM_TYPES/PRICES>` — reused from repo `room_data.json` + `rate_config.json` (verify amounts)
> - Telugu template phrases — **must be reviewed by a native speaker** before any demo to real users
> - Real telephony (Twilio/SIP) — out of scope for the demo

---

## 1. Project Goal

Build a voice agent that answers inbound phone calls for **Karivena Satram** and helps callers
**check availability, book, look up, and cancel rooms**, entirely in **Telugu**.

### Non-negotiables (never violate these)

1. **Telugu only.** The agent speaks Telugu in every spoken response: greeting, questions,
   confirmations, errors, and goodbye. It never switches to English or Hindi, even if the caller does.
   If the caller speaks English words (room, AC, check-in), the agent understands them but replies in Telugu.
2. **Local LLM via Ollama** (`http://localhost:11434`). No cloud LLM calls.
3. **Free / open-source software only.** No paid APIs in the default configuration.
4. **No hallucinated facts.** Availability, prices, and booking IDs come only from the database
   through tool calls. The LLM never invents them.
5. **Always confirm before committing.** Repeat dates, guests, room type, price, and name back
   to the caller and get an explicit "yes" (అవును / సరే) before writing a booking.

---

## 2. Honest Constraints

- Software is free; a real phone number is not. Demo path = text-mode + local mic/speaker (LAN),
  no telephony provider.
- Telugu STT/TTS/LLM quality is the weakest link. Compensate with a narrow, guided dialogue
  (one question per turn), confirmation of every extracted value, and deterministic Telugu templates.
- CPU-only: expect multi-second pauses; use small models and "ఒక్క నిమిషం…" filler phrases.

---

## 3. Architecture (Phase 1 = text-mode; voice/telephony added later)

```
[Phase 1] Text REPL ─► Dialogue Manager (state machine) ─► Ollama (NLU/slots) + SQLite tools ─► Telugu templates
[Phase 4] Mic/VAD ─► STT(te) ─► (same core) ─► TTS(te) ─► Speaker
[Phase 5] Asterisk/SIP ─► (same core)
```

The LLM does **understanding** (intent + slots as JSON). A deterministic **state machine** controls
flow and produces most spoken text from pre-written Telugu templates.

---

## 4. Tech Stack (this build)

| Layer | Choice |
|---|---|
| Language | Python 3.11+, asyncio |
| LLM | Ollama `llama3.2` (config `OLLAMA_MODEL`); alt `gemma3:4b` if pulled |
| DB | SQLite (SQLAlchemy) seeded from Karivena `room_data.json` + `rate_config.json` |
| STT (Phase 2) | `faster-whisper` Telugu (CPU: base/small) — swappable `STTProvider` |
| TTS (Phase 3) | `facebook/mms-tts-tel` (CPU) — swappable `TTSProvider`; `edge-tts` only if `ALLOW_CLOUD_TTS=true` (default false) |
| Telephony (Phase 5) | Asterisk + SIP softphone — swappable `TelephonyAdapter` |
| Config | `.env` + pydantic-settings |
| Tests | pytest + text-mode transcripts |

STT/TTS/LLM/telephony are each swappable interfaces.

---

## 5. Project Structure

```
voice-agent/
├── app/
│   ├── config.py
│   ├── llm/            base.py, ollama_client.py, prompts.py
│   ├── dialogue/       state_machine.py, slots.py, templates_te.py
│   ├── nlp_te/         normalize.py (numbers, dates)
│   ├── tools/          availability.py, booking.py
│   └── db/             models.py, seed.py
├── run_text.py         # Phase 1 text-mode REPL
├── tests/
├── .env.example
└── README.md
```

---

## 6. Conversation Design

Flow: `GREETING → INTENT → COLLECT_SLOTS → CHECK_AVAILABILITY → OFFER → CONFIRM → BOOK → GOODBYE`
with correction loop and global `TRANSFER_TO_HUMAN` / `GOODBYE`.

Intents: `book_room, check_availability, cancel_booking, booking_status, ask_price, ask_facilities, talk_to_human, goodbye, unknown`.
Booking slots: `check_in_date, check_out_date|nights, num_guests, room_type, guest_name, callback_number`.

Rules: one question per turn (<20 words); ask only missing slots; read back + confirm every critical
value; after 2 failed attempts offer human transfer; polite **మీరు** form; barge-in later.

Template phrases live in `templates_te.py` (from the reviewed steering table) — flag for native review.

---

## 7. Telugu-Specific Requirements

Telugu script only for TTS/LLM output (never Tenglish). Handle code-mixed input via an alias dict
(ఏసీ/AC/ఎసి → AC). Convert numbers/dates/prices to Telugu words before TTS. Parse Telugu numbers +
relative dates (రేపు, ఎల్లుండి, వచ్చే శుక్రవారం) → ISO using `Asia/Kolkata`. NFC normalize; UTF-8 everywhere.

---

## 8. LLM (Ollama) Rules

`/api/chat`, `keep_alive=30m`, warm up at start, `temperature 0–0.2`, small `num_ctx`.
NLU returns JSON only: `{"intent": "...", "slots": {...}, "confidence": 0.x}`. Validate with pydantic;
retry once on failure then fall back to a template. App resolves dates (never trust LLM date math).
Guard: discard any generated text lacking Telugu characters (`\u0C00–\u0C7F`) → use template.

---

## 9. Tools & Data Model

`rooms(id, type, capacity, price_per_night, active)`, `bookings(id, room_id, guest_name, phone,
check_in, check_out, guests, status, created_at)`. Tools: `check_availability`, `create_booking`
(transactional, re-check inside txn), `get_booking`, `cancel_booking` (phone match + confirm).
Booking IDs short + speakable (4–6 digits). Log every action with call ID.

---

## 10–11. Latency / Reliability / Safety

Stream everything; preload models; cache static TTS phrases; skip LLM when a rule suffices.
On failure → Telugu apology, retry once, offer transfer. No silence > ~3 s (filler). Concurrency
1–2 calls on CPU. No payments by voice. Announce recording in Telugu if recording.

---

## 12. Build Order

1. **Text-only prototype** (state machine + templates + Ollama NLU + SQLite) ← current
2. STT (Telugu, faster-whisper) 3. TTS (mms-tts-tel) 4. Local mic/speaker loop
5. Asterisk/SIP dev 6. Real number (adapter) 7. Hardening (eval, latency, concurrency)

---

## 13. Definition of Done (Phase 1)

- [ ] Text-mode: type Telugu → complete a booking, cancellation, and availability check in Telugu.
- [ ] No English/Hindi in agent output (automated Telugu-script check on all output).
- [ ] Runs locally with Ollama, no paid service.
- [ ] Bookings need explicit spoken/typed confirmation; no double bookings under concurrency.
- [ ] Tests: date/number parsing, dialogue flow, Telugu guard.
- [ ] README: install, `ollama pull`, run text-mode.

---

## 14. Instructions to the Assistant

Work phase by phase. Confirm library APIs from docs before use. No paid/cloud deps without asking.
Keep all Telugu strings in `templates_te.py`. Flag uncertain Telugu for native-speaker review.
