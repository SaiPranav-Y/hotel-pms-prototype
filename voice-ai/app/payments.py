"""
Razorpay Payment Module — payment links for room bookings and donations.

Two flows:
  1. Room payment  — FIXED amount (from booking total)
  2. Donation      — FLEXIBLE amount, optionally linked to a Seva

Set your Razorpay keys in .env:
  RAZORPAY_KEY_ID=rzp_live_xxxxx  (or rzp_test_xxxxx)
  RAZORPAY_KEY_SECRET=xxxxx

If keys are not set, the module runs in MOCK mode (generates fake links so
the rest of the pipeline works end-to-end for demos).
"""

import os
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
# Webhook secret configured in the Razorpay dashboard (Settings -> Webhooks).
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
# Trust UPI VPA (e.g. "karivena@sbi") — enables a working UPI deep link even
# before Razorpay live keys are set. Payee name shown in the UPI app.
UPI_VPA = os.getenv("UPI_VPA", "")
UPI_PAYEE_NAME = os.getenv("UPI_PAYEE_NAME", "Karivena Satram")

_client = None
_mock_mode = True

# In-memory store of created payment links (also synced to Firebase)
_payment_links: dict[str, dict] = {}


# === DONATION OPTIONS (Karivena Satram — ADMIN editable) ===
# All donations are 80G tax-exempt eligible (certificate issued post-donation).
# Three categories:
#   1. General Donation      — any amount the donor chooses (allow_custom, amount 0)
#   2. Corpus Fund Donations — fixed capital-fund contributions
#   3. Corpus Fund Receipt   — sponsorship / seva receipts (fixed amounts)
DONATION_CATEGORIES = [
    {"id": "general", "name": "General Donation"},
    {"id": "corpus_fund_donation", "name": "Corpus Fund Donations"},
    {"id": "corpus_fund_receipt", "name": "Corpus Fund Receipt"},
]

SEVA_OPTIONS = [
    # 1. General Donation — donor decides the amount
    {"id": "general", "name": "General Donation", "amount": 0,
     "category": "general", "description": "Donate any amount of your choosing",
     "allow_custom": True},

    # 2. Corpus Fund Donations
    {"id": "room_construction", "name": "Room Construction", "amount": 500000,
     "category": "corpus_fund_donation", "description": "Sponsor construction of a room",
     "allow_custom": True},
    {"id": "bhudanam", "name": "Bhudanam (Land Donation)", "amount": 100000,
     "category": "corpus_fund_donation", "description": "Contribution towards land",
     "allow_custom": True},

    # 3. Corpus Fund Receipt (sponsorships / sevas)
    {"id": "one_day_annadanam", "name": "One Day Annadhanam", "amount": 2000,
     "category": "corpus_fund_receipt", "description": "Sponsor one day of Annadanam",
     "allow_custom": True},
    {"id": "five_day_annadanam", "name": "Five Day Annadhanam", "amount": 15000,
     "category": "corpus_fund_receipt", "description": "Sponsor five days of Annadanam",
     "allow_custom": True},
    {"id": "nityannadanam", "name": "Nityannadanam", "amount": 30000,
     "category": "corpus_fund_receipt", "description": "Perpetual daily Annadanam",
     "allow_custom": True},
    {"id": "marriage_day", "name": "Marriage Day", "amount": 3000,
     "category": "corpus_fund_receipt", "description": "Annadanam on your marriage day",
     "allow_custom": True},
    {"id": "birthday", "name": "Birthday", "amount": 2000,
     "category": "corpus_fund_receipt", "description": "Annadanam on your birthday",
     "allow_custom": True},
    {"id": "special_occasion", "name": "Special Occasion", "amount": 6000,
     "category": "corpus_fund_receipt", "description": "Annadanam for a special occasion",
     "allow_custom": True},
    {"id": "maharaja_poshakulu", "name": "Maharaja Poshakulu", "amount": 100000,
     "category": "corpus_fund_receipt", "description": "Maharaja patron sponsorship",
     "allow_custom": True},
    {"id": "budhana_poshakulu", "name": "Budhana Poshakulu", "amount": 10000,
     "category": "corpus_fund_receipt", "description": "Budhana patron sponsorship",
     "allow_custom": True},
    {"id": "vedanidhi", "name": "Vedanidhi", "amount": 5000,
     "category": "corpus_fund_receipt", "description": "Support Vedic scholars / education",
     "allow_custom": True},
    {"id": "gonidhi", "name": "Gonidhi (Gau Seva)", "amount": 5000,
     "category": "corpus_fund_receipt", "description": "Cow protection contribution",
     "allow_custom": True},
]


