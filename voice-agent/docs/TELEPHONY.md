# Telephony (Phases 5-6) — Dev Path & Adapter Seam

Per the project steering, **real telephony is out of scope for the demo**:

> Software is free; a real phone number is not. Demo path = text-mode + local
> mic/speaker (LAN), no telephony provider.

So this repo ships a **telephony adapter seam** — the interface and wiring
needed to attach a phone channel — plus a local **MockTelephony** you can run
and test today, but it does **not** stand up a live SIP server or buy a number.
This doc explains how the seam works and how to wire a real channel when you
choose to.

---

## How it fits

The dialogue core is transport-agnostic. Three front-ends feed it the same way:

```
run_text.py   : keyboard        → DialogueSession → console
run_voice.py  : mic → STT       → DialogueSession → TTS → speaker
run_call.py   : phone → STT     → DialogueSession → TTS → phone   ← this doc
```

Everything specific to "it's a phone call" lives behind one interface,
`app/telephony/base.py::TelephonyAdapter`:

| Method | Responsibility |
| --- | --- |
| `start()` / `stop()` | register/close the channel |
| `wait_for_call()` | block until an inbound call; return a `CallSession` |
| `receive_audio(call)` | next chunk of caller audio (or transcribed text) |
| `send_audio(call, path)` | play an agent audio file to the caller |
| `hangup(call)` | end the call |

`run_call.py` is the single place that ties a `TelephonyAdapter` to the shared
`DialogueSession`. Swapping channels never touches the dialogue, STT, or TTS.

---

## Run the mock now (no hardware)

```powershell
py run_call.py
```

This simulates one inbound call with scripted Telugu turns and prints the full
transcript. It exercises the exact call lifecycle a real adapter must follow
(`start → wait_for_call → receive_audio* → send_audio* → hangup`).

---

## Wiring a real channel (when you want it)

### Option A — Asterisk + SIP softphone (free, local, recommended for dev)

This is the **free** dev path: run Asterisk on your machine/LAN and connect a
free softphone (e.g. Zoiper, Linphone, MicroSIP). No carrier or number needed —
you "call" the agent from the softphone over the LAN.

1. Install Asterisk (Linux/WSL or a Docker image).
2. Use the templates in `deploy/asterisk/` as a starting point:
   - `pjsip.conf` — a SIP endpoint for your softphone,
   - `extensions.conf` — a dialplan that routes the endpoint to the agent app
     via **ARI** (Asterisk REST Interface) or **AGI/AudioSocket**.
3. Implement an `AsteriskTelephony(TelephonyAdapter)`:
   - Recommended transport: **AudioSocket** (Asterisk streams raw PCM over a TCP
     socket) or **ARI externalMedia** — both give you a byte stream you feed to
     the existing `FasterWhisperSTT`, and you stream TTS audio back the same way.
   - Map the SIP caller id to `CallSession.caller_id` so bookings get a callback
     number.
4. Register it in `get_telephony()` as `"asterisk"` and point `run_call.py` at it.

> Audio format note: Asterisk channels are typically 8 kHz slin/ulaw. Resample
> to 16 kHz before STT (`app/audio/stt.py::_resample_to_16k` already does this),
> and resample TTS output down to the channel rate before sending.

### Option B — a real phone number (out of scope, not free)

A DID/number needs a provider (Twilio, Plivo, a SIP trunk, etc.) and costs
money, so it is intentionally **not** implemented. The seam is identical: write
a `TelephonyAdapter` that bridges the provider's media stream (Twilio Media
Streams over WebSocket, a SIP trunk into Asterisk, etc.) to the same pipeline.
Keep credentials in `.env`, never in code.

---

## What is and isn't included

| Item | Status |
| --- | --- |
| `TelephonyAdapter` interface | ✅ implemented (`app/telephony/base.py`) |
| `MockTelephony` + `run_call.py` | ✅ implemented, tested |
| Asterisk config templates | ✅ starting templates in `deploy/asterisk/` |
| Live Asterisk/SIP server | ⛔ you run this on your machine (see Option A) |
| Real phone number / carrier | ⛔ out of scope, not free |

The point of the seam: when you're ready for a real channel, you implement one
class and change one factory line — the Telugu dialogue, booking logic, STT, and
TTS all stay exactly as they are.
