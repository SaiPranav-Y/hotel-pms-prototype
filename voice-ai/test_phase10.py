"""
Phase 10 — Hardening tests: validators/sanitization, audit trail, and the
availability-counter helpers used by concurrency-safe booking.

Run: py test_phase10.py
"""
import sys
from datetime import date, timedelta

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")


print("=== VALIDATORS ===")
from app import validators as v

# phone normalization
check("normalize +91 spacing", v.normalize_phone("98765 43210") == "+919876543210")
check("normalize 0-prefix", v.normalize_phone("098765 43210") == "+919876543210")
check("normalize 91-prefix", v.normalize_phone("919876543210") == "+919876543210")
check("valid phone true", v.is_valid_phone("9876543210") is True)
check("valid phone false (short)", v.is_valid_phone("12345") is False)
check("valid phone false (starts 1)", v.is_valid_phone("1234567890") is False)

# email
check("email ok", v.is_valid_email("a.b@c.co") is True)
check("email bad", v.is_valid_email("nope@") is False)

# name sanitization strips markup / control chars
n = v.sanitize_name("  Ravi<script>alert(1)</script>  Kumar  ")
check("name strips angle brackets", "<" not in n and ">" not in n)
check("name collapses whitespace", "  " not in n)
check("name valid", v.is_valid_name("Ravi Kumar") is True)
check("name too short invalid", v.is_valid_name("R") is False)

# stay validation
ok, _ = v.validate_stay(date.today() + timedelta(days=1), date.today() + timedelta(days=3))
check("stay ok", ok is True)
ok, _ = v.validate_stay(date.today() - timedelta(days=1), date.today())
check("stay past rejected", ok is False)
ok, _ = v.validate_stay(date.today() + timedelta(days=2), date.today() + timedelta(days=1))
check("stay checkout<=checkin rejected", ok is False)
ok, _ = v.validate_stay(date.today(), date.today() + timedelta(days=90))
check("stay >60 nights rejected", ok is False)

# rooms
ok, _ = v.validate_rooms(3)
check("rooms 3 ok", ok is True)
ok, _ = v.validate_rooms(0)
check("rooms 0 rejected", ok is False)
ok, _ = v.validate_rooms(500)
check("rooms 500 rejected", ok is False)


print("\n=== AUDIT ===")
from app import audit

before = len(audit.get_recent(1000))
e = audit.log_event(
    "reservation", "BK-XYZ", "create",
    actor="+919999999999", source="walk_in",
    new_state={"customer_name": "T", "password_hash": "SECRET", "total_price": 900},
)
check("audit action recorded", e["action"] == "create")
check("audit strips password_hash", "password_hash" not in (e["new_state"] or {}))
check("audit keeps safe fields", e["new_state"].get("total_price") == 900)
check("audit has timestamp+actor", bool(e["timestamp"]) and e["actor"] == "+919999999999")
recent = audit.get_recent(10, entity_id="BK-XYZ")
check("audit get_recent filters by entity", all(x["entity_id"] == "BK-XYZ" for x in recent) and len(recent) >= 1)
check("audit ring buffer grew", len(audit.get_recent(1000)) > before)


print("\n=== AVAILABILITY COUNTER HELPERS ===")
from app import firebase_store as fs

check("temple key normalizes", fs._temple_key("Sri Kalahasti ") == "sri_kalahasti")
did = fs._availability_doc_id("Srisailam", date(2027, 1, 5))
check("availability doc id format", did == "srisailam__2027-01-05")
nights = fs._nights_of(date(2027, 1, 1), date(2027, 1, 4))
check("nights_of exclusive checkout (3 nights)", len(nights) == 3 and nights[0] == date(2027, 1, 1) and nights[-1] == date(2027, 1, 3))
nights1 = fs._nights_of(date(2027, 1, 1), date(2027, 1, 1))
check("nights_of same-day -> 1 night", len(nights1) == 1)


print(f"\n{'='*44}")
print(f"  RESULTS: {PASS} PASSED | {FAIL} FAILED")
print(f"{'='*44}")
sys.exit(0 if FAIL == 0 else 1)