def get_donation_categories() -> list[dict]:
    """Return the donation category groups."""
    return DONATION_CATEGORIES


def get_sevas_by_category() -> dict:
    """Group the donation/seva options by category (for grouped UI)."""
    grouped = {c["id"]: {"name": c["name"], "options": []} for c in DONATION_CATEGORIES}
    for s in SEVA_OPTIONS:
        cat = s.get("category", "general")
        grouped.setdefault(cat, {"name": cat, "options": []})
        grouped[cat]["options"].append(s)
    return grouped


def load_sevas_from_firestore():
    """Load admin-configured seva amounts from Firestore (overrides defaults)."""
    global SEVA_OPTIONS
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            docs = list(_db.collection("sevas").stream())
            if docs:
                SEVA_OPTIONS = [d.to_dict() for d in docs]
                logger.info(f"Sevas loaded from Firestore: {len(SEVA_OPTIONS)}")
    except Exception:
        pass


def set_seva_amount(seva_id: str, amount: int, name: str = "", description: str = "") -> dict:
    """Update a seva's amount (ADMIN only — enforced at route level)."""
    for s in SEVA_OPTIONS:
        if s["id"] == seva_id:
            s["amount"] = int(amount)
            if name:
                s["name"] = name
            if description:
                s["description"] = description
            _persist_seva(s)
            return {"success": True, "seva": s}
    # New seva
    new_seva = {
        "id": seva_id, "name": name or seva_id, "amount": int(amount),
        "description": description, "allow_custom": True,
    }
    SEVA_OPTIONS.append(new_seva)
    _persist_seva(new_seva)
    return {"success": True, "seva": new_seva}


def _persist_seva(seva: dict):
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("sevas").document(seva["id"]).set(seva)
    except Exception:
        pass


# === PAYMENT METHODS ===
# Karivena accepts these payment methods. "online" uses the Razorpay link
# (WhatsApp checkout); the others are recorded manually by staff at the counter
# (typical for walk-in bookings) or reconciled after an offline transfer.
PAYMENT_METHODS = [
    {"id": "cash", "name": "Cash", "online": False, "needs_reference": False,
     "reference_label": ""},
    {"id": "card", "name": "Card (Credit/Debit)", "online": False, "needs_reference": True,
     "reference_label": "Card txn / approval code"},
    {"id": "upi", "name": "UPI", "online": False, "needs_reference": True,
     "reference_label": "UPI transaction ID / UTR"},
    {"id": "cheque", "name": "Cheque", "online": False, "needs_reference": True,
     "reference_label": "Cheque number + bank"},
    {"id": "online", "name": "Online (Razorpay link via WhatsApp)", "online": True,
     "needs_reference": False, "reference_label": ""},
]

_VALID_METHOD_IDS = {m["id"] for m in PAYMENT_METHODS}


def get_payment_methods() -> list[dict]:
    """Return the accepted payment methods (for UI dropdowns / voice options)."""
    return PAYMENT_METHODS


def is_valid_payment_method(method_id: str) -> bool:
    return (method_id or "").strip().lower() in _VALID_METHOD_IDS


