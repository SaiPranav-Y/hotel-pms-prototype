# Temple PMS — Core Hardening (Roadmap Section 2)

This document describes the production-hardening layer added across the Flutter
PMS and the Python voice-AI backend. It implements the "Technical Debt &
Scalability" items from the roadmap: security rules, concurrency control, audit
trails, validation/sanitization, and paginated/cached reads.

## 1. Firestore Security Rules (`firestore.rules`)

Previously **absent** — any authenticated client could read/write every
collection. Now enforced at the database layer, mirroring the app's role model.

- Identity = the caller's email (`request.auth.token.email`). The
  `users/{email}` doc holds `{ role, active }`.
- Helpers: `isSignedIn`, `isActiveStaff`, `isAdmin`, `isSuperAdmin`.
- `reservations`: active staff read/create/update; **admin-only delete**.
- `audit_logs`: **append-only** (create by active staff; no update/delete);
  read restricted to admins.
- `temples`, `rates`, `sevas`, `allowed_gotrams`: read = active staff, write =
  admin.
- `payments`, `calls`: read = active staff; **client writes denied** (written by
  the backend Admin SDK, which bypasses rules).
- `users`: a user may read only their own doc; super-admin may list/write.
- `contacts`, `guests`, `room_assignments`, `room_states`: active staff.
- Everything else: **deny by default**.

> The Python backend and voice-gateway use the **Admin SDK** (service account),
> which bypasses these rules — so voice/WhatsApp writes are unaffected.

**Deploy:** `firebase deploy --only firestore:rules,firestore:indexes`
(`firebase.json` now references `firestore.rules` + `firestore.indexes.json`).

## 2. Concurrency Control — no more double-booking

Availability is tracked with per-`(temple, date)` counter documents in the
`availability` collection (id `"<templeKey>__<yyyy-MM-dd>"`, fields
`{ temple_name, date, capacity, booked }`).

- **Flutter** (`firestore_service.createReservationAtomic`): a `runTransaction`
  reads every night's counter, verifies `booked + rooms <= capacity`, then
  writes the reservation and `FieldValue.increment(rooms)` on each counter —
  atomically. Throws `RoomUnavailableException` if full.
- **Python** (`firebase_store.book_reservation_atomic`): the same logic via
  `@firestore.transactional` (Admin SDK). `knowledge_base.create_booking` uses
  it for voice/WhatsApp bookings.

Because walk-in, voice, and WhatsApp all contend on the **same counters**, the
last room cannot be sold twice. Cancels/deletes call `releaseReservationCounters`
/ `release_reservation_counters` to free the rooms.

**Verified** against live Firestore: capacity-2 temple → 2 bookings succeed, 3rd
rejected, release frees a room, rebooking succeeds.

## 3. Audit Trail (`audit_logs`)

Every reservation create / update / delete / cancel writes an **immutable**
entry: `{ entity_type, entity_id, action, actor, source, previous_state,
new_state, timestamp, notes }`.

- **Flutter**: `AuditService.log()` (actor = signed-in Firebase Auth email).
- **Python**: `audit.log_event()` (actor = phone/channel; in-memory ring buffer
  + Firestore). Read via `GET /api/audit` (admin-gated).
- Sensitive fields (`password_hash`, `transcript`, payment links) are stripped
  before logging. Auditing never throws — it cannot block the primary action.

## 4. Validation & Sanitization

Shared rules on both sides (`lib/utils/validators.dart` ↔ `app/validators.py`):

- **Names**: strip control chars + markup (`<`, `>`), collapse whitespace, cap
  length; Telugu block preserved.
- **Phone**: normalize to `+91XXXXXXXXXX` (handles spaces, `0`/`91` prefixes);
  reject anything that isn't a 10-digit mobile starting 6–9.
- **Email**: format-checked.
- **Stay**: both dates required, check-out after check-in, not in the past, ≤ 60
  nights.
- **Rooms**: 1–100.

The walk-in form validators delegate to `Validators`; the backend
`create_booking` sanitizes + validates before persisting (returns
`invalid_field`). The reservations view has error-boundary + retry, loading, and
empty states.

## 5. Pagination & Local Caching

- The reservations listener is now **bounded** (`getReservationsStream({limit=100})`)
  instead of streaming the entire collection.
- **Cursor pagination**: `fetchReservationsPage({startAfter, pageSize=25,
  templeName, status})` returns a `ReservationPage { reservations, lastDocument,
  hasMore }`, backed by the composite indexes in `firestore.indexes.json`.
- **Local cache**: Firestore persistence enabled (40 MB) in `main.dart`, cutting
  repeat network reads and cost.

## Tests

`py test_phase10.py` — 29 hardening tests (validators, audit, counter helpers).
Full suite: 151 backend tests across 7 files, 0 failures.

## Notes / follow-ups

- The `availability` counters are authoritative for booking. A one-time backfill
  (sum existing reservations per temple/date) is recommended before go-live so
  counters reflect current occupancy.
- The paginated browsing screen (infinite scroll UI) is not yet wired into the
  reservations view; the API is ready for it.
- Cloud Functions codebase (`functions/`) referenced in `firebase.json` is a
  future item (server-side payload compression / triggers).
