# Branch: `working-app`

**The complete, runnable Karivena Satram Voice AI backend — clone, install, run.**

This branch is the deployable backend application, laid out at the repo root so it
runs with a single command. It shares git history with `karivena-voice-ai` (the full
monorepo that also contains the Flutter PMS app and the Twilio voice-gateway), so you
can diff and open PRs between the two.

## What's in this branch

| Path | Description |
|------|-------------|
| `app/` | Python/FastAPI platform — browser voice calls, dashboard, all business logic |
| `run.py` | Start the server (checks Ollama first) |
| `setup_and_run.bat` | One-click Windows setup + launch |
| `requirements.txt` | Python dependencies |
| `.env.example` | Every configuration option (copy to `.env`) |
| `test_*.py` | 82 automated tests across 4 suites |

The Flutter app, Twilio gateway, and Firebase export tooling are intentionally **not**
in this branch — they live in `karivena-voice-ai`. This branch is just the runnable
backend service.

## Runs free + local by default

- **LLM**: local Ollama (`llama3.2`) — no API keys
- **Storage**: in-memory (add `firebase-key.json` + `FIREBASE_ENABLED=true` to persist)
- **Payments**: mock Razorpay links (add keys to go live)
- **WhatsApp**: logged mock (add Meta Cloud API or webhook to go live)

## Capabilities

- Voice booking (Kaveri) in English/Telugu via the browser
- Gotram eligibility — mandatory community check on every booking
- Rate management (location × room type × season, admin-editable)
- 3 payment types — fixed room · room + donation · seva (80G eligible)
- Automated invoice + 80G certificate PDFs, pushed to WhatsApp
- WhatsApp-driven end-of-stay checkout
- Payment webhook automation — confirmed donation auto-issues its 80G certificate
- Role-based access — Supervisor / Admin / Super Admin
- Web dashboard, campaigns, escalation, analytics, search
- Call-recording consent + AI disclosure in the greeting (India compliance)

## Quick start

```bash
ollama serve && ollama pull llama3.2   # one-time
pip install -r requirements.txt
python run.py                          # -> http://localhost:8000
```

## Suggested GitHub Branch Description (paste in repo settings)

> Runnable Karivena Satram Voice AI backend (Kaveri) — FastAPI + Ollama, at repo root.
> Gotram eligibility, rate management, 3 payment types + 80G automation, auto
> invoice/certificate PDFs, WhatsApp checkout, role-based access. 100% local by
> default. 82 tests. Shares history with karivena-voice-ai.

## Status: v4.1 — 82 automated tests
