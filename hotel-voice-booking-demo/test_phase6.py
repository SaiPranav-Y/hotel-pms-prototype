"""
Phase 6 Test Suite — Roles, Rates, Payment Types 2+3, Invoice, 80G, Checkout.
Run:  py test_phase6.py
"""

import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PASSED = 0
FAILED = 0


def ok(name):
    global PASSED
    PASSED += 1
    print(f"  [PASS] {name}")


def fail(name, err):
    global FAILED
    FAILED += 1
    print(f"  [FAIL] {name}: {err}")


# === ROLES ===
print("=== ROLES ===")
try:
    from app.roles import (
        has_permission, get_all_roles, create_user, get_user,
        assign_role, check_access, ROLES, PERMISSIONS,
    )
    assert len(ROLES) == 3, "Expected 3 roles"
    ok("3 roles defined")

    assert has_permission("supervisor", "walk_in_booking")
    assert not has_permission("supervisor", "edit_rates")
    assert has_permission("admin", "edit_rates")
    assert has_permission("super_admin", "manage_users")
    ok("Permission matrix correct")

    r = create_user("test_sup@ks.org", "Test Sup", "supervisor")
    assert r["success"]
    ok("Create supervisor user")

    allowed, reason = check_access("test_sup@ks.org", "walk_in_booking")
    assert allowed, f"Should allow walk_in_booking: {reason}"
    ok("Supervisor walk_in_booking allowed")

    denied, reason = check_access("test_sup@ks.org", "edit_rates")
    assert not denied, f"Should deny edit_rates: {reason}"
    ok("Supervisor edit_rates denied")

    r2 = assign_role("test_sup@ks.org", "admin")
    assert r2["success"]
    allowed2, _ = check_access("test_sup@ks.org", "edit_rates")
    assert allowed2
    ok("Promote to admin — edit_rates now allowed")

    roles_info = get_all_roles()
    assert len(roles_info) == 3
    assert roles_info[0]["permission_count"] == 7   # supervisor
    assert roles_info[1]["permission_count"] == 13  # admin
    assert roles_info[2]["permission_count"] == 17  # super_admin
    ok("Role info with permission counts")

except Exception as e:
    fail("Roles", e)

# === RATES ===
print("\n=== RATES ===")
try:
    from app.rates import get_rate, set_rate, add_season_rate, compute_total, get_all_rates
    from datetime import date

    set_rate("Test_Location", "AC", 1200)
    r = get_rate("test_location", "AC")
    assert r == 1200, f"Expected 1200, got {r}"
    ok("Set + get base rate")

    add_season_rate("test_location", "AC", "Festival", "2026-12-01", "2026-12-31", 1800)
    r2 = get_rate("test_location", "AC", date(2026, 12, 15))
    assert r2 == 1800, f"Expected season rate 1800, got {r2}"
    ok("Season rate override")

    r3 = get_rate("test_location", "AC", date(2026, 11, 15))
    assert r3 == 1200, f"Expected base 1200 outside season, got {r3}"
    ok("Base rate outside season")

    total = compute_total("test_location", "AC", date(2026, 11, 10), date(2026, 11, 12), 2)
    assert total["nights"] == 2
    assert total["total"] == 1200 * 2 * 2, f"Expected {1200*4}, got {total['total']}"
    ok("Compute total (2 nights, 2 rooms)")

except Exception as e:
    fail("Rates", e)

# === PAYMENT TYPES ===
print("\n=== PAYMENT TYPES ===")
try:
    from app.payments import (
        create_room_plus_donation_link, create_seva_donation_link,
        get_payment_stats, mark_paid, mark_80g_issued, get_80g_donations,
    )

    # Type 2: fixed room + donation
    combo = create_room_plus_donation_link("BK-T2", 2400, 1000, "Tester", "+919999999999")
    assert combo["type"] == "room_plus_donation"
    assert combo["room_amount"] == 2400
    assert combo["donation_amount"] == 1000
    assert combo["total"] == 3400
    assert combo["is_80g_on_donation"] is True
    assert combo["donation"]["is_80g"] is True
    ok("Type 2: room + donation (80G on donation)")

    # Type 3: seva donation (real Karivena option)
    seva = create_seva_donation_link("Tester", "+919999999999", "nityannadanam")
    assert seva["success"]
    assert seva["amount"] == 30000
    assert seva["is_80g"] is True
    ok("Type 3: seva donation (predefined, 80G)")

    # Custom seva amount
    seva_c = create_seva_donation_link("Tester", "+919999999999", "one_day_annadanam", custom_amount_inr=500)
    assert seva_c["success"]
    assert seva_c["amount"] == 500
    assert seva_c["is_custom_amount"] is True
    ok("Type 3: seva custom amount")

    # Invalid seva
    bad = create_seva_donation_link("T", "+919", "nonexistent_seva")
    assert bad.get("success") is False
    ok("Type 3: unknown seva rejected")

    # 80G stats
    mark_paid(seva["payment_id"])
    stats = get_payment_stats()
    assert stats["donation_80g_total"] > 0
    ok("Payment stats include 80G totals")

    mark_80g_issued(seva["payment_id"])
    stats2 = get_payment_stats()
    assert stats2["certificates_80g_issued"] >= 1
    ok("mark_80g_issued tracked")

