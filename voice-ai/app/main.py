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
from app.payments import (
    create_room_plus_donation_link, create_seva_donation_link,
    set_seva_amount, get_80g_donations,
    verify_webhook_signature, handle_payment_confirmed, parse_webhook_event,
    get_payment_methods, record_manual_payment, clear_cheque,
    get_donation_categories, get_sevas_by_category,
)
from app import roles as roles_mod
from app import rates as rates_mod
from app import checkout as checkout_mod
from app import invoice as invoice_mod
from app import certificate_80g as cert_mod
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
    """
    Mark a payment as completed (manual). Fires the automation loop:
    marks paid + auto-generates 80G certificate + WhatsApp push for donations.
    """
    result = handle_payment_confirmed(payment_id=payment_id)
    return JSONResponse(content=result)


@app.post("/api/payments/webhook")
async def api_payment_webhook(request: Request):
    """
    Razorpay webhook receiver. Verifies the signature, then fires the
    automation loop on payment_link.paid / payment.captured events:
    marks the payment paid and auto-issues the 80G certificate to WhatsApp.

    Configure in Razorpay dashboard -> Settings -> Webhooks:
      URL:    https://<your-host>/api/payments/webhook
      Secret: same value as RAZORPAY_WEBHOOK_SECRET in .env
      Events: payment_link.paid, payment.captured
    """
    raw = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not verify_webhook_signature(raw, signature):
        return JSONResponse(status_code=401, content={"error": "Invalid signature"})

    import json as _json
    try:
        payload = _json.loads(raw.decode("utf-8"))
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    parsed = parse_webhook_event(payload)
    # Only act on success events
    if parsed["event"] in ("payment_link.paid", "payment.captured", "order.paid"):
        result = handle_payment_confirmed(
            reference_id=parsed["reference_id"],
            payment_id=parsed["reference_id"],
        )
        return JSONResponse(content={"handled": True, "event": parsed["event"], "result": result})
    return JSONResponse(content={"handled": False, "event": parsed["event"]})


# === PAYMENT METHODS (Cash / Card / UPI / Cheque / Online) ===

@app.get("/api/payments/methods")
async def api_payment_methods():
    """List accepted payment methods (for dropdowns / voice options)."""
    return JSONResponse(content={"methods": get_payment_methods()})


@app.post("/api/payments/manual")
async def api_record_manual_payment(request: Request):
    """
    Record an offline payment (Cash / Card / UPI / Cheque) — typically for a
    walk-in booking taken at the counter. Requires generate_invoice permission
    (supervisor+). Cheque payments are recorded as pending until cleared.
    Body: {booking_id, amount, method, customer_name, customer_phone,
           reference, payment_type}
    """
    denied = _guard(request, "generate_invoice")
    if denied:
        return denied
    body = await request.json()
    result = record_manual_payment(
        booking_id=body.get("booking_id", ""),
        amount_inr=int(body.get("amount", 0)),
        method=body.get("method", ""),
        customer_name=body.get("customer_name", ""),
        customer_phone=body.get("customer_phone", ""),
        reference=body.get("reference", ""),
        payment_type=body.get("payment_type", "room_booking"),
        collected_by=_caller(request) or "staff",
    )
    code = 200 if result.get("success") else 400
    return JSONResponse(status_code=code, content=result)


@app.post("/api/payments/{payment_id}/clear-cheque")
async def api_clear_cheque(payment_id: str, request: Request):
    """Mark a pending cheque as cleared (supervisor+). Fires automation loop."""
    denied = _guard(request, "generate_invoice")
    if denied:
        return denied
    result = clear_cheque(payment_id)
    code = 200 if result.get("success") else 400
    return JSONResponse(status_code=code, content=result)


# === DONATIONS ===

@app.get("/api/donations/sevas")
async def api_sevas():
    """List available seva/donation plans (flat list)."""
    return JSONResponse(content={"sevas": get_seva_options()})


@app.get("/api/donations/categories")
async def api_donation_categories():
    """List donation category groups (General, Corpus Fund Donations, Corpus Fund Receipt)."""
    return JSONResponse(content={"categories": get_donation_categories()})


