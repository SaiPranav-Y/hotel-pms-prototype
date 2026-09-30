# Telugu Voice Booking Agent — Phase 1 (Text Mode)

A **Telugu-first** room-booking assistant for **Karivena Satram**. Phase 1 runs
entirely as a **text conversation** (type Telugu, get Telugu back) so the
dialogue logic can be built and tested fast, with **no telephony and no audio**.
Everything runs **offline and free**: a local [Ollama](https://ollama.com) model
for intent detection and a self-contained SQLite database for rooms/bookings.

The room inventory and rates are **reused from the existing Karivena data**
(`room_data.json` / `rate_config.json`) so this agent books against the same
source of truth as the main PMS.

---

## Why it's built this way

The single hardest problem is that a small local LLM does **not** reliably read
slot values (dates, counts, room type) out of a full Telugu sentence. So the
design splits responsibilities:

| Concern | How it's handled |
| --- | --- |
| **Intent** ("book", "cancel", "talk to a human") | Fast keyword rules first, LLM (`llama3.2`) as backup classifier |
| **Slot values** (location, date, nights, guests, room type, name) | **Deterministic** parsing per turn — `app/nlp_te/normalize.py` + `app/dialogue/slots.py`. No LLM. |
| **What the agent says** | **Reviewed Telugu templates only** (`app/dialogue/templates_te.py`). Nothing free-form is spoken. |
| **Availability & booking** | SQLite tools with a transactional re-check (no double-booking) |

Every outgoing line passes a **Telugu-script guard** (`is_telugu`); if a line
somehow isn't Telugu, the agent falls back to a safe "I didn't understand"
template rather than speaking English or garbage.

---

## Project layout

```
voice-agent/
├── app/
│   ├── config.py            # env-driven config (Ollama, DB, data paths)
│   ├── db/
│   │   ├── models.py        # SQLAlchemy Room + Booking, engine/session
│   │   └── seed.py          # seeds rooms from Karivena JSON (idempotent)
│   ├── nlp_te/
│   │   └── normalize.py     # Telugu numbers/dates parsing + rendering, guard
│   ├── dialogue/
│   │   ├── slots.py         # alias normalization + BookingSlots
│   │   ├── templates_te.py  # all reviewed Telugu phrases
│   │   └── state_machine.py # the DialogueSession turn engine
│   ├── llm/
│   │   ├── base.py          # LLMProvider interface + NLU pydantic schema
│   │   ├── prompts.py       # English JSON-only NLU prompt
│   │   └── ollama_client.py # local Ollama backend (httpx)
│   └── tools/
│       ├── availability.py  # check_availability / price_for
│       └── booking.py       # create / get / cancel (transactional)
├── tests/                   # pytest suite (parsing, tools, dialogue flow)
├── run_text.py              # the text-mode REPL entrypoint
├── .env.example
└── pytest.ini
```

---

## Prerequisites

- **Python 3.12+**
- **[Ollama](https://ollama.com)** running locally, with the model pulled:
  ```
  ollama pull llama3.2
  ```
  Ollama is **optional** — you can run deterministic-only mode with `--no-llm`.
- Python packages: `sqlalchemy`, `httpx`, `pydantic` (and `pytest` for tests).

---

## Setup

```powershell
# from voice-agent/
copy .env.example .env      # optional; defaults work out of the box

# seed the SQLite DB from the Karivena room/rate data (idempotent)
py -m app.db.seed
```

`seed` auto-discovers the sibling `hotel-voice-booking-demo/app/room_data.json`.
Set `ROOM_DATA_PATH` / `RATE_CONFIG_PATH` in `.env` to override.

---

## Run the text demo

Windows terminals need UTF-8 so Telugu renders correctly:

```powershell
chcp 65001 > $null
$env:PYTHONIOENCODING = "utf-8"

py run_text.py            # with Ollama intent classification
py run_text.py --no-llm   # deterministic only (no Ollama needed)
```

Then type in Telugu. Example booking turns:

```
బుక్ చేయాలి → శ్రీశైలం → రేపు → రెండు రోజులు → ఇద్దరు → ఏసీ → రవి కుమార్ → అవును
```

The agent asks one question per turn, reads back a confirmation summary, and on
`అవును` returns a short **spoken** booking number (digits spelled out in Telugu).
Type `exit` / `q` to quit. Say `మనిషితో మాట్లాడాలి` to transfer to a human.

---

## Tests

```powershell
chcp 65001 > $null
$env:PYTHONIOENCODING = "utf-8"
py -m pytest
```

The suite covers:
- **Telugu number/date parsing** and the script guard (`test_normalize.py`)
- **Alias normalization** and slot logic (`test_slots.py`)
- **Booking tools** — no double-booking, pricing, cancel, rebook, non-overlap
  (`test_booking_tools.py`)
- **End-to-end dialogue flow** — full booking, cancellation, "no rooms" when
  full, transfer-to-human, retry-then-transfer (`test_dialogue_flow.py`)

Each test runs against an **isolated temp SQLite DB** (see `tests/conftest.py`),
so your real `voice_agent.db` is never touched.

---

## Configuration

All settings are environment variables (see `.env.example`). Key ones:

| Variable | Default | Notes |
| --- | --- | --- |
| `OLLAMA_MODEL` | `llama3.2` | intent classification only |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | local server |
| `VOICE_AGENT_DB` | `voice_agent.db` | SQLite path |
| `HOTEL_NAME` | `Karivena Satram` | used in the greeting |
| `TIMEZONE` | `Asia/Kolkata` | anchors "today"/"tomorrow" |
| `ALLOW_CLOUD_TTS` | `false` | Phase 1 keeps everything local |

---

## Phase 1 scope & limits

- ✅ Book a room, quote a price, confirm, cancel — all in Telugu, offline.
- ✅ No hallucinated facts: availability and prices come only from the DB.
- ⏳ **Text only** — no speech-to-text, text-to-speech, or telephony yet.
- ⏳ **Telugu templates need a native-speaker review** before any production use.
- ⏳ No FAQ/facilities knowledge base yet (facility questions steer to booking).

Generated files (`voice_agent.db`, `.env`) are git-ignored. Never commit
credentials or guest PII.
