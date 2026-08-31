"""
Checkout Flow — WhatsApp-driven, triggered at end of stay.

The checkout is ALWAYS handled over WhatsApp (per requirements):
  1. Compute / confirm the final amount due (room via rates, + any donation).
  2. Create a Razorpay checkout payment link.
  3. Auto-generate the invoice PDF.
  4. If a donation was made, auto-generate the 80G certificate PDF.
  5. Push checkout message + payment link + documents to the guest's WhatsApp.

Can be triggered:
  - Manually by a Supervisor (permission: trigger_checkout) via API.
  - Automatically by the end-of-stay scheduler (run_due_checkouts).
"""

import logging
from datetime import date, datetime

from app import payments, invoice as invoice_mod, certificate_80g, whatsapp

logger = logging.getLogger(__name__)


def process_checkout(booking: dict, donation_payment_id: str = "") -> dict:
    """
    Run the full checkout pipeline for one booking.

    booking: reservation dict (customer_name, customer_phone, location/temple_name,
             room_type, check_in, check_out, no_of_rooms, total_price/room_amount,
             booking_id/id, gotram, ...)
    donation_payment_id: optional — link an existing paid donation so its amount
             is reflected on the invoice and an 80G certificate is issued.
    """
    result = {"success": False, "steps": {}}

    bid = str(booking.get("booking_id") or booking.get("id") or f"BK-{datetime.now():%Y%m%d%H%M%S}")
    name = booking.get("customer_name", "Guest")
    phone = booking.get("customer_phone", "")
    room_amount = int(booking.get("room_amount") or booking.get("total_price") or 0)

    # 1. Resolve donation (if any) for invoice line + 80G
    donation = None
    donation_amount = 0
    if donation_payment_id:
        donation = payments.get_payment(donation_payment_id)
        if donation:
            donation_amount = int(donation.get("amount", 0) or 0)

    # 2. Create the checkout payment link (Razorpay)
    pay = payments.create_room_payment_link(
        booking_id=bid,
        amount_inr=room_amount,
        customer_name=name,
        customer_phone=phone,
        description=f"Checkout {bid} - Karivena Satram",
    )
    result["steps"]["payment_link"] = pay.get("link")

    # 3. Generate the invoice PDF (room + optional donation line)
    inv = invoice_mod.generate_invoice({
        **booking,
        "booking_id": bid,
        "room_amount": room_amount,
        "donation_amount": donation_amount,
        "payment_status": booking.get("payment_status", "Pending"),
    })
    result["steps"]["invoice"] = {"invoice_no": inv["invoice_no"], "file": inv["file_path"]}

    # 4. Generate 80G certificate if there was a donation
    cert = None
    if donation and donation_amount > 0:
        cert = certificate_80g.generate_80g_certificate(donation)
        payments.mark_80g_issued(donation_payment_id)
        result["steps"]["certificate_80g"] = {"cert_no": cert["certificate_no"], "file": cert["file_path"]}

    # 5. WhatsApp: checkout message + payment link, then documents
    checkout_msg = whatsapp.compose_checkout_message(
        {**booking, "booking_id": bid, "total_price": room_amount + donation_amount},
        payment_link=pay.get("link", ""),
        invoice_no=inv["invoice_no"],
    )
    wa_msg = whatsapp.send_whatsapp(phone, checkout_msg)
    result["steps"]["whatsapp_message"] = wa_msg.get("provider")

    # Invoice document
    inv_caption = whatsapp.compose_document_message(name, "invoice", inv["invoice_no"])
    whatsapp.send_whatsapp_document(phone, inv["file_path"], inv_caption)

    # 80G document
    if cert:
        cert_caption = whatsapp.compose_document_message(name, "80g", cert["certificate_no"])
        whatsapp.send_whatsapp_document(phone, cert["file_path"], cert_caption)

    # 6. Update reservation status in Firebase (best effort)
    _mark_checked_out(bid, inv["invoice_no"])

    result["success"] = True
    result["booking_id"] = bid
    result["invoice_no"] = inv["invoice_no"]
    result["payment_link"] = pay.get("link")
    result["total"] = room_amount + donation_amount
    logger.info(f"Checkout processed for {bid}")
    return result


def run_due_checkouts(on_date: date = None) -> dict:
    """
    Scheduler entry point: find bookings whose check_out is today (or past and
    not yet checked out) and run checkout for each.
    Returns a summary of processed bookings.
    """
    if not on_date:
        on_date = date.today()

    processed = []
    failed = []

    for booking in _fetch_due_bookings(on_date):
        try:
            r = process_checkout(booking)
            processed.append({"booking_id": r["booking_id"], "invoice_no": r["invoice_no"]})
        except Exception as e:
            logger.error(f"Checkout failed for {booking.get('id')}: {e}")
            failed.append({"booking_id": booking.get("id"), "error": str(e)})

    return {
        "date": on_date.isoformat(),
        "processed_count": len(processed),
        "failed_count": len(failed),
        "processed": processed,
        "failed": failed,
    }


def _fetch_due_bookings(on_date: date) -> list[dict]:
    """Fetch reservations due for checkout (check_out <= today, not checked out)."""
    bookings = []
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            for doc in _db.collection("reservations").stream():
                b = doc.to_dict()
                b["id"] = doc.id
                status = (b.get("reservation_status") or "").lower()
                if status in ("checked_out", "cancelled"):
                    continue
                co = b.get("check_out", "")
                try:
                    if date.fromisoformat(str(co)[:10]) <= on_date:
                        bookings.append(b)
                except Exception:
                    continue
    except Exception as e:
        logger.debug(f"Due-booking fetch skipped: {e}")
    return bookings


def _mark_checked_out(booking_id: str, invoice_no: str):
    """Update reservation status to checked_out with the invoice number."""
    try:
        from app.firebase_store import is_firebase_active, _db
        if is_firebase_active() and _db:
            _db.collection("reservations").document(booking_id).update({
                "reservation_status": "checked_out",
                "invoice_no": invoice_no,
                "checked_out_at": datetime.now().isoformat(),
            })
    except Exception:
        pass