def record_manual_payment(
    booking_id: str,
    amount_inr: int,
    method: str,
    customer_name: str = "",
    customer_phone: str = "",
    reference: str = "",
    payment_type: str = "room_booking",
    collected_by: str = "",
) -> dict:
    """
    Record an OFFLINE payment (Cash / Card / UPI / Cheque) taken at the counter.
    Used for walk-in bookings and manual reconciliation.

    - For methods that need a reference (card/upi/cheque), 'reference' should be
      the txn id / cheque number.
    - Cheque payments start as 'pending' (until cleared); others are 'paid'.
    Returns the payment record.
    """
    method = (method or "").strip().lower()
    if method not in _VALID_METHOD_IDS:
        return {"success": False, "error": f"Invalid payment method '{method}'. "
                                            f"Valid: {sorted(_VALID_METHOD_IDS)}"}
    if method == "online":
        return {"success": False, "error": "Use create_room_payment_link for online payments"}

    meta = next(m for m in PAYMENT_METHODS if m["id"] == method)
    if meta["needs_reference"] and not reference:
        return {"success": False, "error": f"{meta['name']} requires a reference "
                                           f"({meta['reference_label']})"}

    ref_id = f"MAN-{uuid.uuid4().hex[:8].upper()}"
    # Cheques are provisional until cleared
    status = "pending" if method == "cheque" else "paid"

    record = {
        "payment_id": ref_id,
        "type": payment_type,            # room_booking | donation
        "method": method,
        "method_name": meta["name"],
        "reference": reference,
        "booking_id": booking_id,
        "amount": int(amount_inr),
        "currency": "INR",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "link": None,                    # offline — no link
        "status": status,
        "collected_by": collected_by,
        "is_manual": True,
        "created_at": datetime.now().isoformat(),
    }
    if status == "paid":
        record["paid_at"] = datetime.now().isoformat()

    _payment_links[ref_id] = record
    _sync_payment(record)
    logger.info(f"Manual payment recorded: {ref_id} {method} INR {amount_inr} ({status})")
    return {"success": True, **record}


def clear_cheque(payment_id: str) -> dict:
    """Mark a pending cheque payment as cleared/paid."""
    rec = _payment_links.get(payment_id)
    if not rec:
        return {"success": False, "error": "Payment not found"}
    if rec.get("method") != "cheque":
        return {"success": False, "error": "Not a cheque payment"}
    rec["status"] = "paid"
    rec["paid_at"] = datetime.now().isoformat()
    _sync_payment(rec)
    # Fire the automation loop (e.g. 80G cert if it was a donation)
    return handle_payment_confirmed(payment_id=payment_id)


def init_razorpay():
    """Initialize Razorpay client if keys are present."""
    global _client, _mock_mode

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        logger.info("Razorpay keys not set — running in MOCK mode (demo links)")
        _mock_mode = True
        return False

    try:
        import razorpay
        _client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        _mock_mode = False
        logger.info("Razorpay connected (LIVE mode)")
        return True
    except ImportError:
        logger.warning("razorpay package not installed — MOCK mode. Run: pip install razorpay")
        _mock_mode = True
        return False
    except Exception as e:
        logger.error(f"Razorpay init failed: {e} — MOCK mode")
        _mock_mode = True
        return False


def create_room_payment_link(
    booking_id: str,
    amount_inr: int,
    customer_name: str,
    customer_phone: str,
    description: str = "",
) -> dict:
    """
    Create a FIXED-amount payment link for a room booking.
    amount_inr: the room total in rupees.
    """
    desc = description or f"Room booking {booking_id} - Karivena Satram"
    ref_id = f"PAY-{booking_id}"

    if _mock_mode:
        link = _mock_link("room", ref_id, amount_inr)
    else:
        try:
            resp = _client.payment_link.create({
                "amount": amount_inr * 100,  # paise
                "currency": "INR",
                "accept_partial": False,
                "description": desc,
                "reference_id": ref_id,
                "customer": {"name": customer_name, "contact": customer_phone},
                "notify": {"sms": True, "whatsapp": True},
                "reminder_enable": True,
                "notes": {"type": "room_booking", "booking_id": booking_id},
            })
            link = resp.get("short_url", "")
        except Exception as e:
            logger.error(f"Razorpay room link failed: {e}")
            link = _mock_link("room", ref_id, amount_inr)

    record = {
        "payment_id": ref_id,
        "type": "room_booking",
        "booking_id": booking_id,
        "amount": amount_inr,
        "currency": "INR",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "link": link,
        "status": "created",
        "created_at": datetime.now().isoformat(),
    }
    _payment_links[ref_id] = record
    _sync_payment(record)
    return record


