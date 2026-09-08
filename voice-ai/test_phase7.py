"""
Phase 7 Test Suite — Gap closures: payment automation, relative dates, consent.
Run:  py test_phase7.py
"""

import sys
import os
import glob

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


def _cleanup_pdfs():
    for f in glob.glob("app/generated/**/*.pdf", recursive=True):
        try:
            os.remove(f)
        except Exception:
            pass


# === PAYMENT AUTOMATION LOOP ===
print("=== PAYMENT AUTOMATION ===")
try:
    from app import payments

    # A donation, once confirmed, should auto-issue an 80G certificate.
    d = payments.create_seva_donation_link("Auto Test", "+919000000010", "nityannadanam")
    assert d["success"]
    assert d.get("certificate_80g_issued") in (False, None)

    result = payments.handle_payment_confirmed(payment_id=d["payment_id"])
    assert result["success"]
    assert result["certificate_80g"] is not None, "80G cert should auto-generate"
    assert result["whatsapp"] is not None, "WhatsApp push should fire"
    ok("Confirmed donation auto-issues 80G certificate + WhatsApp")

    rec = payments.get_payment(d["payment_id"])
    assert rec["status"] == "paid"
    assert rec["certificate_80g_issued"] is True
    ok("Payment marked paid + cert flag set")

    # Idempotency: confirming again should NOT regenerate
    result2 = payments.handle_payment_confirmed(payment_id=d["payment_id"])
    assert result2["certificate_80g"] is None, "Should not regenerate cert"
    ok("Idempotent — no duplicate certificate")

    # Room payment (not 80G) should NOT generate a certificate
    room = payments.create_room_payment_link("BK-AUTO-1", 2400, "Room Guy", "+919000000011")
    r3 = payments.handle_payment_confirmed(payment_id=room["payment_id"])
    assert r3["success"]
    assert r3["certificate_80g"] is None, "Room payment must not issue 80G"
    ok("Room payment confirmed — no 80G certificate (correct)")

    _cleanup_pdfs()
except Exception as e:
    fail("Payment automation", e)
    _cleanup_pdfs()

# === WEBHOOK SIGNATURE + PARSING ===
print("\n=== WEBHOOK ===")
try:
    from app import payments
    import json, hmac, hashlib

    # No secret configured -> skip verification (mock/demo)
    assert payments.verify_webhook_signature(b'{}', "") is True
    ok("No-secret mode skips signature (mock)")

    # With a secret -> valid signature accepted, bad rejected
    payments.RAZORPAY_WEBHOOK_SECRET = "s3cr3t"
    body = json.dumps({"event": "payment_link.paid"}).encode()
    good = hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert payments.verify_webhook_signature(body, good) is True
    assert payments.verify_webhook_signature(body, "bad") is False
    payments.RAZORPAY_WEBHOOK_SECRET = ""  # reset
    ok("HMAC signature: valid accepted, invalid rejected")

    # Event parsing
    d = payments.create_seva_donation_link("Hook Test", "+919000000012", "one_day_annadanam")
    payload = {"event": "payment_link.paid",
               "payload": {"payment_link": {"entity": {"reference_id": d["payment_id"]}}}}
    parsed = payments.parse_webhook_event(payload)
    assert parsed["event"] == "payment_link.paid"
    assert parsed["reference_id"] == d["payment_id"]
    ok("Webhook payload parsed (reference_id extracted)")

    _cleanup_pdfs()
except Exception as e:
    fail("Webhook", e)
    _cleanup_pdfs()

# === RELATIVE DATE PARSING ===
print("\n=== RELATIVE DATES ===")
try:
    from app.normalizer import _extract_dates, _next_weekday
    from datetime import date, timedelta

    today = date.today()

    r = _extract_dates("book for tomorrow")
    assert r["check_in"] == (today + timedelta(days=1)).isoformat()
    ok("tomorrow")

    r = _extract_dates("day after tomorrow")
    assert r["check_in"] == (today + timedelta(days=2)).isoformat()
    ok("day after tomorrow")

    # this weekend vs next weekend must differ by 7 days
    tw = _extract_dates("this weekend")["check_in"]
    nw = _extract_dates("next weekend")["check_in"]
    assert date.fromisoformat(nw) - date.fromisoformat(tw) == timedelta(days=7)
    ok("this weekend vs next weekend differ by a week")

    # named weekday resolves to a future date of that weekday
    r = _extract_dates("next friday")
    assert date.fromisoformat(r["check_in"]).weekday() == 4
    assert date.fromisoformat(r["check_in"]) > today
    ok("next friday -> future Friday")

    # date range captures both
    r = _extract_dates("June 28 to June 30")
    assert "check_in" in r and "check_out" in r
    assert r["check_out"] > r["check_in"]
    ok("explicit date range -> check_in + check_out")

    # duration
    r = _extract_dates("tomorrow for 3 nights")
    assert r["num_nights"] == 3
    ci = date.fromisoformat(r["check_in"])
    assert date.fromisoformat(r["check_out"]) == ci + timedelta(days=3)
    ok("duration (3 nights) -> check_out")

    # ISO passthrough
    r = _extract_dates("check in 2026-09-01 out 2026-09-05")
    assert r["check_in"] == "2026-09-01" and r["check_out"] == "2026-09-05"
    ok("explicit ISO dates")

    # never returns today for a weekday==today request (always future)
    wd_today = today.weekday()
    name = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][wd_today]
    r = _extract_dates(name)
    assert date.fromisoformat(r["check_in"]) > today
    ok("weekday == today resolves to next week (future)")
except Exception as e:
    fail("Relative dates", e)

# === FULL NORMALIZE PIPELINE ===
print("\n=== NORMALIZE PIPELINE ===")
try:
    from app.normalizer import normalize_query
    r = normalize_query("book next friday for 2 nights at srisailam ac")
    ex = r["extracted"]
    assert ex.get("check_in") and ex.get("check_out")
    assert ex.get("num_nights") == 2
    assert ex.get("location") == "Srisailam"
    assert ex.get("room_type") == "ac"
    ok("normalize_query extracts dates + location + room_type together")
except Exception as e:
    fail("Normalize pipeline", e)

# === CONSENT DISCLOSURE ===
print("\n=== CONSENT DISCLOSURE ===")
try:
    from app import ai_engine
    g = ai_engine.CACHED_GREETING
    assert "recorded" in g.lower(), "Greeting must disclose recording"
    assert "ai assistant" in g.lower(), "Greeting must disclose AI"
    ok("Greeting discloses AI + call recording")

    assert "recorded" in ai_engine.SYSTEM_PROMPT.lower()
    ok("System prompt includes recording-consent rule")
except Exception as e:
    fail("Consent disclosure", e)

# === API ROUTE PRESENT ===
print("\n=== WEBHOOK ROUTE ===")
try:
    from app.main import app
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/payments/webhook" in paths, "Webhook route missing"
    ok("/api/payments/webhook route registered")
except Exception as e:
    fail("Webhook route", e)

# === SUMMARY ===
print(f"\n{'='*55}")
print(f"  RESULTS: {PASSED} PASSED | {FAILED} FAILED")
print(f"{'='*55}")
_cleanup_pdfs()
sys.exit(1 if FAILED == 0 else 2)
