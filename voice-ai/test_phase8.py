"""
Phase 8 Test Suite — Real Karivena data integration.
  - Gotram filter robustness (Telugu, aliases, fuzzy, rejection)
  - Real room rates from Excel
  - 4 payment methods (cash/card/upi/cheque) + online
  - Donation categories + real amounts (all 80G)
Run:  py test_phase8.py
"""

import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = 0


def ok(n):
    global PASSED
    PASSED += 1
    print(f"  [PASS] {n}")


def fail(n, e):
    global FAILED
    FAILED += 1
    print(f"  [FAIL] {n}: {e}")


# === GOTRAM FILTER ===
print("=== GOTRAM FILTER (robust) ===")
try:
    from app import gotram

    assert gotram.get_gotram_count() >= 30
    ok(f"Loaded {gotram.get_gotram_count()} gotrams")

    # English canonical + alias + suffix
    assert gotram.match_gotram("Bharadwaja") == "Bharadwaja"
    assert gotram.match_gotram("bharadwaj") == "Bharadwaja"
    assert gotram.match_gotram("Bharadwaja gotram") == "Bharadwaja"
    ok("English + alias + suffix match")

    # Telugu Unicode input
    assert gotram.match_gotram("భారద్వాజ") == "Bharadwaja"
    assert gotram.match_gotram("కాశ్యప") == "Kashyapa"
    ok("Telugu Unicode match")

    # Fuzzy (minor misspelling)
    assert gotram.match_gotram("Kashyapaa") == "Kashyapa"
    ok("Fuzzy misspelling match")

    # Rejections
    assert gotram.match_gotram("") is None
    assert gotram.match_gotram("Smith") is None
    assert gotram.match_gotram("ka") is None  # too short — must not match Kashyapa
    ok("Invalid / too-short inputs rejected")

    assert gotram.is_allowed("Koundinya") is True
    assert gotram.is_allowed("NotReal") is False
    ok("is_allowed works")
except Exception as e:
    fail("Gotram filter", e)

# === RATES (real Excel data) ===
print("\n=== RATES (real data) ===")
try:
    from app import rates
    from datetime import date

    all_rates = rates.get_all_rates()
    assert len(all_rates) >= 8, f"expected >=8 locations, got {len(all_rates)}"
    ok(f"{len(all_rates)} locations loaded")

    # Spot-check known base rates from the Excel
    assert rates.get_rate("Srisailam", "AC") == 1500, rates.get_rate("Srisailam", "AC")
    assert rates.get_rate("Srisailam", "Non-AC") == 500
    assert rates.get_rate("Kasi", "AC") == 1800
    assert rates.get_rate("Tirupathi", "AC") == 1500
    assert rates.get_rate("Mahanandi", "Non-AC") == 600
    ok("Base rates match Excel (Srisailam/Kasi/Tirupathi/Mahanandi)")

    q = rates.compute_total("Srisailam", "AC", date(2026, 7, 1), date(2026, 7, 3), 2)
    assert q["total"] == 6000, q
    ok("compute_total: Srisailam AC 2N x 2 rooms = 6000")
except Exception as e:
    fail("Rates", e)

# === PAYMENT METHODS ===
print("\n=== PAYMENT METHODS ===")
try:
    from app import payments as p

    ids = [m["id"] for m in p.get_payment_methods()]
    for m in ("cash", "card", "upi", "cheque", "online"):
        assert m in ids, f"missing method {m}"
    ok("cash / card / upi / cheque / online present")

    r = p.record_manual_payment("BK8-CASH", 1500, "cash")
    assert r["success"] and r["status"] == "paid"
    ok("Cash recorded (paid, no reference)")

    r = p.record_manual_payment("BK8-UPI", 1500, "upi")
    assert not r["success"]
    r = p.record_manual_payment("BK8-UPI", 1500, "upi", reference="UTR999")
    assert r["success"] and r["status"] == "paid"
    ok("UPI needs reference; with reference -> paid")

    r = p.record_manual_payment("BK8-CHQ", 5000, "cheque", reference="CHQ-9 SBI")
    assert r["success"] and r["status"] == "pending"
    cid = r["payment_id"]
    cl = p.clear_cheque(cid)
    assert cl["success"] and p.get_payment(cid)["status"] == "paid"
    ok("Cheque pending -> cleared -> paid")

    assert not p.record_manual_payment("X", 1, "bitcoin")["success"]
    ok("Invalid method rejected")

    stats = p.get_payment_stats()
    assert "revenue_by_method" in stats and "pending_cheques" in stats
    ok("Stats include revenue_by_method + pending_cheques")