def create_donation_link(
    customer_name: str,
    customer_phone: str,
    amount_inr: int = 0,
    seva_id: str = "",
) -> dict:
    """
    Create a donation payment link.
    - If seva_id given: FIXED amount from the seva plan.
    - If amount_inr given (no seva): fixed custom amount.
    - If neither: FLEXIBLE (accept_partial / any amount) link.
    """
    seva = None
    if seva_id:
        seva = next((s for s in SEVA_OPTIONS if s["id"] == seva_id), None)
        if seva:
            amount_inr = seva["amount"]

    ref_id = f"DON-{uuid.uuid4().hex[:8].upper()}"
    flexible = (amount_inr == 0)
    desc = f"Donation - {seva['name']}" if seva else "Donation to Karivena Satram"

    if _mock_mode:
        link = _mock_link("donation", ref_id, amount_inr)
    else:
        try:
            payload = {
                "amount": (amount_inr if amount_inr > 0 else 100) * 100,
                "currency": "INR",
                "accept_partial": flexible,
                "description": desc,
                "reference_id": ref_id,
                "customer": {"name": customer_name, "contact": customer_phone},
                "notify": {"sms": True, "whatsapp": True},
                "notes": {"type": "donation", "seva": seva_id or "general"},
            }
            if flexible:
                payload["first_min_partial_amount"] = 10000  # min 100 rupees
            resp = _client.payment_link.create(payload)
            link = resp.get("short_url", "")
        except Exception as e:
            logger.error(f"Razorpay donation link failed: {e}")
            link = _mock_link("donation", ref_id, amount_inr)

    record = {
        "payment_id": ref_id,
        "type": "donation",
        "seva_id": seva_id or None,
        "seva_name": seva["name"] if seva else None,
        "amount": amount_inr,
        "flexible": flexible,
        "currency": "INR",
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "link": link,
        "status": "created",
        "is_80g": True,  # all donations are 80G tax-exempt eligible
        "certificate_80g_issued": False,
        "created_at": datetime.now().isoformat(),
    }
    _payment_links[ref_id] = record
    _sync_payment(record)
    return record


def create_room_plus_donation_link(
    booking_id: str,
    room_amount_inr: int,
    donation_amount_inr: int,
    customer_name: str,
    customer_phone: str,
) -> dict:
    """
    Payment TYPE 2: Fixed room amount + a customer-chosen donation amount.
    The room portion is a normal charge; the donation portion is 80G eligible.
    Returns TWO linked records (room + donation) so the 80G certificate can be
    issued for the donation portion only.
    """
    room_record = create_room_payment_link(
        booking_id=booking_id,
        amount_inr=room_amount_inr,
        customer_name=customer_name,
        customer_phone=customer_phone,
        description=f"Room booking {booking_id} - Karivena Satram",
    )

    donation_record = None
    if donation_amount_inr and donation_amount_inr > 0:
        donation_record = create_donation_link(
            customer_name=customer_name,
            customer_phone=customer_phone,
            amount_inr=donation_amount_inr,
        )
        # Link the donation to the booking + mark 80G eligible
        donation_record["linked_booking_id"] = booking_id
        donation_record["is_80g"] = True
        _payment_links[donation_record["payment_id"]] = donation_record
        _sync_payment(donation_record)

    return {
        "type": "room_plus_donation",
        "booking_id": booking_id,
        "room": room_record,
        "donation": donation_record,
        "room_amount": room_amount_inr,
        "donation_amount": donation_amount_inr if donation_record else 0,
        "total": room_amount_inr + (donation_amount_inr if donation_record else 0),
        "is_80g_on_donation": bool(donation_record),
    }