except Exception as e:
    fail("Payment types", e)

# === INVOICE PDF ===
print("\n=== INVOICE ===")
try:
    from app.invoice import generate_invoice
    inv = generate_invoice({
        "booking_id": "BK-INV-TEST",
        "customer_name": "Invoice Tester",
        "customer_phone": "+919000000000",
        "gotram": "Bharadwaja",
        "location": "Srisailam",
        "room_type": "AC",
        "check_in": "2026-08-01",
        "check_out": "2026-08-03",
        "no_of_rooms": 1,
        "room_amount": 2400,
        "donation_amount": 500,
        "payment_status": "Paid",
    })
    assert inv["success"]
    assert inv["total"] == 2900
    assert os.path.isfile(inv["file_path"]), f"PDF not found: {inv['file_path']}"
    ok("Invoice PDF generated")
    os.remove(inv["file_path"])  # cleanup
except Exception as e:
    fail("Invoice", e)

# === 80G CERTIFICATE PDF ===
print("\n=== 80G CERTIFICATE ===")
try:
    from app.certificate_80g import generate_80g_certificate
    cert = generate_80g_certificate({
        "payment_id": "DON-CERT-TEST",
        "customer_name": "Cert Tester",
        "customer_phone": "+919000000000",
        "amount": 1116,
        "seva_name": "Annadanam",
    })
    assert cert["success"]
    assert cert["amount"] == 1116
    assert cert["is_draft"] is True  # no real 80G reg yet
    assert os.path.isfile(cert["file_path"]), f"PDF not found: {cert['file_path']}"
    ok("80G certificate PDF generated (draft)")
    os.remove(cert["file_path"])
except Exception as e:
    fail("80G Certificate", e)

# === CHECKOUT FLOW ===
print("\n=== CHECKOUT ===")
try:
    from app.checkout import process_checkout
    from app.payments import create_donation_link, mark_paid as mp

    # Create a paid donation for checkout
    don = create_donation_link("Checkout Tester", "+919000000001", amount_inr=500)
    mp(don["payment_id"])

    result = process_checkout(
        booking={
            "booking_id": "BK-CO-TEST",
            "customer_name": "Checkout Tester",
            "customer_phone": "+919000000001",
            "gotram": "Bharadwaja",
            "location": "Srisailam",
            "room_type": "AC",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "no_of_rooms": 1,
            "room_amount": 2400,
        },
        donation_payment_id=don["payment_id"],
    )
    assert result["success"]
    assert "payment_link" in result["steps"]
    assert "invoice" in result["steps"]
    assert "certificate_80g" in result["steps"]
    assert "whatsapp_message" in result["steps"]
    ok("Full checkout pipeline (payment + invoice + 80G + WhatsApp)")

    # Cleanup PDFs
    import glob
    for f in glob.glob("app/generated/**/*.pdf", recursive=True):
        os.remove(f)
except Exception as e:
    fail("Checkout", e)

# === WHATSAPP CHECKOUT MESSAGES ===
print("\n=== WHATSAPP CHECKOUT ===")
try:
    from app.whatsapp import compose_checkout_message, compose_document_message
    msg = compose_checkout_message(
        {"customer_name": "Test", "location": "Srisailam", "booking_id": "BK1", "total_price": 2400, "check_out": "2026-08-03"},
        "https://rzp.io/test",
        "KS/202608/BK1",
    )
    assert "Checkout Summary" in msg
    assert "rzp.io" in msg
    ok("Checkout WhatsApp message composed")

    inv_msg = compose_document_message("Test", "invoice", "KS/202608/BK1")
    assert "Tax Invoice" in inv_msg
    ok("Invoice caption composed")

    cert_msg = compose_document_message("Test", "80g", "80G/202608/TEST")
    assert "80G Donation Certificate" in cert_msg
    ok("80G caption composed")
except Exception as e:
    fail("WhatsApp checkout", e)

# === API ROUTES REGISTERED ===
print("\n=== API ROUTES ===")
try:
    from app.main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    for p in ["/api/roles", "/api/users", "/api/rates", "/api/rates/quote",
              "/api/rates/season", "/api/sevas", "/api/payments/room-donation",
              "/api/payments/seva", "/api/invoice", "/api/checkout",
              "/api/certificates/80g", "/api/checkout/run-due", "/health"]:
        assert p in paths, f"Missing route: {p}"
    ok(f"All new API routes present ({len(paths)} total)")
except Exception as e:
    fail("API routes", e)

# === SUMMARY ===
print(f"\n{'='*55}")
print(f"  RESULTS: {PASSED} PASSED | {FAILED} FAILED")
print(f"{'='*55}")
if FAILED > 0:
    print("  *** FAILURES DETECTED ***")
sys.exit(1 if FAILED == 0 else 2)
