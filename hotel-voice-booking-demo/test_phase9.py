"""
Phase 9 Test Suite — Staff accounts, mandatory email, WhatsApp flow,
receipt+80G on payment, UPI URL, donations.
Run:  py test_phase9.py
"""

import os
import sys
import glob

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


def _clean():
    for f in glob.glob("app/generated/**/*.pdf", recursive=True):
        try:
            os.remove(f)
        except Exception:
            pass


# === STAFF ACCOUNTS / AUTH ===
print("=== STAFF ACCOUNTS & AUTH ===")
try:
    from app import roles

    # password hashing round-trip
    h = roles.hash_password("Secret123@")
    assert h.startswith("pbkdf2$")
    assert roles.verify_password("Secret123@", h)
    assert not roles.verify_password("wrong", h)
    ok("Password hash + verify (pbkdf2)")

    # create user with password, authenticate
    roles.create_user("t_admin@ks.org", "Test Admin", "admin", password="AdminPass1@")
    a = roles.authenticate("t_admin@ks.org", "AdminPass1@")
    assert a["success"] and a["role"] == "admin"
    ok("Create user with password + authenticate")

    bad = roles.authenticate("t_admin@ks.org", "nope")
    assert not bad["success"]
    ok("Wrong password rejected")

    # get_all_users must NOT leak password_hash
    users = roles.get_all_users()
    assert all("password_hash" not in u for u in users)
    ok("get_all_users strips password_hash")

    # role tiers exist
    assert set(roles.ROLES) == {"supervisor", "admin", "super_admin"}
    ok("3 role tiers defined")
except Exception as e:
    fail("Staff accounts", e)

# === MANDATORY EMAIL ON BOOKING ===
print("\n=== MANDATORY EMAIL ===")
try:
    from app.knowledge_base import create_booking
    from datetime import date

    r = create_booking("Ravi", "+919000000801", "Srisailam", "ac",
                        date(2027, 1, 1), date(2027, 1, 2), 1, 1, "30",
                        "Bharadwaja", customer_email="", send_whatsapp=False)
    assert not r["success"] and "email (Mail ID)" in r.get("missing_fields", [])
    ok("Booking without email rejected")

    r = create_booking("Ravi", "+919000000801", "Srisailam", "ac",
                        date(2027, 1, 1), date(2027, 1, 2), 1, 1, "30",
                        "Bharadwaja", customer_email="bad", send_whatsapp=False)
    assert not r["success"] and r.get("invalid_field") == "email"
    ok("Invalid email rejected")

    r = create_booking("Ravi", "+919000000801", "Srisailam", "ac",
                        date(2027, 1, 1), date(2027, 1, 2), 1, 1, "30",
                        "Bharadwaja", customer_email="ravi@example.com", send_whatsapp=False)
    assert r["success"] and r["total_price"] > 0
    ok("Valid booking with email accepted (total computed)")
except Exception as e:
    fail("Mandatory email", e)

# === WHATSAPP FLOW (caller phone auto-used) ===
print("\n=== WHATSAPP FLOW ===")
try:
    from app import whatsapp_flow as wf

    phone = "+919000000802"
    wf.handle_incoming(phone, "Hi")
    wf.handle_incoming(phone, "Meena")
    wf.handle_incoming(phone, "Kashyapa")
    r = wf.handle_incoming(phone, "meena@example.com")   # email step
    assert "location" in r.lower() or "place" in r.lower()
    wf.handle_incoming(phone, "Tirupathi")
    wf.handle_incoming(phone, "AC")
    wf.handle_incoming(phone, "2027-02-01 to 2027-02-03")
    conf = wf.handle_incoming(phone, "1")   # rooms -> confirm
    assert "confirm" in conf.lower()
    # phone was never asked
    sess = wf.get_session(phone)
    assert sess["data"]["customer_phone"] == phone
    ok("Flow collects fields; caller phone auto-used, never asked")

    done = wf.handle_incoming(phone, "YES")
    assert "confirmed" in done.lower() and "Booking ID" in done
    assert wf.get_session(phone) is None
    ok("Flow completes booking + returns payment options")

    # gotram rejection
    p2 = "+919000000803"
    wf.handle_incoming(p2, "Hi")
    wf.handle_incoming(p2, "Test")
    rej = wf.handle_incoming(p2, "NotAGotram")
    assert "not in our approved" in rej
    ok("Flow rejects invalid gotram")
except Exception as e:
    fail("WhatsApp flow", e)

# === RECEIPT + 80G ON PAYMENT ===
print("\n=== RECEIPT + 80G ON PAYMENT ===")
try:
    from app import knowledge_base as kb, payments as p
    from datetime import date

    b = kb.create_booking("Sita", "+919000000804", "Kasi", "ac",
                          date(2027, 3, 1), date(2027, 3, 3), 1, 2, "40",
                          "Gautama", customer_email="sita@example.com", send_whatsapp=False)
    assert b["success"]
    res = p.handle_payment_confirmed(payment_id=b["payment_id"])
    assert res["receipt"] is not None, "receipt should generate on room payment"
    assert res["certificate_80g"] is None, "room payment must not issue 80G"
    ok("Room payment -> receipt generated, no 80G")

    don = p.create_seva_donation_link("Sita", "+919000000804", "vedanidhi")
    dres = p.handle_payment_confirmed(payment_id=don["payment_id"])
    assert dres["certificate_80g"] is not None
    ok("Donation payment -> 80G certificate generated")
    _clean()
except Exception as e:
    fail("Receipt + 80G", e)
    _clean()

# === UPI URL ===
print("\n=== UPI GATEWAY URL ===")
try:
    from app import payments as p
    url = p.build_upi_url("PAY-TEST", 3000, "Room")
    assert url.startswith("upi://pay?")
    assert "am=3000" in url and "cu=INR" in url
    ok("build_upi_url produces valid UPI deep link")
except Exception as e:
    fail("UPI URL", e)

# === DONATIONS EXPOSED ===
print("\n=== DONATIONS ===")
try:
    from app import payments as p
    grouped = p.get_sevas_by_category()
    total = sum(len(v["options"]) for v in grouped.values())
    assert total == 13, f"expected 13 options, got {total}"
    ok("All 13 donation options exposed (grouped)")

    d = p.create_seva_donation_link("Donor", "+919000000805", "room_construction")
    assert d["success"] and d["amount"] == 500000 and d["is_80g"]
    ok("Donation payment link created (Room Construction, 80G)")
except Exception as e:
    fail("Donations", e)

# === API ROUTES ===
print("\n=== API ROUTES ===")
try:
    from app.main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    for pth in ("/api/login", "/api/users/{email}/password",
                "/api/whatsapp/incoming", "/api/payments/seva",
                "/api/donations/grouped"):
        assert pth in paths, f"missing {pth}"
    ok("New routes present (login, password, whatsapp/incoming, seva, grouped)")
except Exception as e:
    fail("API routes", e)

print(f"\n{'='*55}")
print(f"  RESULTS: {PASSED} PASSED | {FAILED} FAILED")
print(f"{'='*55}")
_clean()
sys.exit(1 if FAILED == 0 else 2)