def create_seva_donation_link(
    customer_name: str,
    customer_phone: str,
    seva_id: str,
    custom_amount_inr: int = 0,
) -> dict:
    """
    Payment TYPE 3: Donation via a Seva plan.
    - Predefined amount from the seva, OR
    - Custom amount if the seva allows it (allow_custom) and custom_amount given.
    Always 80G eligible.
    """
    seva = next((s for s in SEVA_OPTIONS if s["id"] == seva_id), None)
    if not seva:
        return {"success": False, "error": f"Unknown seva '{seva_id}'"}

    amount = seva["amount"]
    is_custom = False
    if custom_amount_inr and custom_amount_inr > 0:
        if not seva.get("allow_custom", False):
            return {"success": False, "error": f"Seva '{seva_id}' does not allow custom amounts"}
        amount = int(custom_amount_inr)
        is_custom = True

    # General Donation (predefined amount 0) needs the donor to choose an amount;
    # if none given, the link is created as flexible (donor enters amount).
    record = create_donation_link(
        customer_name=customer_name,
        customer_phone=customer_phone,
        amount_inr=amount,
    )
    # Enrich with seva + 80G metadata
    record["seva_id"] = seva_id
    record["seva_name"] = seva["name"]
    record["category"] = seva.get("category", "general")
    record["is_custom_amount"] = is_custom
    record["is_80g"] = True
    _payment_links[record["payment_id"]] = record
    _sync_payment(record)

    return {"success": True, **record}


def get_seva_options() -> list[dict]:
    """Return available seva donation plans."""
    return SEVA_OPTIONS


def get_payment(payment_id: str) -> dict | None:
    return _payment_links.get(payment_id)


def get_all_payments() -> list[dict]:
    return sorted(_payment_links.values(), key=lambda p: p.get("created_at", ""), reverse=True)


def mark_paid(payment_id: str) -> bool:
    """Mark a payment as completed (called by webhook or manual)."""
    if payment_id in _payment_links:
        _payment_links[payment_id]["status"] = "paid"
        _payment_links[payment_id]["paid_at"] = datetime.now().isoformat()
        _sync_payment(_payment_links[payment_id])
        return True
    return False


def get_payment_stats() -> dict:
    total = len(_payment_links)
    paid = sum(1 for p in _payment_links.values() if p["status"] == "paid")
    room_revenue = sum(p["amount"] for p in _payment_links.values()
                       if p["type"] == "room_booking" and p["status"] == "paid")
    donation_total = sum(p["amount"] for p in _payment_links.values()
                         if p["type"] == "donation" and p["status"] == "paid")
    donation_80g_total = sum(p["amount"] for p in _payment_links.values()
                             if p["type"] == "donation" and p["status"] == "paid"
                             and p.get("is_80g"))
    certs_issued = sum(1 for p in _payment_links.values()
                       if p.get("is_80g") and p.get("certificate_80g_issued"))

    # Revenue broken down by payment method (paid only)
    by_method = {}
    for m in _VALID_METHOD_IDS:
        by_method[m] = sum(p["amount"] for p in _payment_links.values()
                           if p.get("status") == "paid"
                           and (p.get("method") or ("online" if p.get("link") else "cash")) == m)
    pending_cheques = sum(1 for p in _payment_links.values()
                          if p.get("method") == "cheque" and p.get("status") == "pending")

    return {
        "total_links": total,
        "paid": paid,
        "pending": total - paid,
        "room_revenue": room_revenue,
        "donation_total": donation_total,
        "donation_80g_total": donation_80g_total,
        "certificates_80g_issued": certs_issued,
        "revenue_by_method": by_method,
        "pending_cheques": pending_cheques,
        "mode": "mock" if _mock_mode else "live",
    }


def mark_80g_issued(payment_id: str) -> bool:
    """Flag that an 80G certificate has been generated for a donation."""
    if payment_id in _payment_links:
        _payment_links[payment_id]["certificate_80g_issued"] = True
        _sync_payment(_payment_links[payment_id])
        return True
    return False


