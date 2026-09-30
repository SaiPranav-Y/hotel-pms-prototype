# -*- coding: utf-8 -*-
"""
WhatsApp webhook server — the Telugu booking agent over WhatsApp text.

Runs a tiny FastAPI app that receives inbound WhatsApp messages, runs each one
through the SAME Telugu `DialogueSession` the voice agent uses, and sends the
Telugu reply back. The sender's WhatsApp number is used automatically as their
contact number (never asked).

Endpoints:
  GET  /            → info page
  GET  /health      → {"status": "ok", ...}
  GET  /webhook     → Meta webhook verification (echoes hub.challenge)
  POST /webhook     → inbound message; replies inline AND sends via provider

Run:
  py run_whatsapp.py                 # SQLite data (offline)
  set DATA_SOURCE=live & py run_whatsapp.py   # book into the live PMS data

Outbound sending is MOCK by default (messages are logged). Configure a real
provider (Meta Cloud API or a generic webhook) via .env — see .env.example.

Testing without WhatsApp: POST JSON to /webhook, e.g.
  {"from": "+919876543210", "text": "namaste"}
"""

import logging

from app import config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("run_whatsapp")


def build_app():
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse

    # Seed the local SQLite DB so location matching works in sqlite mode. (In
    # live mode the demo's knowledge_base is the source of truth; this is a
    # harmless no-op-ish idempotent seed.)
    try:
        from app.db.seed import seed
        seed(config.DB_PATH)
    except Exception as e:
        log.warning(f"seed skipped: {e}")

    from app.channels.whatsapp import get_channel
    from app.channels import whatsapp_io

    app = FastAPI(title="Karivena Satram — Telugu WhatsApp Booking",
                  version="1.0")
    channel = get_channel()

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return (
            "<h2>Karivena Satram — Telugu WhatsApp Booking</h2>"
            "<p>Webhook is live. POST messages to <code>/webhook</code>.</p>"
            f"<p>Data source: <b>{config.DATA_SOURCE}</b></p>"
        )

    @app.get("/health")
    async def health():
        return {"status": "ok", "data_source": config.DATA_SOURCE,
                "active_conversations": channel.active_count()}

    @app.get("/webhook")
    async def verify(request: Request):
        # Meta webhook verification handshake.
        params = request.query_params
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge", "")
        if mode == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
            return PlainTextResponse(challenge)
        return PlainTextResponse("verification failed", status_code=403)

    @app.post("/webhook")
    async def incoming(request: Request):
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "invalid JSON"})

        phone, text = whatsapp_io.parse_incoming(body)
        if not phone:
            return JSONResponse(status_code=400,
                                content={"error": "no sender phone in payload"})

        reply = channel.handle_incoming(phone, text)
        # Send the reply back to the user (MOCK-logs if no provider configured).
        try:
            whatsapp_io.send(phone, reply)
        except Exception as e:
            log.warning(f"send failed: {e}")
        return JSONResponse(content={"reply": reply})

    return app


# Importable ASGI app (uvicorn app / tests can import this).
app = build_app()


def main():
    import uvicorn
    print("=" * 60)
    print(f"  {config.HOTEL_NAME} — Telugu WhatsApp Booking (webhook)")
    print(f"  Data source: {config.DATA_SOURCE}")
    print(f"  Listening on http://{config.WHATSAPP_HOST}:{config.WHATSAPP_PORT}")
    print("  POST {\"from\":\"+91...\",\"text\":\"namaste\"} to /webhook")
    print("=" * 60)
    uvicorn.run("run_whatsapp:app", host=config.WHATSAPP_HOST,
                port=config.WHATSAPP_PORT, reload=False)


if __name__ == "__main__":
    main()
