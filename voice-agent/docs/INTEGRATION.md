# Integration — Telugu Voice Agent ↔ Karivena PMS (`hotel-voice-booking-demo`)

This document explains how the offline Telugu voice agent (`voice-agent/`) plugs
into the live Karivena data layer that lives in the sibling
`hotel-voice-booking-demo` project, so a Telugu voice booking lands in the same
place as a PMS booking.

## The two projects

| | `voice-agent/` (this project) | `hotel-voice-booking-demo/` |
| --- | --- | --- |
| Role | Telugu-first dialogue: STT → dialogue → TTS | The data + business layer + PMS |
| Data | local SQLite (seeded from Karivena JSON) | `knowledge_base` + rates + gotram + Firestore |
| Speech | faster-whisper (STT), edge-tts (TTS) | its own web/voice UI |
| Booking rules | name only | **name + phone + gotram + email**, gotram must be approved |

Both happen to use the same local stack (Ollama / Whisper / edge-tts) and the
same Karivena room data — the integration reuses the demo's data layer rather
than duplicating it.

## The seam: a pluggable `DataSource`

The Telugu dialogue never touches a database directly. It talks to a
`DataSource` (`app/tools/datasource.py`), which has two implementations:

```
DialogueSession ──► DataSource ──┬── SqliteDataSource   (offline, self-contained)
                                 └── LiveDataSource     (demo knowledge_base + Firestore)
```

`DATA_SOURCE=sqlite|live` (env) picks one. The dialogue asks the data source
`extra_required` to learn which extra slots to collect:

- `SqliteDataSource.extra_required = ()` → asks name only (unchanged offline flow).
- `LiveDataSource.extra_required = ("phone", "gotram", "email")` → the dialogue
  additionally asks for phone, gotram, and email, in Telugu, before confirming.

If `DATA_SOURCE=live` but the demo can't be imported, the factory falls back to
SQLite and logs a warning — the agent always runs.

## The bridge: importing the demo in-process

Both projects use a top-level package called `app`, so we can't just
`import app.knowledge_base` — it would collide with our own `app`. The bridge
(`app/integration/karivena.py`) solves this:

1. `bridge()` locates the demo (auto-discovered sibling folder or
   `KARIVENA_DEMO_PATH`), puts its root on `sys.path`, and imports the demo's
   `knowledge_base`, `rates`, `vernacular`, `gotram`, `firebase_store` (plus the
   modules `create_booking` loads lazily: `validators`, `payments`, `whatsapp`,
   `audit`). It snapshots that demo `app.*` module set.
2. Every call into the demo runs inside `bridge().use_demo_app()`, a context
   manager that swaps `sys.modules['app*']` to the demo's set for the duration
   of the call — so the demo's lazy `from app import validators` resolves to the
   DEMO's package — then restores ours. This keeps the two `app` packages from
   stepping on each other.

`init_firebase()` is called once during bridging; it's a no-op unless the demo's
`.env` has `FIREBASE_ENABLED=true` and a `firebase-key.json` is present.

## Data flow — a live Telugu booking

```
Caller speaks Telugu
      │  (voice mode) faster-whisper STT → text
      ▼
DialogueSession (state machine, deterministic slot parsing)
      │  collects: location, dates, nights, guests, room type,
      │            name, phone, gotram, email   (Telugu prompts)
      ▼
LiveDataSource.check_availability(...)  ─► demo knowledge_base.check_availability
      │                                      (rooms from room_data.json, price from rates.py)
      ▼
confirm summary in Telugu  ──►  caller says "అవును"
      ▼
LiveDataSource.create_booking(...)  ─► demo knowledge_base.create_booking
      │   • validates + normalizes (validators.py)
      │   • gotram eligibility (gotram.match_gotram vs allowed_gotrams.json)
      │   • prices via rates.py
      │   • Firestore atomic booking (reservations + availability counters)
      │     — the SAME counters the Flutter PMS books against (no double-booking)
      │   • Razorpay payment + donation links (mock unless keys set)
      │   • WhatsApp confirmation (mock unless configured)
      ▼
Telugu confirmation spoken:  "మీ బుకింగ్ ధృవీకరించబడింది. మీ బుకింగ్ నంబర్ BK-XXXX …"
```

## Location & room-type handling

Callers say Telugu/colloquial names (`శ్రీశైలం`, `balaji`, `sai baba`). In live
mode the adapter resolves these through the demo's `vernacular.normalize_location`,
which maps them to the canonical names in `room_data.json`
(`Srisailam`, `Tirupathi`, `Shiridi`, …). Room type collapses to `ac` / `nonac`.
Available live locations: Brundavanam, Kasi, Mahanandi, Naimisaranyam,
Tirupathi, Vruddasramam, Rameswaram, Srisailam, Shiridi (Arunachalam has no rooms).

## Shared Firestore schema (when Firebase is on)

The demo owns these collections; the bridge just calls into it:

- `reservations` — one doc per booking (`BK-XXXXXXXX`), same schema the Flutter
  PMS reads/writes.
- `availability` — per-(location, date) counter docs
  (`<templeKey>__<yyyy-MM-dd>`) with `capacity` + `booked`, bumped atomically in
  a transaction so a voice booking and a walk-in can't take the same last room.

## What the integration deliberately does NOT change

- The demo project is imported, never modified. All Karivena business rules
  (gotram, rates, payments, WhatsApp, 80G, roles) stay in the demo and run as-is.
- The offline SQLite path is untouched — every existing test still passes.
- No secrets are read or committed. `firebase-key.json`, `.env`, and
  `staff_credentials.txt` remain the demo's own, git-ignored files.