def get_80g_donations() -> list[dict]:
    """All paid, 80G-eligible donations (for certificate generation)."""
    return [p for p in _payment_links.values()
            if p.get("is_80g") and p.get("status") == "paid"]


def find_payment_by_reference(reference_id: str) -> dict | None:
    """
    Look up a payment by its Razorpay reference_id (which equals our payment_id
    for room links, and the DON-/PAY- ref we set). Falls back to a scan.
    """
    if not reference_id:
        return None
    if reference_id in _payment_links:
        return _payment_links[reference_id]
    for p in _payment_links.values():
        if p.get("payment_id") == reference_id:
            return p
    return None


# === WEBHOOK + AUTOMATION ===

def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    """
    Verify a Razorpay webhook signature (HMAC-SHA256 of the raw body using the
    webhook secret). In MOCK mode (no secret configured) verification is skipped
    so local/demo testing still works.
    """
    if not RAZORPAY_WEBHOOK_SECRET:
        logger.info("[Webhook] No RAZORPAY_WEBHOOK_SECRET set — skipping signature check (mock)")
        return True
    if not signature:
        return False
    import hmac
    import hashlib
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def handle_payment_confirmed(reference_id: str = "", payment_id: str = "") -> dict:
    """
    THE AUTOMATION LOOP. Called when a payment is confirmed (via webhook or
    manual mark). Steps:
      1. Mark the payment paid.
      2. If it's an 80G donation, auto-generate the 80G certificate PDF and
         push it to the donor's WhatsApp.
      3. Return a summary of what fired.

    This closes the "make sure this is automated" requirement: a confirmed
    donation payment now issues its 80G certificate with no manual step.
    """
    ref = payment_id or reference_id
    record = find_payment_by_reference(ref)
    if not record:
        return {"success": False, "error": f"No payment found for '{ref}'"}

    pid = record["payment_id"]
    already_paid = record.get("status") == "paid"
    mark_paid(pid)

    result = {
        "success": True,
        "payment_id": pid,
        "type": record.get("type"),
        "was_already_paid": already_paid,
        "receipt": None,
        "certificate_80g": None,
        "whatsapp": None,
    }

    phone = record.get("customer_phone", "")
    cust = record.get("customer_name", "Guest")

    # 1. RECEIPT (invoice) — generated for room bookings (and any paid payment
    #    linked to a booking). Pushed to the customer's WhatsApp.
    if record.get("type") in ("room_booking", "room_plus_donation") or record.get("booking_id"):
        try:
            from app import invoice as invoice_mod
            booking = _lookup_booking(record.get("booking_id", ""))
            inv_input = booking or {
                "booking_id": record.get("booking_id", pid),
                "customer_name": cust,
                "customer_phone": phone,
                "customer_email": record.get("customer_email", ""),
                "room_amount": record.get("amount", 0),
                "payment_status": "Paid",
            }
            inv = invoice_mod.generate_invoice(inv_input)
            result["receipt"] = {"invoice_no": inv["invoice_no"], "file": inv["file_path"]}
            if phone:
                try:
                    from app import whatsapp
                    cap = whatsapp.compose_document_message(cust, "invoice", inv["invoice_no"])
                    whatsapp.send_whatsapp_document(phone, inv["file_path"], cap)
                except Exception as e:
                    logger.error(f"[Automation] receipt WhatsApp push failed: {e}")
        except Exception as e:
            logger.error(f"[Automation] receipt generation failed: {e}")
            result["receipt_error"] = str(e)

    # 2. Auto-issue 80G certificate for donations
    if record.get("is_80g") and not record.get("certificate_80g_issued"):
        try:
            from app import certificate_80g
            cert = certificate_80g.generate_80g_certificate(record)
            mark_80g_issued(pid)
            result["certificate_80g"] = {
                "certificate_no": cert["certificate_no"],
                "file": cert["file_path"],
            }
            # Push to WhatsApp
            if phone:
                try:
                    from app import whatsapp
                    caption = whatsapp.compose_document_message(cust, "80g", cert["certificate_no"])
                    wa = whatsapp.send_whatsapp_document(phone, cert["file_path"], caption)
                    result["whatsapp"] = wa.get("provider")
                except Exception as e:
                    logger.error(f"[Automation] 80G WhatsApp push failed: {e}")
        except Exception as e:
            logger.error(f"[Automation] 80G certificate generation failed: {e}")
            result["certificate_error"] = str(e)

    logger.info(f"[Automation] Payment confirmed {pid} — "
                f"receipt={bool(result['receipt'])} cert={bool(result['certificate_80g'])}")
    return result


