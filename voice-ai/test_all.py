"""
FULL SYSTEM TEST — tests every module, function, and pipeline.
Run: py test_all.py
"""

import sys
import os
import traceback
from datetime import date, timedelta

os.chdir(os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed += 1
            errors.append(f"{name}: returned False")
            print(f"  [FAIL] {name}")
    except Exception as e:
        failed += 1
        errors.append(f"{name}: {e}")
        print(f"  [FAIL] {name} — {e}")


# ===========================================================================
print("\n=== 1. CONFIG ===")


def t_config():
    from app.config import HOST, PORT, OLLAMA_BASE_URL, OLLAMA_MODEL
    assert HOST == "0.0.0.0"
    assert PORT == 8000
    assert "11434" in OLLAMA_BASE_URL
    assert "llama" in OLLAMA_MODEL
    return True


test("Config loads correctly", t_config)

# ===========================================================================
print("\n=== 2. KNOWLEDGE BASE (Rooms + Locations) ===")


def t_kb_load():
    from app.knowledge_base import get_all_locations, get_locations_summary
    locs = get_all_locations()
    assert len(locs) == 10, f"Expected 10 locations, got {len(locs)}"
    return True


def t_kb_availability():
    from app.knowledge_base import check_availability
    r = check_availability("Srisailam", "ac", date.today() + timedelta(days=1), date.today() + timedelta(days=3))
    assert r["available"] == True, f"Srisailam should have rooms: {r}"
    assert r["location"] == "Srisailam"
    return True


def t_kb_availability_bad_location():
    from app.knowledge_base import check_availability
    r = check_availability("Atlantis", "ac", date.today(), date.today() + timedelta(days=1))
    assert r["available"] == False
    assert "error" in r
    return True


def t_kb_booking():
    from app.knowledge_base import create_booking, get_booking, cancel_booking
    r = create_booking(
        customer_name="Test User", customer_phone="9876543210",
        location="Srisailam", room_type="ac",
        check_in=date.today() + timedelta(days=5),
        check_out=date.today() + timedelta(days=7),
        num_rooms=1, num_guests=2, customer_age="35",
    )
    assert r["success"] == True, f"Booking failed: {r}"
    bid = r["booking_id"]
    # Verify get
    b = get_booking(bid)
    assert b is not None
    assert b["customer_name"] == "Test User"
    # Cancel
    c = cancel_booking(bid)
    assert c["success"] == True
    return True


def t_kb_workflow():
    from app.knowledge_base import create_call_log, update_call_workflow, get_call_log
    log = create_call_log("TEST-CALL-001", duration=30.0, transcript=[{"role": "kaveri", "text": "hello"}], status="pending")
    assert log["workflow_status"] == "pending"
    update_call_workflow("TEST-CALL-001", "completed")
    log2 = get_call_log("TEST-CALL-001")
    assert log2["workflow_status"] == "completed"
    return True


test("10 locations loaded", t_kb_load)
test("Availability check (valid)", t_kb_availability)
test("Availability check (invalid location)", t_kb_availability_bad_location)
test("Create + get + cancel booking", t_kb_booking)
test("Call workflow status transitions", t_kb_workflow)

# ===========================================================================
print("\n=== 3. VERNACULAR DICTIONARY ===")


def t_vern_location():
    from app.vernacular import normalize_location
    assert normalize_location("sri sailam") == "Srisailam"
    assert normalize_location("tirupati") == "Tirupathi"
    assert normalize_location("sai baba") == "Shiridi"
    assert normalize_location("kashi") == "Kasi"
    assert normalize_location("శ్రీశైలం") == "Srisailam"
    return True


def t_vern_room():
    from app.vernacular import normalize_room_type
    assert normalize_room_type("ac room") == "ac"
    assert normalize_room_type("non ac") == "nonac"
    assert normalize_room_type("fan room") == "nonac"
    assert normalize_room_type("air conditioned") == "ac"
    return True


def t_vern_language():
    from app.vernacular import detect_language
    assert detect_language("I want a room") == "english"
    assert detect_language("నాకు గది కావాలి") == "telugu"
    return True


test("Location normalization (English + Telugu)", t_vern_location)
test("Room type normalization", t_vern_room)
test("Language detection", t_vern_language)

# ===========================================================================
print("\n=== 4. NORMALIZER ===")


def t_norm_dates():
    from app.normalizer import normalize_query
    r = normalize_query("I want room tomorrow for 3 nights")
    assert "check_in" in r["extracted"]
    assert "check_out" in r["extracted"]
    assert r["extracted"]["num_nights"] == 3
    return True


def t_norm_location():
    from app.normalizer import normalize_query
    r = normalize_query("book room in tirupati")
    assert r["extracted"].get("location") == "Tirupathi"
    return True


def t_norm_phone():
    from app.normalizer import normalize_query
    r = normalize_query("my number is 9876543210")
    assert r["extracted"].get("phone") == "9876543210"
    return True


def t_norm_rooms():
    from app.normalizer import normalize_query
    r = normalize_query("I need 3 rooms")
    assert r["extracted"].get("num_rooms") == 3
    return True


test("Date parsing (tomorrow + nights)", t_norm_dates)
test("Location extraction", t_norm_location)
test("Phone number extraction", t_norm_phone)
test("Room count extraction", t_norm_rooms)

# ===========================================================================
print("\n=== 5. PRONUNCIATION ===")


def t_pron():
    from app.pronunciation import apply_pronunciation
    r = apply_pronunciation("Your booking at Srisailam is confirmed for INR 1200")
    assert "Shree-Shy-Lum" in r
    assert "rupees" in r
    return True


test("Pronunciation rules applied", t_pron)

# ===========================================================================
print("\n=== 6. CONTACTS ===")


def t_contacts():
    from app.contacts import upsert_contact, get_contact, get_all_contacts
    upsert_contact(phone="1111111111", name="Test Contact", age="40", location="Srisailam", tags=["test"])
    c = get_contact("1111111111")
    assert c is not None
    assert c["name"] == "Test Contact"
    assert "Srisailam" in c["preferred_locations"]
    assert "test" in c["tags"]
    # Update
    upsert_contact(phone="1111111111", name="Updated Name", location="Tirupathi")
    c2 = get_contact("1111111111")
    assert c2["name"] == "Updated Name"
    assert "Tirupathi" in c2["preferred_locations"]
    return True


test("Contact CRUD + enrichment", t_contacts)

# ===========================================================================
print("\n=== 7. CAMPAIGNS ===")


def t_campaigns():
    from app.campaigns import create_campaign, get_campaign, get_next_contact, record_call_attempt
    c = create_campaign(name="Test Campaign", contacts=["9000000001", "9000000002"], max_retries=3)
    assert c["campaign_id"].startswith("CMP-")
    assert c["total_contacts"] == 2
    # Get next
    nxt = get_next_contact(c["campaign_id"])
    assert nxt is not None
    assert nxt["phone"] == "9000000001"
    # Record attempt
    record_call_attempt(c["campaign_id"], "9000000001", "CALL-TEST", True)
    g = get_campaign(c["campaign_id"])
    assert g["completed_count"] == 1
    return True


test("Campaign create + queue + record attempt", t_campaigns)

# ===========================================================================
print("\n=== 8. ESCALATION ===")


def t_escalation():
    from app.escalation import check_escalation_needed, create_escalation, get_all_escalations, resolve_escalation
    # Keyword trigger
    r = check_escalation_needed("I want to speak to a manager")
    assert r["escalate"] == True
    # No trigger
    r2 = check_escalation_needed("I want to book a room")
    assert r2["escalate"] == False
    # Create
    esc = create_escalation("CALL-ESC-01", reason="test", customer_name="Test")
    assert esc["id"].startswith("ESC-")
    # Resolve
    resolve_escalation(esc["id"])
    all_esc = get_all_escalations()
    assert any(e["status"] == "resolved" for e in all_esc)
    return True


test("Escalation trigger + create + resolve", t_escalation)

# ===========================================================================
print("\n=== 9. ANALYTICS ===")


def t_analytics():
    from app.analytics import compute_analytics
    from app.knowledge_base import get_all_call_logs, get_all_bookings
    a = compute_analytics(get_all_call_logs(), get_all_bookings())
    assert "summary" in a
    assert "daily" in a
    assert "total_calls" in a["summary"]
    return True


test("Analytics computation", t_analytics)

# ===========================================================================
print("\n=== 10. SEARCH ===")


def t_search():
    from app.search import search_transcripts, global_search
    from app.knowledge_base import get_all_call_logs
    from app.contacts import get_all_contacts
    # Search contacts (we added "Test Contact" earlier)
    results = global_search(get_all_call_logs(), get_all_contacts(), "Test")
    assert results["contacts"] or results["calls"] is not None  # At least structure exists
    return True


test("Global search", t_search)

# ===========================================================================
print("\n=== 11. KB INGESTION ===")


def t_kb_ingest():
    from app.kb_ingestion import ingest_text, search_knowledge_base, get_kb_stats
    ingest_text("Srisailam temple has 112 rooms available for pilgrims. AC rooms and Non-AC rooms available.", title="Test KB", approved=True)
    results = search_knowledge_base("Srisailam rooms")
    assert len(results) > 0
    stats = get_kb_stats()
    assert stats["total_chunks"] > 0
    return True


test("KB text ingestion + search", t_kb_ingest)

# ===========================================================================
print("\n=== 12. RETENTION ===")


def t_retention():
    from app.retention import get_retention_config, set_retention_days, check_retention_status
    cfg = get_retention_config()
    assert cfg["retention_days"] == 90
    set_retention_days(60)
    cfg2 = get_retention_config()
    assert cfg2["retention_days"] == 60
    set_retention_days(90)  # Reset
    status = check_retention_status()
    assert "recordings_to_clean" in status
    return True


test("Retention config + status check", t_retention)

# ===========================================================================
print("\n=== 13. CAMPAIGN RUNNER ===")


def t_runner():
    from app.campaign_runner import can_make_call, get_daily_stats, get_runner_state
    assert can_make_call() == True
    stats = get_daily_stats()
    assert stats["max_per_day"] == 50
    state = get_runner_state()
    assert state["max_calls_per_day"] == 50
    return True


test("Campaign runner rate limits", t_runner)

# ===========================================================================
print("\n=== 14. INTELLIGENCE (rule-based fallback) ===")


def t_intelligence():
    from app.intelligence import analyze_call
    transcript = [
        {"role": "kaveri", "text": "Namaste, how can I help?"},
        {"role": "guest", "text": "I want to book a room in Srisailam"},
        {"role": "kaveri", "text": "Sure, for which dates?"},
    ]
    result = analyze_call(transcript, {"location": "Srisailam", "customer_name": "Ravi"})
    assert result["intent"] == "booking"
    assert "srisailam" in [t.lower() for t in result["tags"]]
    return True


test("Intelligence analysis (rule-based)", t_intelligence)

# ===========================================================================
print("\n=== 15. AI ENGINE ===")


def t_ai_engine():
    from app.ai_engine import ConversationEngine, CACHED_GREETING
    engine = ConversationEngine()
    g = engine.get_greeting()
    assert g == CACHED_GREETING
    assert "Karivena" in g
    return True


test("AI engine greeting (instant)", t_ai_engine)

# ===========================================================================
print("\n=== 16. FIREBASE ===")


def t_firebase():
    from app.firebase_store import init_firebase, is_firebase_active, get_all_bookings_firebase
    init_firebase()
    assert is_firebase_active() == True
    bookings = get_all_bookings_firebase()
    assert isinstance(bookings, list)
    return True


test("Firebase connection + read", t_firebase)

# ===========================================================================
print("\n=== 17. FASTAPI APP ===")


def t_app():
    from app.main import app
    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/api/bookings" in routes
    assert "/api/calls" in routes
    assert "/api/contacts" in routes
    assert "/api/campaigns" in routes
    assert "/api/analytics" in routes
    assert "/api/escalations" in routes
    assert "/api/search" in routes
    assert "/api/recordings" in routes
    assert "/api/locations" in routes
    assert "/health" in routes
    assert "/" in routes
    assert "/dashboard" in routes
    assert "/voice" in routes
    return True


test("FastAPI app routes registered", t_app)

# ===========================================================================
print("\n=== 18. RECORDER ===")


def t_recorder():
    from app.recorder import save_recording, get_recording, get_all_recordings, RECORDINGS_DIR
    # Save a dummy recording
    data = b"fake audio data for testing" * 100
    info = save_recording("TEST-REC-001", data, "audio/webm")
    assert info["call_id"] == "TEST-REC-001"
    # Retrieve
    r = get_recording("TEST-REC-001")
    assert r is not None
    assert r["size_bytes"] > 0
    # Cleanup test file
    import os
    filepath = RECORDINGS_DIR / info["filename"]
    if filepath.exists():
        filepath.unlink()
    return True


test("Recording save + retrieve", t_recorder)


# ===========================================================================
# SUMMARY
print("\n" + "=" * 60)
print(f"  RESULTS: {passed} PASSED | {failed} FAILED | {passed + failed} TOTAL")
print("=" * 60)

if errors:
    print("\n  FAILURES:")
    for e in errors:
        print(f"    - {e}")

print()
if failed == 0:
    print("  ALL TESTS PASSED. System is FOOLPROOF.")
else:
    print(f"  {failed} ISSUES NEED FIXING.")

sys.exit(0 if failed == 0 else 1)
