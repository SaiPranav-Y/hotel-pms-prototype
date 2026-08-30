"""
Main FastAPI — Karivena Satram AI Calling Platform.
All routes for voice, bookings, contacts, campaigns, analytics, escalation, search.
"""

import logging
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from app.config import HOST, PORT
from app.call_handler import handle_voice_websocket, active_calls
from app.knowledge_base import (
    get_all_bookings, get_all_call_logs, get_all_customers,
    get_all_locations, ORG_INFO, update_call_workflow, WORKFLOW_STATUSES,
)
from app.contacts import (
    upsert_contact, get_contact, get_all_contacts, add_note,
    set_contact_status, get_contact_count,
)
from app.campaigns import (
    create_campaign, get_campaign, get_all_campaigns,
    update_campaign_status, record_call_attempt, get_campaign_stats,
)
from app.escalation import (
    get_escalation_config, set_escalation_numbers, check_escalation_needed,
    create_escalation, resolve_escalation, get_all_escalations,
    get_pending_escalations, get_escalation_stats,
)
from app.analytics import compute_analytics, compute_location_analytics, compute_source_analytics
from app.search import search_transcripts, global_search
from app.recorder import get_recording_path, get_recording, get_all_recordings
from app.gotram import get_all_gotrams, add_gotram, is_allowed, match_gotram, get_gotram_count
from app.payments import (
    create_room_payment_link, create_donation_link, get_seva_options,
    get_all_payments, get_payment, mark_paid, get_payment_stats,
)
from app.whatsapp import compose_donation_only_message, send_whatsapp, get_sent_log
from app.pages.call_page import CALL_PAGE_HTML
from app.pages.dashboard_page import DASHBOARD_HTML

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Karivena Satram — Kaveri AI Caller", version="2.0")

# Initialize Firebase
from app.firebase_store import init_firebase
init_firebase()


# === VOICE ===

@app.websocket("/voice")
async def voice_ws(websocket: WebSocket):
    await handle_voice_websocket(websocket)


# === BOOKINGS ===

@app.get("/api/bookings")
async def api_bookings():
    return JSONResponse(content={"bookings": get_all_bookings()})


# === CALLS ===

@app.get("/api/calls")
async def api_calls():
    calls = list(active_calls.values())
    logs = get_all_call_logs()
    log_ids = {c["call_id"] for c in logs}
    for call in calls:
        if call["call_id"] not in log_ids:
            logs.append(call)
    logs.sort(key=lambda c: c.get("start_time", c.get("created_at", 0)), reverse=True)
    safe = []
    for c in logs:
        sc = {**c}
        if "transcript" in sc:
            sc["transcript"] = [{"role": t["role"], "text": t["text"]} for t in sc["transcript"]]
        safe.append(sc)
    return JSONResponse(content={"calls": safe})


@app.post("/api/calls/{call_id}/workflow")
async def api_update_workflow(call_id: str, request: Request):
    body = await request.json()
    new_status = body.get("status", "")
    if new_status not in WORKFLOW_STATUSES:
        return JSONResponse(status_code=400, content={"error": f"Invalid. Use: {WORKFLOW_STATUSES}"})
    success = update_call_workflow(call_id, new_status)
    if not success:
        return JSONResponse(status_code=404, content={"error": "Call not found"})
    return JSONResponse(content={"success": True, "workflow_status": new_status})


# === CONTACTS ===

@app.get("/api/contacts")
async def api_contacts():
    # Merge knowledge_base customers with contacts module
    from app.contacts import get_all_contacts as get_contacts_list
    return JSONResponse(content={"contacts": get_contacts_list()})


@app.post("/api/contacts")
async def api_create_contact(request: Request):
    body = await request.json()
    contact = upsert_contact(
        phone=body.get("phone", ""),
        name=body.get("name", ""),
        age=body.get("age", ""),
        location=body.get("location", ""),
        tags=body.get("tags", []),
    )
    return JSONResponse(content={"contact": contact})


@app.get("/api/contacts/{phone}")
async def api_get_contact(phone: str):
    c = get_contact(phone)
    if not c:
        return JSONResponse(status_code=404, content={"error": "Contact not found"})
    return JSONResponse(content={"contact": c})


@app.post("/api/contacts/{phone}/note")
async def api_add_note(phone: str, request: Request):
    body = await request.json()
    success = add_note(phone, body.get("note", ""))
    return JSONResponse(content={"success": success})


@app.post("/api/contacts/{phone}/status")
async def api_set_status(phone: str, request: Request):
    body = await request.json()
    success = set_contact_status(phone, body.get("status", ""))
    return JSONResponse(content={"success": success})


# === CAMPAIGNS ===

@app.get("/api/campaigns")
async def api_campaigns():
    return JSONResponse(content={"campaigns": get_all_campaigns(), "stats": get_campaign_stats()})


@app.post("/api/campaigns")
async def api_create_campaign(request: Request):
    body = await request.json()
    campaign = create_campaign(
        name=body.get("name", "Untitled Campaign"),
        contacts=body.get("contacts", []),
        scheduled_date=body.get("scheduled_date", ""),
        scheduled_time=body.get("scheduled_time", ""),
        max_retries=body.get("max_retries", 3),
        message_template=body.get("message_template", ""),
        notes=body.get("notes", ""),
    )
    return JSONResponse(content={"campaign": campaign})


@app.post("/api/campaigns/{campaign_id}/status")
async def api_campaign_status(campaign_id: str, request: Request):
    body = await request.json()
    success = update_campaign_status(campaign_id, body.get("status", ""))
    return JSONResponse(content={"success": success})


