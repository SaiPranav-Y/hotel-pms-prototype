"""
80G Tax-Exemption Certificate PDF Generator — automated.

Generated automatically when a donation payment is confirmed (paid) and pushed
to WhatsApp. Covers ONLY the donation amount (room charges are never 80G).

Uses reportlab. PDFs written to app/generated/certificates/.

NOTE: The 80G registration number / trust PAN / approval details must be filled
into TRUST_80G below once the client provides them. Until then placeholders are
used and a "DRAFT" watermark note appears.
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

_OUT_DIR = Path(__file__).parent / "generated" / "certificates"
_OUT_DIR.mkdir(parents=True, exist_ok=True)

# Fill these when the client provides official 80G approval details.
TRUST_80G = {
    "name": "Karivena Satram",
    "address": "Karivena, Andhra Pradesh, India",
    "pan": "",                    # Trust PAN
    "reg_80g_number": "",         # 80G approval / registration number
    "reg_80g_date": "",           # date of approval
    "email": "info@karivenasatram.org",
    "phone": "+91-XXXXXXXXXX",
}

BRAND = colors.HexColor("#8B4513")
GOLD = colors.HexColor("#B8860B")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("CertOrg", parent=ss["Title"], fontSize=22, textColor=BRAND, alignment=1, spaceAfter=2))
    ss.add(ParagraphStyle("CertSub", parent=ss["Normal"], fontSize=9, textColor=colors.grey, alignment=1))
    ss.add(ParagraphStyle("CertTitle", parent=ss["Heading1"], fontSize=16, textColor=GOLD, alignment=1, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("Body", parent=ss["Normal"], fontSize=10.5, leading=16))
    ss.add(ParagraphStyle("Small", parent=ss["Normal"], fontSize=9))
    ss.add(ParagraphStyle("SmallRight", parent=ss["Normal"], fontSize=9, alignment=2))
    ss.add(ParagraphStyle("Foot", parent=ss["Normal"], fontSize=8, textColor=colors.grey, alignment=1))
    ss.add(ParagraphStyle("Draft", parent=ss["Normal"], fontSize=8, textColor=colors.red, alignment=1))
    return ss


def generate_80g_certificate(donation: dict) -> dict:
    """
    Generate an 80G certificate PDF for a paid donation.

    Expected donation fields:
      payment_id, customer_name, customer_phone, amount, seva_name (optional),
      pan (optional donor PAN), created_at/paid_at
    """
    ss = _styles()

    pay_id = str(donation.get("payment_id") or f"DON-{datetime.now():%Y%m%d%H%M%S}")
    cert_no = f"80G/{datetime.now():%Y%m}/{pay_id[-6:]}"
    filename = f"80g_{pay_id}.pdf"
    path = _OUT_DIR / filename

    donor = donation.get("customer_name", "Donor")
    phone = donation.get("customer_phone", "")
    amount = int(donation.get("amount", 0) or 0)
    seva = donation.get("seva_name") or "General Donation"
    donor_pan = donation.get("pan", "")
    paid_on = donation.get("paid_at") or donation.get("created_at") or datetime.now().isoformat()
    try:
        paid_on = datetime.fromisoformat(paid_on).strftime("%d %b %Y")
    except Exception:
        paid_on = f"{datetime.now():%d %b %Y}"

    is_draft = not (TRUST_80G["reg_80g_number"] and TRUST_80G["pan"])

    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )
    e = []

    e.append(Paragraph(TRUST_80G["name"], ss["CertOrg"]))
    e.append(Paragraph(TRUST_80G["address"], ss["CertSub"]))
    e.append(Paragraph(f"{TRUST_80G['email']} &nbsp;|&nbsp; {TRUST_80G['phone']}", ss["CertSub"]))
    e.append(Spacer(1, 6))
    e.append(HRFlowable(width="100%", thickness=1.5, color=GOLD))
    e.append(Paragraph("DONATION RECEIPT &amp; 80G CERTIFICATE", ss["CertTitle"]))
    e.append(Paragraph("Under Section 80G of the Income Tax Act, 1961", ss["CertSub"]))
    e.append(Spacer(1, 10))

    if is_draft:
        e.append(Paragraph("[ DRAFT — official 80G registration details pending ]", ss["Draft"]))
        e.append(Spacer(1, 6))

    meta = [
        [Paragraph("<b>Certificate No:</b>", ss["Small"]), Paragraph(cert_no, ss["Small"]),
         Paragraph("<b>Date:</b>", ss["Small"]), Paragraph(f"{datetime.now():%d %b %Y}", ss["Small"])],
        [Paragraph("<b>Receipt Ref:</b>", ss["Small"]), Paragraph(pay_id, ss["Small"]),
         Paragraph("<b>Received On:</b>", ss["Small"]), Paragraph(paid_on, ss["Small"])],
    ]
    mt = Table(meta, colWidths=[30 * mm, 50 * mm, 30 * mm, 40 * mm])
    mt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    e.append(mt)
    e.append(Spacer(1, 10))

    body = (
        f"This is to gratefully acknowledge the receipt of a voluntary donation of "
        f"<b>Rs. {amount:,}/-</b> ({_rupees_in_words(amount)}) from <b>{donor}</b>"
        + (f" (PAN: {donor_pan})" if donor_pan else "")
        + f", towards <b>{seva}</b>."
    )
    e.append(Paragraph(body, ss["Body"]))
    e.append(Spacer(1, 10))

    detail_rows = [
        [Paragraph("<b>Donor Name</b>", ss["Small"]), Paragraph(donor, ss["Small"])],
        [Paragraph("<b>Contact</b>", ss["Small"]), Paragraph(phone, ss["Small"])],
        [Paragraph("<b>Purpose</b>", ss["Small"]), Paragraph(seva, ss["Small"])],
        [Paragraph("<b>Amount (INR)</b>", ss["Small"]), Paragraph(f"Rs. {amount:,}/-", ss["Small"])],
        [Paragraph("<b>Trust PAN</b>", ss["Small"]), Paragraph(TRUST_80G["pan"] or "—", ss["Small"])],
        [Paragraph("<b>80G Reg. No.</b>", ss["Small"]), Paragraph(TRUST_80G["reg_80g_number"] or "—", ss["Small"])],
    ]
    dt = Table(detail_rows, colWidths=[45 * mm, 109 * mm])
    dt.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FFF9EC")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    e.append(dt)
    e.append(Spacer(1, 14))

    e.append(Paragraph(
        "Donations to this institution are eligible for deduction under Section 80G "
        "of the Income Tax Act, 1961, subject to the limits and conditions specified therein.",
        ss["Small"],
    ))
    e.append(Spacer(1, 26))

    sign = [[Paragraph("", ss["Small"]),
             Paragraph("_______________________<br/>Authorised Signatory<br/>" + TRUST_80G["name"], ss["SmallRight"])]]
    st = Table(sign, colWidths=[94 * mm, 60 * mm])
    st.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    e.append(st)
    e.append(Spacer(1, 16))
    e.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    e.append(Paragraph("This is a computer-generated receipt. Please retain it for your tax records.", ss["Foot"]))

    doc.build(e)
    logger.info(f"80G certificate generated: {path}")

    return {
        "success": True,
        "certificate_no": cert_no,
        "payment_id": pay_id,
        "file_path": str(path),
        "file_name": filename,
        "amount": amount,
        "is_draft": is_draft,
    }


def _rupees_in_words(amount: int) -> str:
    """Reuse invoice word converter."""
    try:
        from app.invoice import _rupees_in_words as conv
        return conv(amount)
    except Exception:
        return f"{amount} Rupees Only"
