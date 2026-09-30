# Karivena Voice Gateway — Twilio + Ollama

Real phone call → Twilio STT → Local Ollama LLM → TwiML TTS → Caller hears response.

## Quick Start

```bash
cd voice-gateway
npm install
cp .env.example .env   # Fill in your Twilio credentials
npm start
```

Then in another terminal:
```bash
ngrok http 3000
```

Copy the ngrok HTTPS URL into your `.env` as `PUBLIC_URL`, and set it as your Twilio phone number's Voice webhook:
```
POST https://xxxx.ngrok-free.app/voice/incoming
```

## Prerequisites

- Node.js 18+
- Ollama running locally (`ollama serve` + `ollama pull llama3.2:3b`)
- Twilio account (free trial: $15 credit)
- ngrok (free: https://ngrok.com/download)

## How It Works

```
Caller dials Twilio number
    │
    ▼
Twilio → POST /voice/incoming (greeting + Gather)
    │
    ▼
Caller speaks → Twilio STT → POST /voice/process
    │
    ▼
Server → Ollama (local LLM) → response text
    │
    ▼
Server returns TwiML <Say> → Twilio speaks to caller
    │
    ▼
(Loop until all booking details collected)
    │
    ▼
Ollama outputs JSON → POST /voice/confirm
    │
    ▼
Caller says "yes" → Firebase reservation created
    │
    ▼
"Booking confirmed. Details sent to WhatsApp. Goodbye."
```

## Architecture

| Component | File | Role |
|-----------|------|------|
| Server | `src/server.js` | Express app, route definitions |
| Controller | `src/controllers/voiceController.js` | Twilio webhook handlers |
| Ollama | `src/services/ollamaService.js` | LLM chat + streaming + JSON extraction |
| Sessions | `src/services/sessionStore.js` | Per-call memory (keyed by CallSid) |
| PMS | `src/services/pmsBridge.js` | Firebase Firestore reservation writer |
| Prompt | `src/prompts/receptionistPrompt.js` | Voice-tuned system prompt |
| Config | `src/config/voiceConfig.js` | All settings from .env |

## Concurrency

Default: max 3 concurrent calls. If a 4th caller dials in, they hear:
"All agents are busy. Please try again in a few minutes."

Change in `.env`: `MAX_CONCURRENT_CALLS=5`

## Latency Tips

- Use `llama3.2:3b` (faster than 8b)
- Keep `num_predict: 80` (short responses)
- Ensure Ollama has GPU access for <1s generation
- Streaming support built-in (sends first sentence immediately)
