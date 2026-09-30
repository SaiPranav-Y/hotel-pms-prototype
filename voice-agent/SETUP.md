# Setup Guide — Telugu Voice Booking Agent (Karivena Satram)

This is the step-by-step setup for the Telugu voice agent, in **two modes**:

- **SQLite mode** (default) — fully self-contained and offline. Bookings go to a
  local SQLite file seeded from the Karivena room data. Best for a quick demo
  and for all the tests.
- **Live mode** — books against the **same live data** as the
  `hotel-voice-booking-demo` PMS (its `knowledge_base`, rates, gotram rules, and
  — when Firebase is on — the shared Firestore that the Flutter PMS also uses).

You can run the whole thing without spending anything. Speech output uses
Microsoft's free `edge-tts` Telugu voices (no key, but needs internet).

---

## 1. Prerequisites

| Requirement | Why | How |
| --- | --- | --- |
| **Python 3.12+** | runtime | https://www.python.org/downloads/ (tick "Add to PATH") |
| **Ollama** + `llama3.2` | intent classification (optional — `--no-llm` skips it) | https://ollama.com/download, then `ollama pull llama3.2` |
| **Internet** (for voice) | `edge-tts` Telugu speech | only needed when speaking; text mode is offline |
| **A microphone** (for voice) | the spoken loop | any input device; the loop falls back to typing without one |
| **The demo project** (for live mode) | shares Karivena data | clone/keep `hotel-voice-booking-demo` next to this repo |

> On Windows, use the `py` launcher (not `python`). All commands below assume
> PowerShell.

---

## 2. Install

```powershell
# from the voice-agent/ folder
py -m pip install -r requirements.txt
```

This installs the core (SQLAlchemy, httpx, pydantic), plus the optional
speech deps (`faster-whisper`, `edge-tts`, `sounddevice`, `soundfile`). For
**live mode** you also need the demo's own deps (Firebase, etc.):

```powershell
py -m pip install -r ..\..\hotel-voice-booking-demo\requirements.txt
```

Make Telugu render correctly in the terminal (once per session):

```powershell
chcp 65001 > $null
$env:PYTHONIOENCODING = "utf-8"
```

---

## 3. Configure

```powershell
copy .env.example .env      # optional — defaults work out of the box
```

The defaults run SQLite mode, offline, no LLM required. Change `.env` only for
what you want to turn on (LLM model, cloud TTS, live data). See the inline
comments in `.env.example`.

---

## 4. Seed the local database (SQLite mode)

```powershell
py -m app.db.seed
```

This reads the Karivena `room_data.json` / `rate_config.json` (auto-discovered
from the sibling demo project) into a local `voice_agent.db`. Idempotent — safe
to re-run.

---

## 5. Run it

### Text mode (fastest to try)

```powershell
py run_text.py            # uses Ollama for intent (needs Ollama running)
py run_text.py --no-llm   # deterministic only, no Ollama
```

Type in Telugu, e.g.:

```
బుక్ చేయాలి → శ్రీశైలం → రేపు → రెండు రోజులు → ఇద్దరు → ఏసీ → రవి కుమార్ → అవును
```

### Voice mode (mic + speaker)

```powershell
$env:ALLOW_CLOUD_TTS = "true"   # needed for spoken Telugu (edge-tts)
py run_voice.py
py run_voice.py --no-llm        # deterministic intent
py run_voice.py --text          # skip the mic, still speaks replies
```

### Telephony (simulated call)

```powershell
py run_call.py                  # runs a scripted inbound call (mock adapter)
```

Real phone/SIP is out of scope — see `docs/TELEPHONY.md`.

---

## 6. Live mode (book against the Karivena PMS data)

Live mode routes availability + bookings through the demo's `knowledge_base`, so
a Telugu voice booking shows up in the same place as the PMS. Live bookings
require the caller's **phone, gotram, and email**, and the gotram must be in the
approved community list (the agent asks for these in Telugu).

**Step 1 — point at the demo (auto-discovered if it's a sibling folder):**

```powershell
$env:DATA_SOURCE = "live"
# only if it's not auto-found:
# $env:KARIVENA_DEMO_PATH = "C:\GIT\voice Z\hotel-voice-booking-demo"
```

**Step 2 — choose persistence:**

- **In-memory (simplest):** do nothing else. The demo keeps bookings in memory
  for the session. Great for testing the live flow without any cloud setup.
- **Shared Firestore (bookings appear in the Flutter PMS):** enable Firebase in
  the **demo** project (not here):
  1. In `hotel-voice-booking-demo/`, put the Firebase service-account key at
     `firebase-key.json` (Firebase console → Project settings → Service
     accounts → Generate new private key).
  2. In `hotel-voice-booking-demo/.env` set `FIREBASE_ENABLED=true`.
  The bridge calls the demo's `init_firebase()` for you, so live bookings then
  write to the shared `reservations` / `availability` Firestore collections.

**Step 3 — run any front-end in live mode:**

```powershell
$env:DATA_SOURCE = "live"
py run_text.py --no-llm
```

If the demo can't be found or imported, the agent automatically falls back to
SQLite mode and logs a warning, so it always runs.

---

## 7. Tests & evaluation

```powershell
py -m pytest               # full suite (offline; live bridge tests skip if demo absent)
py -m app.eval             # scenario evaluation report
```

---

## 8. Troubleshooting

- **Telugu shows as boxes/????** — run `chcp 65001` and set
  `$env:PYTHONIOENCODING="utf-8"` in the same terminal before running.
- **`python` opens the Microsoft Store** — use `py` instead.
- **No spoken audio** — set `$env:ALLOW_CLOUD_TTS="true"` and check internet;
  `edge-tts` needs both. Without them, replies are printed.
- **Ollama errors** — run `ollama serve` in another terminal and
  `ollama pull llama3.2`, or use `--no-llm`.
- **Live mode falls back to SQLite** — the demo folder wasn't found; set
  `KARIVENA_DEMO_PATH`, and `pip install -r` the demo's requirements.
- **Gotram rejected in live mode** — the spoken gotram isn't in the demo's
  `allowed_gotrams.json`. That's the demo's eligibility rule, not a bug.
