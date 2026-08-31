"""
Invoice PDF Generator — automated tax invoice for a completed stay.

Generated automatically at checkout (end of stay) and pushed to WhatsApp.
Uses reportlab. PDFs are written to app/generated/invoices/.

An invoice covers the ROOM charge (and any linked room+donation split shows
the donation as a separate 80G line note, but the 80G certificate itself is a
separate document — see certificate_80g.py).
"""

import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable,
)

logger = logging.getLogger(__name__)

_OUT_DIR = Path(__file__).parent / "generated" / "invoices"
_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Organisation details (update with real trust details when provided)
ORG = {
    "name": "Karivena Satram",
    "subtitle": "Pilgrim Accommodation & Devotional Services",
    "address": "Karivena, Andhra Pradesh, India",
    "email": "info@karivenasatram.org",
    "phone": "+91-XXXXXXXXXX",
    "gstin": "",   # fill when available
    "pan": "",     # fill when available
}

BRAND = colors.HexColor("#8B4513")   # saffron-brown
ACCENT = colors.HexColor("#D2691E")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("OrgName", parent=ss["Title"], fontSize=20, textColor=BRAND, spaceAfter=2))
    ss.add(ParagraphStyle("OrgSub", parent=ss["Normal"], fontSize=9, textColor=colors.grey))
    ss.add(ParagraphStyle("DocTitle", parent=ss["Heading1"], fontSize=15, textColor=ACCENT, spaceBefore=6))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=9))
    ss.add(ParagraphStyle("SmallRight", parent=ss["Normal"], fontSize=9, alignment=2))
    ss.add(ParagraphStyle("Foot", parent=ss["Normal"], fontSize=8, textColor=colors.grey, alignment=1))
    return ss