@app.get("/api/donations/grouped")
async def api_donations_grouped():
    """Donation options grouped by category (for grouped dropdowns / UI)."""
    return JSONResponse(content={"grouped": get_sevas_by_category()})


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
        "version": "4.0",
        "gotrams": get_gotram_count(),
        "payment_mode": get_payment_stats().get("mode"),
        "roles": roles_mod.ROLES,
        "rate_locations": len(rates_mod.get_all_rates()),
    }


# === RBAC HELPER ===

def _caller(request: Request) -> str:
    """
    Resolve the acting user's email from the X-User-Email header.
    (Firebase Auth token verification wires in here later when creds provided.)
    """
    return request.headers.get("X-User-Email", "").strip().lower()


def _guard(request: Request, permission: str):
    """
    Return None if allowed, else a JSONResponse(403/401).
    Usage: denied = _guard(request, "edit_rates"); if denied: return denied
    """
    email = _caller(request)
    allowed, reason = roles_mod.check_access(email, permission)
    if allowed:
        return None
    status = 401 if reason in ("No user identity provided", "User not found") else 403
    return JSONResponse(status_code=status, content={"error": reason, "permission": permission})


# === ROLES & USERS ===

@app.get("/api/roles")
async def api_roles():
    """List roles and their permission sets."""
    return JSONResponse(content={"roles": roles_mod.get_all_roles()})


@app.get("/api/users")
async def api_users(request: Request):
    """List staff users (super_admin only)."""
    denied = _guard(request, "manage_users")
    if denied:
        return denied
    return JSONResponse(content={"users": roles_mod.get_all_users()})


@app.post("/api/users")
async def api_create_user(request: Request):
    """Create a staff user (super_admin only)."""
    denied = _guard(request, "manage_users")
    if denied:
        return denied
    body = await request.json()
    result = roles_mod.create_user(
        email=body.get("email", ""),
        name=body.get("name", ""),
        role=body.get("role", "supervisor"),
        created_by=_caller(request) or "system",
    )
    code = 200 if result.get("success") else 400
    return JSONResponse(status_code=code, content=result)


@app.post("/api/users/{email}/role")
async def api_assign_role(email: str, request: Request):
    """Change a user's role (super_admin only)."""
    denied = _guard(request, "assign_roles")
    if denied:
        return denied
    body = await request.json()
    result = roles_mod.assign_role(email, body.get("role", ""))
    code = 200 if result.get("success") else 400
    return JSONResponse(status_code=code, content=result)


# === RATES (admin editable) ===

@app.get("/api/rates")
async def api_rates():
    """Full rate table (viewable by any authenticated staff)."""
    return JSONResponse(content={"rates": rates_mod.get_all_rates()})


@app.get("/api/rates/quote")
async def api_rate_quote(location: str = "", room_type: str = "AC",
                         check_in: str = "", check_out: str = "", rooms: int = 1):
    """Compute a price quote for a stay."""
    from datetime import date
    try:
        ci = date.fromisoformat(check_in)
        co = date.fromisoformat(check_out)
    except Exception:
        return JSONResponse(status_code=400, content={"error": "check_in/check_out must be YYYY-MM-DD"})
    quote = rates_mod.compute_total(location, room_type, ci, co, rooms)
    return JSONResponse(content=quote)


@app.post("/api/rates")
async def api_set_rate(request: Request):
    """Set a base rate (admin only)."""
    denied = _guard(request, "edit_rates")
    if denied:
        return denied
    body = await request.json()
    result = rates_mod.set_rate(
        location=body.get("location", ""),
        room_type=body.get("room_type", "AC"),
        base_rate=int(body.get("base_rate", 0)),
    )
    return JSONResponse(content=result)


@app.post("/api/rates/season")
async def api_add_season_rate(request: Request):
    """Add a seasonal rate override (admin only)."""
    denied = _guard(request, "edit_rates")
    if denied:
        return denied
    body = await request.json()
    result = rates_mod.add_season_rate(
        location=body.get("location", ""),
        room_type=body.get("room_type", "AC"),
        name=body.get("name", "Season"),
        from_date=body.get("from", ""),
        to_date=body.get("to", ""),
        rate=int(body.get("rate", 0)),
    )
    return JSONResponse(content=result)


# === SEVA AMOUNTS (admin editable) ===

