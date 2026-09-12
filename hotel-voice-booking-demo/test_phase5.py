"""
Phase 5 Tests — Gotram, Payments, Donations, WhatsApp.
Run: py test_phase5.py
"""
import os
import sys
from datetime import date, timedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed
    try:
        if fn():
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            errors.append(name)
            print(f"  [FAIL] {name}")
    except Exception as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  [FAIL] {name} — {e}")


print("\n=== GOTRAM ===")


def t_gotram_load():
    from app.gotram import get_all_gotrams, get_gotram_count
    assert get_gotram_count() > 0
    assert len(get_all_gotrams()) > 0
    return True


def t_gotram_allowed():
    from app.gotram import is_allowed, match_gotram
    assert is_allowed("Bharadwaja") == True
    assert is_allowed("bharadwaja gotram") == True   # suffix
    assert is_allowed("BHARADWAJA") == True           # case
    assert match_gotram("kashyap") == "Kashyapa"      # fuzzy
    return True


def t_gotram_rejected():
    from app.gotram import is_allowed, match_gotram
    assert is_allowed("NotARealGotram") == False
    assert match_gotram("xyzabc") is None
    return True


test("Gotram list loads", t_gotram_load)
test("Approved gotram accepted (case/suffix/fuzzy)", t_gotram_allowed)
test("Unknown gotram rejected", t_gotram_rejected)


print("\n=== PAYMENTS ===")


def t_room_payment():
    from app.payments import create_room_payment_link
    r = create_room_payment_link("BK-TEST01", 2400, "Test User", "9876543210")
    assert r["type"] == "room_booking"
    assert r["amount"] == 2400
    assert r["link"]
    return True


def t_donation_flexible():
    from app.payments import create_donation_link
    r = create_donation_link("Devotee", "9876543210", amount_inr=0)
    assert r["type"] == "donation"
    assert r["flexible"] == True
    assert r["link"]
    return True


def t_donation_seva():
    from app.payments import create_donation_link, get_seva_options
    sevas = get_seva_options()
    assert len(sevas) >= 6
    r = create_donation_link("Devotee", "9876543210", seva_id="nityannadanam")
    assert r["seva_id"] == "nityannadanam"
    assert r["amount"] == 30000
    return True


test("Room payment link (fixed amount)", t_room_payment)
test("Donation link (flexible/any amount)", t_donation_flexible)
test("Donation link (seva fixed amount)", t_donation_seva)


print("\n=== WHATSAPP ===")


def t_whatsapp_compose():
    from app.whatsapp import compose_booking_message
    booking = {
        "customer_name": "Ravi", "location": "Srisailam", "room_type": "AC",
        "check_in": "2026-07-01", "check_out": "2026-07-03", "num_rooms": 1,
        "gotram": "Bharadwaja", "total_price": 2400, "booking_id": "BK-TEST01",
    }
    msg = compose_booking_message(booking, "https://rzp.io/pay", "https://rzp.io/donate")
    assert "Ravi" in msg
    assert "Srisailam" in msg
    assert "Bharadwaja" in msg
    assert "https://rzp.io/pay" in msg
    assert "https://rzp.io/donate" in msg
    return True


def t_whatsapp_send():
    from app.whatsapp import send_whatsapp
    r = send_whatsapp("9876543210", "Test message")
    assert r["success"] == True   # mock mode always succeeds
    return True


test("WhatsApp message composition", t_whatsapp_compose)
test("WhatsApp send (mock)", t_whatsapp_send)


print("\n=== BOOKING WITH GOTRAM ===")


def t_booking_requires_gotram():
    from app.knowledge_base import create_booking
    # Missing gotram → should fail
    r = create_booking(
        customer_name="Test", customer_phone="9876543210",
        location="Srisailam", room_type="ac",
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=12),
        gotram="",
    )
    assert r["success"] == False
    assert "gotram" in str(r.get("missing_fields", [])).lower() or "gotram" in r.get("error", "").lower()
    return True


def t_booking_rejects_bad_gotram():
    from app.knowledge_base import create_booking
    r = create_booking(
        customer_name="Test", customer_phone="9876543210",
        location="Srisailam", room_type="ac",
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=12),
        gotram="FakeGotram123", customer_email="test@example.com",
    )
    assert r["success"] == False
    assert r.get("gotram_rejected") == True
    return True


def t_booking_success_with_gotram():
    from app.knowledge_base import create_booking, cancel_booking
    r = create_booking(
        customer_name="Ravi Kumar", customer_phone="9876543210",
        location="Srisailam", room_type="ac",
        check_in=date.today() + timedelta(days=20),
        check_out=date.today() + timedelta(days=22),
        gotram="Bharadwaja", customer_email="ravi@example.com",
        send_whatsapp=True,
    )
    assert r["success"] == True, f"Booking failed: {r}"
    assert r["payment_link"], "No payment link generated"
    assert r["donation_link"], "No donation link generated"
    assert r["details"]["gotram"] == "Bharadwaja"
    # Cleanup
    cancel_booking(r["booking_id"])
    return True


test("Booking requires gotram (rejects empty)", t_booking_requires_gotram)
test("Booking rejects unapproved gotram", t_booking_rejects_bad_gotram)
test("Booking success generates payment + donation + WhatsApp", t_booking_success_with_gotram)


print("\n=== APP IMPORTS ===")


def t_app_loads():
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/gotrams" in routes
    assert "/api/payments" in routes
    assert "/api/donations" in routes
    assert "/api/donations/sevas" in routes
    return True


test("App loads with new routes", t_app_loads)


print("\n" + "=" * 55)
print(f"  RESULTS: {passed} PASSED | {failed} FAILED")
print("=" * 55)
if errors:
    print("\n  FAILURES:")
    for e in errors:
        print(f"    - {e}")
print()
sys.exit(0 if failed == 0 else 1)