def generate_invoice(booking: dict) -> dict:
    """
    Generate an invoice PDF for a booking/stay.

    Expected booking fields (missing ones are handled gracefully):
      booking_id / id, customer_name, customer_phone, gotram, temple_name/location,
      room_type, check_in, check_out, no_of_rooms, total_price/room_amount,
      donation_amount (optional), payment_status
    """
    ss = _styles()

    bid = str(booking.get("booking_id") or booking.get("id") or f"INV-{datetime.now():%Y%m%d%H%M%S}")
    invoice_no = f"KS/{datetime.now():%Y%m}/{bid[-6:]}"
    filename = f"invoice_{bid}.pdf"
    path = _OUT_DIR / filename

    customer = booking.get("customer_name", "Guest")
    phone = booking.get("customer_phone", "")
    gotram = booking.get("gotram", "")
    location = booking.get("temple_name") or booking.get("location", "")
    room_type = booking.get("room_type", "")
    check_in = str(booking.get("check_in", ""))
    check_out = str(booking.get("check_out", ""))
    num_rooms = int(booking.get("no_of_rooms", 1) or 1)
    room_amount = int(booking.get("room_amount") or booking.get("total_price") or 0)
    donation_amount = int(booking.get("donation_amount", 0) or 0)

    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    )
    e = []

    # Header
    e.append(Paragraph(ORG["name"], ss["OrgName"]))
    e.append(Paragraph(ORG["subtitle"], ss["OrgSub"]))
    e.append(Paragraph(ORG["address"], ss["OrgSub"]))
    e.append(Paragraph(f"{ORG['email']} &nbsp;|&nbsp; {ORG['phone']}", ss["OrgSub"]))
    e.append(Spacer(1, 6))
    e.append(HRFlowable(width="100%", thickness=1.2, color=BRAND))
    e.append(Paragraph("TAX INVOICE", ss["DocTitle"]))
    e.append(Spacer(1, 4))

    # Invoice meta + customer (two-column)
    meta = [
        [Paragraph("<b>Invoice No:</b>", ss["Small"]), Paragraph(invoice_no, ss["Small"]),
         Paragraph("<b>Booking ID:</b>", ss["Small"]), Paragraph(bid, ss["Small"])],
        [Paragraph("<b>Date:</b>", ss["Small"]), Paragraph(f"{datetime.now():%d %b %Y}", ss["Small"]),
         Paragraph("<b>Payment:</b>", ss["Small"]), Paragraph(str(booking.get("payment_status", "Pending")), ss["Small"])],
    ]
    mt = Table(meta, colWidths=[28 * mm, 55 * mm, 28 * mm, 43 * mm])
    mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    e.append(mt)
    e.append(Spacer(1, 6))

    bill_to = [
        [Paragraph("<b>Billed To</b>", ss["Small"])],
        [Paragraph(customer, ss["Small"])],
        [Paragraph(f"Phone: {phone}", ss["Small"])],
    ]
    if gotram:
        bill_to.append([Paragraph(f"Gotram: {gotram}", ss["Small"])])
    bt = Table(bill_to, colWidths=[154 * mm])
    bt.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF6EC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    e.append(bt)
    e.append(Spacer(1, 10))

    # Line items
    nights = _nights(check_in, check_out)
    stay_desc = f"{location} — {room_type}<br/><font size=8 color=grey>Stay: {check_in} to {check_out} ({nights} night(s)), {num_rooms} room(s)</font>"

    rows = [
        [Paragraph("<b>Description</b>", ss["Small"]), Paragraph("<b>Amount (INR)</b>", ss["SmallRight"])],
        [Paragraph(stay_desc, ss["Small"]), Paragraph(f"{room_amount:,}", ss["SmallRight"])],
    ]
    if donation_amount > 0:
        rows.append([
            Paragraph("Voluntary Donation <font size=7 color=grey>(80G certificate issued separately)</font>", ss["Small"]),
            Paragraph(f"{donation_amount:,}", ss["SmallRight"]),
        ])
    grand_total = room_amount + donation_amount
    rows.append([Paragraph("<b>Total</b>", ss["Small"]), Paragraph(f"<b>{grand_total:,}</b>", ss["SmallRight"])])

    it = Table(rows, colWidths=[124 * mm, 30 * mm])
    it.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFF6EC")),
    ]))
    e.append(it)
    e.append(Spacer(1, 14))

    e.append(Paragraph(f"Amount in words: <b>{_rupees_in_words(grand_total)}</b>", ss["Small"]))
    e.append(Spacer(1, 20))
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    e.append(Spacer(1, 6))
    e.append(Paragraph("This is a computer-generated invoice and does not require a signature.", ss["Foot"]))
    e.append(Paragraph("Om Namah Shivaya — Thank you for your visit.", ss["Foot"]))

    doc.build(e)
    logger.info(f"Invoice generated: {path}")

    return {
        "success": True,
        "invoice_no": invoice_no,
        "booking_id": bid,
        "file_path": str(path),
        "file_name": filename,
        "total": grand_total,
        "room_amount": room_amount,
        "donation_amount": donation_amount,
    }


def _nights(check_in: str, check_out: str) -> int:
    try:
        from datetime import date
        ci = date.fromisoformat(check_in[:10])
        co = date.fromisoformat(check_out[:10])
        return max((co - ci).days, 1)
    except Exception:
        return 1


def _rupees_in_words(amount: int) -> str:
    """Convert an integer rupee amount to Indian-format words."""
    if amount == 0:
        return "Zero Rupees Only"
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + ((" " + ones[n % 10]) if n % 10 else "")

    def three(n):
        h = n // 100
        r = n % 100
        s = ""
        if h:
            s += ones[h] + " Hundred"
            if r:
                s += " "
        if r:
            s += two(r)
        return s

    parts = []
    crore = amount // 10000000
    amount %= 10000000
    lakh = amount // 100000
    amount %= 100000
    thousand = amount // 1000
    amount %= 1000
    hundred = amount

    if crore:
        parts.append(two(crore) + " Crore")
    if lakh:
        parts.append(two(lakh) + " Lakh")
    if thousand:
        parts.append(two(thousand) + " Thousand")
    if hundred:
        parts.append(three(hundred))
    return " ".join(parts).strip() + " Rupees Only"