@app.post("/api/sevas")
async def api_set_seva(request: Request):
    """Set/update a seva amount (admin only)."""
    denied = _guard(request, "set_seva_amounts")
    if denied:
        return denied
    body = await request.json()
    result = set_seva_amount(
        seva_id=body.get("seva_id", ""),
        amount=int(body.get("amount", 0)),
        name=body.get("name", ""),
        description=body.get("description", ""),
    )
    return JSONResponse(content=result)


# === PAYMENTS: combined + seva types ===

@app.post("/api/payments/room-donation")
async def api_room_plus_donation(request: Request):
    """Payment type 2: fixed room + customer-chosen donation (80G on donation)."""
    body = await request.json()
    result = create_room_plus_donation_link(
        booking_id=body.get("booking_id", ""),
        room_amount_inr=int(body.get("room_amount", 0)),
        donation_amount_inr=int(body.get("donation_amount", 0)),
        customer_name=body.get("customer_name", ""),
        customer_phone=body.get("customer_phone", ""),
    )
    return JSONResponse(content=result)


@app.post("/api/payments/seva")
async def api_seva_donation(request: Request):
    """Payment type 3: seva donation (predefined or custom amount, 80G)."""
    body = await request.json()
    result = create_seva_donation_link(
        customer_name=body.get("customer_name", ""),
        customer_phone=body.get("customer_phone", ""),
        seva_id=body.get("seva_id", ""),
        custom_amount_inr=int(body.get("custom_amount", 0)),
    )
    code = 200 if result.get("success", True) else 400
    return JSONResponse(status_code=code, content=result)


# === INVOICE (supervisor+) ===

@app.post("/api/invoice")
async def api_generate_invoice(request: Request):
    """Generate an invoice PDF for a booking (supervisor+)."""
    denied = _guard(request, "generate_invoice")
    if denied:
        return denied
    body = await request.json()
    result = invoice_mod.generate_invoice(body.get("booking", body))
    return JSONResponse(content=result)


@app.get("/api/invoice/{booking_id}/download")
async def api_download_invoice(booking_id: str):
    """Download a generated invoice PDF."""
    from pathlib import Path
    path = Path(invoice_mod._OUT_DIR) / f"invoice_{booking_id}.pdf"
    if path.exists():
        return FileResponse(path, media_type="application/pdf", filename=path.name)
    return JSONResponse(status_code=404, content={"error": "Invoice not found"})


# === 80G CERTIFICATE ===

@app.get("/api/certificates/80g")
async def api_list_80g():
    """List paid donations eligible for 80G certificates."""
    return JSONResponse(content={"donations": get_80g_donations()})


@app.post("/api/certificates/80g")
async def api_generate_80g(request: Request):
    """Generate an 80G certificate PDF for a donation (supervisor+)."""
    denied = _guard(request, "generate_invoice")
    if denied:
        return denied
    body = await request.json()
    result = cert_mod.generate_80g_certificate(body.get("donation", body))
    return JSONResponse(content=result)


@app.get("/api/certificates/80g/{payment_id}/download")
async def api_download_80g(payment_id: str):
    """Download a generated 80G certificate PDF."""
    from pathlib import Path
    path = Path(cert_mod._OUT_DIR) / f"80g_{payment_id}.pdf"
    if path.exists():
        return FileResponse(path, media_type="application/pdf", filename=path.name)
    return JSONResponse(status_code=404, content={"error": "Certificate not found"})


# === CHECKOUT (supervisor+, WhatsApp-driven) ===

@app.post("/api/checkout")
async def api_checkout(request: Request):
    """
    Trigger checkout for a booking (supervisor+).
    Body: {booking: {...}, donation_payment_id?: "..."}
    Runs: payment link + invoice + 80G (if donation) + WhatsApp push.
    """
    denied = _guard(request, "trigger_checkout")
    if denied:
        return denied
    body = await request.json()
    result = checkout_mod.process_checkout(
        booking=body.get("booking", body),
        donation_payment_id=body.get("donation_payment_id", ""),
    )
    return JSONResponse(content=result)


@app.post("/api/checkout/run-due")
async def api_run_due_checkouts(request: Request):
    """Run all due checkouts (end-of-stay scheduler; supervisor+)."""
    denied = _guard(request, "trigger_checkout")
    if denied:
        return denied
    from datetime import date
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    on_date = date.fromisoformat(body["date"]) if body.get("date") else None
    result = checkout_mod.run_due_checkouts(on_date)
    return JSONResponse(content=result)
