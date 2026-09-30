# Telugu Voice Booking Agent

A **Telugu-first** room-booking assistant for **Karivena Satram**. Callers
interact entirely in **Telugu** to check availability, book, look up, and cancel
rooms. It runs **offline and free**: a local [Ollama](https://ollama.com) model
for intent detection, a self-contained SQLite database for rooms/bookings, and
CPU-friendly speech components.

The room inventory and rates are **reused from the existing Karivena data**
(`room_data.json` / `rate_config.json`) so this agent books against the same
source of truth as the main PMS.

Three interchangeable front-ends drive the **same** dialogue core:

```
run_text.py   : keyboard      → DialogueSession → console          (Phase 1)
run_voice.py  : mic → STT     → DialogueSession → TTS → speaker     (Phases 2-4)
run_call.py   : phone → STT   → DialogueSession → TTS → phone       (Phases 5-6)
```

There are three ways to talk to the **same** Telugu booking agent: text, voice,
and **WhatsApp** — all sharing one dialogue core (same greeting, gotram, email,
etc.). It can book against a local practice database or the **live Karivena PMS
data** (`DATA_SOURCE=sqlite|live`).

> **New to this? Start here:** double-click **`start_here.bat`** (or run
> `py start_here.py`) for a guided menu, and read the plain-language
> **[GETTING_STARTED.md](GETTING_STARTED.md)**.

- **End-user guide (no coding):** **[GETTING_STARTED.md](GETTING_STARTED.md)**
- **Full setup / live mode / Firebase:** **[SETUP.md](SETUP.md)**
- **How this connects to the PMS:** **[docs/INTEGRATION.md](docs/INTEGRATION.md)**

---

## Why it's built this way

A small local LLM does **not** reliably read slot values (dates, counts, room
type) out of a full Telugu sentence. So responsibilities are split:

| Concern | How it's handled |
| --- | --- |
| **Intent** ("book", "cancel", "talk to a human") | Fast keyword rules first, LLM (`llama3.2`) as backup classifier |
| **Slot values** (location, date, nights, guests, room type, name) | **Deterministic** parsing per turn — `app/nlp_te/normalize.py` + `app/dialogue/slots.py`. No LLM. |
| **What the agent says** | **Reviewed Telugu templates only** (`app/dialogue/templates_te.py`). Nothing free-form is spoken. |
| **Availability & booking** | SQLite tools with a transactional re-check (no double-booking) |

Every outgoing line passes a **Telugu-script guard** (`is_telugu`); a line that
isn't Telugu is replaced with a safe template rather than spoken. The same guard
runs before TTS synthesis, so the agent can never voice non-Telugu.

---

## Project layout

```
voice-agent/
├── app/
│   ├── config.py            # env-driven config (Ollama, DB, STT/TTS, audio)
│   ├── metrics.py           # latency timing (Timings / measure / @timed)
│   ├── eval.py              # scenario eval harness (Telugu guard + outcomes)
│   ├── db/                  # models.py, seed.py (SQLite, seeded from Karivena)
│   ├── nlp_te/              # normalize.py (Telugu numbers/dates + guard)
│   ├── dialogue/            # slots.py, templates_te.py, state_machine.py
│   ├── llm/                 # base.py, prompts.py, ollama_client.py
│   ├── tools/               # availability.py, booking.py (transactional)
│   ├── audio/               # stt.py, tts.py, mic.py  (Phases 2-4)
│   └── telephony/           # base.py TelephonyAdapter + MockTelephony (5-6)
├── run_text.py              # Phase 1  text REPL
├── run_voice.py             # Phase 4  local mic/speaker loop
├── run_call.py              # Phase 5-6 telephony driver (mock by default)
├── deploy/asterisk/         # Asterisk/SIP config templates
├── docs/TELEPHONY.md        # how to wire a real phone channel
├── tests/                   # pytest suite
├── requirements.txt
├── .env.example
└── pytest.ini
```

---

## Prerequisites

- **Python 3.12+**
- **[Ollama](https://ollama.com)** running locally with the model pulled
  (optional — `--no-llm` skips it):
  ```
  ollama pull llama3.2
  ```
- Python packages: `py -m pip install -r requirements.txt`
  (core is small; STT/TTS/audio deps are optional — see the file's comments).

---

## Setup

```powershell
# from voice-agent/
copy .env.example .env      # optional; defaults work out of the box
py -m app.db.seed           # seed SQLite from the Karivena room/rate data
```

`seed` auto-discovers the sibling `hotel-voice-booking-demo/app/room_data.json`.
Set `ROOM_DATA_PATH` / `RATE_CONFIG_PATH` in `.env` to override.

Windows terminals need UTF-8 for Telugu to render:

```powershell
chcp 65001 > $null
$env:PYTHONIOENCODING = "utf-8"
```

---

## Phase 1 — Text mode

```powershell
py run_text.py            # with Ollama intent classification
py run_text.py --no-llm   # deterministic only (no Ollama needed)
```

Type in Telugu. Example booking turns:

```
బుక్ చేయాలి → శ్రీశైలం → రేపు → రెండు రోజులు → ఇద్దరు → ఏసీ → రవి కుమార్ → అవును
```

One question per turn; the agent reads back a confirmation summary and, on
`అవును`, returns a spoken booking number (digits spelled out in Telugu). Say
`మనిషితో మాట్లాడాలి` to transfer to a human. `exit` / `q` quits.

## Phases 2-4 — Local voice (mic + speaker)

```powershell
# spoken Telugu output uses edge-tts, which needs network + the flag:
$env:ALLOW_CLOUD_TTS = "true"
py run_voice.py
py run_voice.py --no-llm   # deterministic intent
py run_voice.py --text     # force typed input (skip the mic)
```

- **STT**: `faster-whisper` (CTranslate2, CPU `int8`, no PyTorch). The Telugu
  model downloads on first run.
- **TTS**: `edge-tts` Telugu voice (`te-IN-ShrutiNeural`), **gated** behind
  `ALLOW_CLOUD_TTS` because it sends text to Microsoft's free service. A fully
  offline Piper/MMS provider is stubbed as a seam.
- The loop **degrades gracefully**: no mic → typed input, no TTS → printed
  replies. Static phrases (greeting, prompts) are cached so repeat turns are fast.

## Phases 5-6 — Telephony

```powershell
py run_call.py             # runs a simulated inbound call (MockTelephony)
```

Real telephony is intentionally **out of scope** (a phone number isn't free).
The repo ships the `TelephonyAdapter` seam, a working in-memory mock, and
Asterisk/SIP config templates. To connect a free local SIP softphone via
Asterisk, see **[docs/TELEPHONY.md](docs/TELEPHONY.md)**.

---

## WhatsApp text channel

The same Telugu dialogue also runs over **WhatsApp text** — same greeting, same
guided questions, same gotram/email collection. The sender's WhatsApp number is
used as their contact automatically (so the phone question is skipped).

```powershell
py run_whatsapp.py            # starts the webhook on :8100 (MOCK send by default)
```

Test it without a WhatsApp account by POSTing to `/webhook`:

```
POST /webhook   {"from": "+919876543210", "text": "namaste"}
```

It accepts both a simple `{from, text}` body and the Meta WhatsApp Cloud API
webhook shape, and replies in Telugu. Outbound sending is MOCK (logged) until you
configure a provider (`WHATSAPP_TOKEN`+`WHATSAPP_PHONE_ID`, or
`WHATSAPP_WEBHOOK_URL`). Set `DATA_SOURCE=live` to book into the PMS. See
[GETTING_STARTED.md](GETTING_STARTED.md) for the friendly walkthrough.

---

## Live data integration (book into the Karivena PMS)

By default the agent uses its own offline SQLite DB. Set `DATA_SOURCE=live` to
book against the **same live data** as the `hotel-voice-booking-demo` PMS — its
`knowledge_base`, admin rates, gotram eligibility, payment/WhatsApp side-effects,
and (when Firebase is enabled in the demo) the shared Firestore the Flutter PMS
uses.

```powershell
$env:DATA_SOURCE = "live"
py run_text.py --no-llm
```

In live mode the agent additionally collects the caller's **phone, gotram, and
email** (required by the PMS), all in Telugu, and the gotram must be in the
approved community list. If the demo project can't be found, the agent falls
back to SQLite automatically. Full details and the data-flow diagram are in
**[docs/INTEGRATION.md](docs/INTEGRATION.md)**; setup is in **[SETUP.md](SETUP.md)**.

## Natural Telugu voice

Spoken output uses the natural Telugu neural voice `te-IN-ShrutiNeural` (female;
`te-IN-MohanNeural` is the male alternate) via `edge-tts`, with light prosody
tuning (`TTS_RATE=-6%`, `TTS_PITCH=-2Hz`) for a warmer, clearer read. Numbers,
prices, and dates are converted to **Telugu words** before synthesis so they're
spoken naturally rather than digit-by-digit.

---

## Tests & evaluation

```powershell
py -m pytest               # full suite
py -m app.eval             # scenario evaluation report
```

The suite covers:
- Telugu number/date parsing + the script guard (`test_normalize.py`)
- Alias normalization + slot logic (`test_slots.py`)
- Booking tools — no double-booking, pricing, cancel, rebook, non-overlap
  (`test_booking_tools.py`)
- End-to-end dialogue — booking, cancellation, "no rooms", transfer, retry
  (`test_dialogue_flow.py`)
- STT audio-shaping + TTS guard/cache/gating (`test_stt.py`, `test_tts.py`)
- Mic RMS + WAV I/O (`test_mic.py`)
- Telephony call lifecycle over the mock (`test_telephony.py`)
- Hardening — eval harness, latency timings, and **concurrent** create_booking
  never double-books (`test_hardening.py`)

Each DB-backed test runs against an **isolated temp SQLite DB** (see
`tests/conftest.py`), so your real `voice_agent.db` is never touched. Live audio
(actual mic/speaker) is verified by running `run_voice.py`.

---

## Configuration

All settings are environment variables (see `.env.example`). Key ones:

| Variable | Default | Notes |
| --- | --- | --- |
| `OLLAMA_MODEL` | `llama3.2` | intent classification only |
| `VOICE_AGENT_DB` | `voice_agent.db` | SQLite path |
| `HOTEL_NAME` | `Karivena Satram` | used in the greeting |
| `TIMEZONE` | `Asia/Kolkata` | anchors "today"/"tomorrow" |
| `ALLOW_CLOUD_TTS` | `false` | must be `true` for spoken (edge-tts) output |
| `STT_MODEL` | `small` | faster-whisper size (`base`/`small` on CPU) |
| `TTS_VOICE_TE` | `te-IN-ShrutiNeural` | edge-tts Telugu voice (natural) |
| `TTS_RATE` / `TTS_PITCH` | `-6%` / `-2Hz` | prosody for a warmer voice |
| `DATA_SOURCE` | `sqlite` | `live` books into the Karivena PMS data |
| `KARIVENA_DEMO_PATH` | (auto) | path to `hotel-voice-booking-demo` for live mode |

---

## Definition of Done (Phase 1) — status

- [x] Text-mode: type Telugu → complete a booking, cancellation, and
  availability check in Telugu.
- [x] No English/Hindi in agent output (automated Telugu-script check on every
  output line, in tests and the eval harness).
- [x] Runs locally with Ollama, no paid service.
- [x] Bookings need explicit typed/spoken confirmation; **no double bookings**
  under concurrency (verified with a threaded test).
- [x] Tests: date/number parsing, dialogue flow, Telugu guard.
- [x] README: install, `ollama pull`, run text-mode.

## Phase status overview

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Text-mode dialogue + booking | ✅ done |
| 2 | STT (faster-whisper, Telugu) | ✅ done |
| 3 | TTS (edge-tts Telugu + offline seam) | ✅ done |
| 4 | Local mic/speaker loop | ✅ done (live audio is user-run) |
| 5-6 | Telephony adapter seam + Asterisk templates | ✅ seam + mock + docs |
| 7 | Hardening: eval, latency, concurrency | ✅ done |
| + | Live PMS data integration (`DATA_SOURCE=live`) | ✅ done (see INTEGRATION.md) |

---

## Known limits & honest caveats

- **Telugu templates need a native-speaker review** before any real-user demo.
- **STT/TTS quality is the weakest link** on CPU; expect multi-second pauses.
  The dialogue is deliberately narrow (one question per turn, confirm everything)
  to compensate.
- **edge-tts needs network** and sends text to Microsoft. A fully offline neural
  TTS (Piper / `facebook/mms-tts-tel`) is left as a wired seam — it needs a
  working PyTorch/ONNX runtime, which wasn't available on the build machine.
- **No real telephony/number** — dev path only (mock + Asterisk templates).
- **No FAQ/facilities knowledge base** yet (facility questions steer to booking).

Generated files (`voice_agent.db`, `.env`, `.tts_cache/`, audio) are git-ignored.
Never commit credentials or guest PII.