def _lookup_booking(booking_id: str) -> dict | None:
    """Fetch the booking record (in-memory then Firestore) for receipt details."""
    if not booking_id:
        return None
    try:
        from app.knowledge_base import _bookings
        if booking_id in _bookings:
            b = _bookings[booking_id]
            return {
                "booking_id": booking_id,
                "customer_name": b.get("customer_name", ""),
                "customer_phone": b.get("customer_phone", ""),
                "customer_email": b.get("customer_email", ""),
                "gotram": b.get("gotram", ""),
                "location": b.get("location", ""),
                "room_type": b.get("room_type", ""),
                "check_in": b.get("check_in", ""),
                "check_out": b.get("check_out", ""),
                "no_of_rooms": b.get("num_rooms", 1),
                "room_amount": b.get("total_price", 0),
                "payment_status": "Paid",
            }
    except Exception:
        pass
    return None


def parse_webhook_event(payload: dict) -> dict:
    """
    Extract the reference_id + razorpay payment id from a Razorpay webhook
    payload. Handles both payment_link.paid and payment.captured events.
    """
    event = payload.get("event", "")
    reference_id = ""
    rp_payment_id = ""
    try:
        entities = payload.get("payload", {})
        # payment_link.paid
        pl = entities.get("payment_link", {}).get("entity", {})
        if pl:
            reference_id = pl.get("reference_id", "")
        # payment.captured
        pay = entities.get("payment", {}).get("entity", {})
        if pay:
            rp_payment_id = pay.get("id", "")
            notes = pay.get("notes", {}) or {}
            reference_id = reference_id or notes.get("booking_id", "") or notes.get("reference_id", "")
    except Exception:
        pass
    return {"event": event, "reference_id": reference_id, "razorpay_payment_id": rp_payment_id}


# === HELPERS ===

def _mock_link(kind: str, ref_id: str, amount: int) -> str:
    """
    Build a payment URL for demo / pre-live use.

    If a UPI VPA is configured (UPI_VPA), return a REAL UPI deep link
    (upi://pay?...) that opens the user's UPI app (GPay/PhonePe/Paytm) with the
    payee, amount, and reference pre-filled. Otherwise fall back to a mock
    Razorpay-style URL so the pipeline still completes.
    """
    if UPI_VPA:
        return build_upi_url(ref_id, amount, note=f"Karivena {kind}")
    return f"https://rzp.io/i/MOCK-{kind}-{ref_id[-6:]}"


def build_upi_url(ref_id: str, amount: int, note: str = "Karivena Satram") -> str:
    """
    Construct a UPI payment deep link (NPCI UPI URI spec).
    Opens any UPI app: pa=payee VPA, pn=payee name, am=amount, tn=note, tr=ref.
    Example: upi://pay?pa=karivena@sbi&pn=Karivena%20Satram&am=3000&cu=INR&tn=...
    """
    from urllib.parse import quote
    params = [
        f"pa={quote(UPI_VPA)}",
        f"pn={quote(UPI_PAYEE_NAME)}",
        f"tr={quote(ref_id)}",
        f"tn={quote(note)}",
        "cu=INR",
    ]
    if amount and amount > 0:
        params.append(f"am={amount}")
    return "upi://pay?" + "&".join(params)


def _sync_payment(record: dict):
    """Persist payment record to Firebase."""
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("payments").document(record["payment_id"]).set(record)
    except Exception:
        pass


# Initialize on import
init_razorpay()
load_sevas_from_firestore()
