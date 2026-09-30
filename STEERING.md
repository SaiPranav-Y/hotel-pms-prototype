# Project Steering Document: Voice AI Hotel Booking Engine
**Target Branch:** `karivena-voice-ai`  
**Repository:** `hotel-pms-prototype`  
**Objective:** Enable automated voice-call room reservations powered by a self-hosted Ollama LLM that extracts booking parameters and triggers existing WhatsApp PMS workflows.

---

## 1. System Architecture & Information Flow

```
[ Caller ]
│ (PSTN Phone Call)
▼
[ Telephony Provider (Twilio) ]
│ (Webhook: Speech Transcription)
▼
[ Voice Gateway API (Node.js/Express) ]
│ (Call State & Session Management)
├──► [ Local Ollama Instance (http://localhost:11434) ]
│        └─ (System Prompt + Structured Extraction)
│
└──► [ PMS Core API / Firebase Firestore ]
         └─ (Room Check -> Create Booking -> WhatsApp Confirmation)
```

---

## 2. Technical Stack

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Telephony** | Twilio Voice | Inbound call routing, `<Gather>` STT & `<Say>` TTS (Polly.Aditi) |
| **Edge Tunneling** | Ngrok | Exposing local server via HTTPS |
| **Voice Gateway** | Node.js (Express) | Call orchestration, TwiML generation, session management |
| **LLM Core** | Ollama (`llama3.2:3b`) | Real-time slot-filling, JSON extraction |
| **Session Cache** | In-Memory Map | Conversation history per `CallSid` |
| **PMS Integration** | Firebase Firestore | `reservations` collection (same as Flutter app + WhatsApp bot) |

---

## 3. Implementation Status

### Phase 1: Telephony Pipeline ✅
- [x] Express server with Twilio webhook endpoints
- [x] TwiML greeting with `<Gather input="speech">`
- [x] Speech recognition: `speechTimeout="auto"`, `speechModel="phone_call"`, `language="en-IN"`
- [x] Session manager keyed by `CallSid`
- [x] Concurrency limiter (max 3 calls, graceful rejection)

### Phase 2: Ollama Conversation Engine ✅
- [x] Ollama REST client with streaming support
- [x] Voice-tuned system prompt (1-2 sentences, no formatting)
- [x] Slot-filling: location, check_in, check_out, room_type, guests, guest_name
- [x] JSON extraction when all slots filled
- [x] Confirmation flow (yes/no before booking)

### Phase 3: PMS Booking Bridge ✅
- [x] Firebase Admin SDK initialization
- [x] Writes to `reservations` collection (same schema as Flutter PMS)
- [x] Reservation mode: "Voice Assistant"
- [x] Availability check (overlap query)
- [x] Voice confirmation: "Booking confirmed. Details sent to WhatsApp."

### Phase 4: Latency & Resilience ✅
- [x] Streaming support (first sentence sent while LLM generates rest)
- [x] Max 15 turns safety limit per call
- [x] Silence/no-speech fallback prompts
- [x] Error recovery: "I apologize, could you repeat that?"
- [x] Graceful busy signal when at capacity

### Phase 5: Community, Payments & Donations ✅
- [x] Gotram eligibility — MANDATORY field on every reservation/booking
- [x] Approved gotram list (file/Firestore/default) with fuzzy matching
- [x] Mandatory field validation: name, gotram, location, room type, stay span
- [x] Razorpay room payment link (fixed amount from room total)
- [x] Donations — flexible (any amount) + 6 fixed seva plans
- [x] WhatsApp confirmation with payment + donation links
- [x] Dashboard: Gotram column, Payments/Donations/Gotrams tabs, revenue stats
- [x] 39 automated tests passing (27 core + 12 payment/gotram)

---

## 4. Directory Structure

```
hotel-pms-prototype/
├── voice-gateway/              # Twilio + Ollama telephony server
│   ├── src/
│   │   ├── config/voiceConfig.js
│   │   ├── controllers/voiceController.js
│   │   ├── services/
│   │   │   ├── ollamaService.js
│   │   │   ├── sessionStore.js
│   │   │   └── pmsBridge.js
│   │   ├── prompts/receptionistPrompt.js
│   │   └── server.js
│   ├── .env.example
│   ├── package.json
│   └── README.md
├── voice-ai/                   # Browser-based voice + full platform (Python)
│   └── (Phase 1-3 code)
├── lib/                        # Flutter PMS app
├── STEERING.md                 # This file
└── .firebaserc
```

---

## 5. Verification Checklist

- [ ] `npm start` in voice-gateway starts without errors
- [ ] `/health` returns Ollama status and active call count
- [ ] Twilio webhook receives speech and returns TwiML
- [ ] Ollama responds in <2 seconds on local hardware
- [ ] Complete booking creates document in Firestore `reservations`
- [ ] 4th concurrent call gets polite rejection message
- [ ] Call that drops mid-way does NOT create a partial reservation