# === ESCALATION ===

@app.get("/api/escalations")
async def api_escalations():
    return JSONResponse(content={
        "escalations": get_all_escalations(),
        "config": get_escalation_config(),
        "stats": get_escalation_stats(),
    })


@app.post("/api/escalations/config")
async def api_set_escalation_config(request: Request):
    body = await request.json()
    numbers = body.get("numbers", [])
    success = set_escalation_numbers(numbers)
    return JSONResponse(content={"success": success, "config": get_escalation_config()})


@app.post("/api/escalations/{escalation_id}/resolve")
async def api_resolve_escalation(escalation_id: str):
    success = resolve_escalation(escalation_id)
    return JSONResponse(content={"success": success})


# === ANALYTICS ===

@app.get("/api/analytics")
async def api_analytics():
    calls = get_all_call_logs()
    bookings = get_all_bookings()
    analytics = compute_analytics(calls, bookings)
    analytics["by_location"] = compute_location_analytics(bookings)
    analytics["by_source"] = compute_source_analytics(bookings)
    return JSONResponse(content=analytics)


# === SEARCH ===

@app.get("/api/search")
async def api_search(q: str = ""):
    if not q:
        return JSONResponse(content={"query": "", "calls": [], "contacts": []})
    calls = get_all_call_logs()
    contacts = get_all_contacts()
    results = global_search(calls, contacts, q)
    results["total_results"] = len(results["calls"]) + len(results["contacts"])
    return JSONResponse(content=results)


# === RECORDINGS ===

@app.get("/api/recordings")
async def api_recordings():
    return JSONResponse(content={"recordings": get_all_recordings()})


@app.get("/api/recordings/{call_id}")
async def api_get_recording(call_id: str):
    path = get_recording_path(call_id)
    if path and path.exists():
        info = get_recording(call_id)
        mime = info.get("mime_type", "audio/webm") if info else "audio/webm"
        return FileResponse(path, media_type=mime, filename=path.name)
    return JSONResponse(status_code=404, content={"error": "Recording not found"})


# === INFO ===

@app.get("/api/locations")
async def api_locations():
    return JSONResponse(content={"locations": get_all_locations()})


@app.get("/api/info")
async def api_info():
    return JSONResponse(content={"org": ORG_INFO, "locations": get_all_locations()})


# === PAGES ===

@app.get("/", response_class=HTMLResponse)
async def call_page():
    return CALL_PAGE_HTML


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return DASHBOARD_HTML


# === GOTRAM MANAGEMENT ===

@app.get("/api/gotrams")
async def api_gotrams():
    """List all approved gotrams."""
    return JSONResponse(content={"gotrams": get_all_gotrams(), "count": get_gotram_count()})


@app.post("/api/gotrams")
async def api_add_gotram(request: Request):
    """Add a gotram to the approved list."""
    body = await request.json()
    name = body.get("name", "")
    success = add_gotram(name)
    return JSONResponse(content={"success": success, "count": get_gotram_count()})


@app.get("/api/gotrams/check")
async def api_check_gotram(gotram: str = ""):
    """Check if a gotram is approved. Returns matched canonical name."""
    matched = match_gotram(gotram)
    return JSONResponse(content={
        "input": gotram,
        "allowed": matched is not None,
        "matched": matched,
    })


# === PAYMENTS ===

@app.get("/api/payments")
async def api_payments():
    """List all payment links + stats."""
    return JSONResponse(content={
        "payments": get_all_payments(),
        "stats": get_payment_stats(),
    })


@app.post("/api/payments/room")
async def api_create_room_payment(request: Request):
    """Create a room payment link (fixed amount)."""
    body = await request.json()
    result = create_room_payment_link(
        booking_id=body.get("booking_id", ""),
        amount_inr=int(body.get("amount", 0)),
        customer_name=body.get("customer_name", ""),
        customer_phone=body.get("customer_phone", ""),
    )
    return JSONResponse(content=result)


@app.post("/api/payments/{payment_id}/paid")
async def api_mark_paid(payment_id: str):
    """Mark a payment as completed (webhook or manual)."""
    success = mark_paid(payment_id)
    return JSONResponse(content={"success": success})


# === DONATIONS ===

@app.get("/api/donations/sevas")
async def api_sevas():
    """List available seva donation plans."""
    return JSONResponse(content={"sevas": get_seva_options()})


@app.post("/api/donations")
async def api_create_donation(request: Request):
    """
    Create a donation link.
    Body: {customer_name, customer_phone, amount (0=flexible), seva_id (optional)}
    """
    body = await request.json()
    result = create_donation_link(
        customer_name=body.get("customer_name", "Devotee"),
        customer_phone=body.get("customer_phone", ""),
        amount_inr=int(body.get("amount", 0)),
        seva_id=body.get("seva_id", ""),
    )
    # Optionally send via WhatsApp
    if body.get("send_whatsapp") and body.get("customer_phone"):
        msg = compose_donation_only_message(body.get("customer_name", "Devotee"), result["link"])
        send_whatsapp(body["customer_phone"], msg)
        result["whatsapp_sent"] = True
    return JSONResponse(content=result)


# === WHATSAPP ===

@app.get("/api/whatsapp/log")
async def api_whatsapp_log():
    """Get log of sent WhatsApp messages."""
    return JSONResponse(content={"messages": get_sent_log()})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "karivena-kaveri-ai",
        "version": "3.0",
        "gotrams": get_gotram_count(),
        "payment_mode": get_payment_stats().get("mode"),
    }