except Exception as e:
    fail("Payment methods", e)

# === DONATIONS (real categories + amounts) ===
print("\n=== DONATIONS (real) ===")
try:
    from app import payments as p

    cats = [c["id"] for c in p.get_donation_categories()]
    assert cats == ["general", "corpus_fund_donation", "corpus_fund_receipt"], cats
    ok("3 donation categories")

    expect = {
        "general": 0, "room_construction": 500000, "bhudanam": 100000,
        "one_day_annadanam": 2000, "five_day_annadanam": 15000,
        "nityannadanam": 30000, "marriage_day": 3000, "birthday": 2000,
        "special_occasion": 6000, "maharaja_poshakulu": 100000,
        "budhana_poshakulu": 10000, "vedanidhi": 5000, "gonidhi": 5000,
    }
    by_id = {s["id"]: s for s in p.get_seva_options()}
    for sid, amt in expect.items():
        assert sid in by_id, f"missing {sid}"
        assert by_id[sid]["amount"] == amt, f"{sid}={by_id[sid]['amount']} != {amt}"
    ok(f"All {len(expect)} donation options with exact amounts")

    grouped = p.get_sevas_by_category()
    assert len(grouped["corpus_fund_receipt"]["options"]) == 10
    assert len(grouped["corpus_fund_donation"]["options"]) == 2
    assert len(grouped["general"]["options"]) == 1
    ok("Grouped: general=1, corpus_donation=2, corpus_receipt=10")

    # All donations 80G
    for s in p.get_seva_options():
        r = p.create_seva_donation_link("T", "+919999999999", s["id"],
                                        custom_amount_inr=(100 if s["amount"] == 0 else 0))
        assert r.get("is_80g") is True, f"{s['id']} not 80G"
    ok("Every donation option is 80G eligible")

    # Category tagged on the record
    r = p.create_seva_donation_link("D", "+919000000099", "room_construction")
    assert r["category"] == "corpus_fund_donation"
    ok("Donation record tagged with category")
except Exception as e:
    fail("Donations", e)

# === ORG / TRUST NAME ===
print("\n=== ORG / TRUST DETAILS ===")
try:
    from app import invoice, certificate_80g as c
    assert "Karivena Nityannadana Satram" in invoice.ORG["name"]
    assert "Karivena Nityannadana Satram" in c.TRUST_80G["name"]
    ok("Official trust name set in invoice + 80G certificate")
    # 80G still DRAFT until reg no + PAN provided
    cert = c.generate_80g_certificate({"payment_id": "DON-P8", "customer_name": "X",
                                       "customer_phone": "+91", "amount": 5000,
                                       "seva_name": "Vedanidhi"})
    assert cert["is_draft"] is True
    ok("80G certificate remains DRAFT until reg no + PAN provided")
    import glob
    for f in glob.glob("app/generated/**/*.pdf", recursive=True):
        os.remove(f)
except Exception as e:
    fail("Org/Trust", e)

# === API ROUTES ===
print("\n=== NEW API ROUTES ===")
try:
    from app.main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    for pth in ("/api/payments/methods", "/api/payments/manual",
                "/api/donations/categories", "/api/donations/grouped"):
        assert pth in paths, f"missing {pth}"
    ok("New payment + donation routes registered")
except Exception as e:
    fail("API routes", e)

print(f"\n{'='*55}")
print(f"  RESULTS: {PASSED} PASSED | {FAILED} FAILED")
print(f"{'='*55}")
sys.exit(1 if FAILED == 0 else 2)
