# Authentication — How Voice AI and Flutter PMS Share Accounts

This document explains how the previously conflicting authentication systems
were unified, so **one staff account logs into both** the Voice-AI backend and
the Flutter PMS.

## The problem (before)

| System        | Password storage            | Authentication          | Users |
|---------------|-----------------------------|-------------------------|-------|
| Voice AI      | PBKDF2 hashes in Firestore  | `roles.authenticate()`  | karivena.org |
| Flutter PMS   | Firebase Auth passwords     | `signInWithEmailAndPassword()` | example.com |

Both read roles from the same Firestore `users` collection, but they verified
passwords differently — so an account seeded for one system could not log into
the other.

## The fix (now) — one source of truth per concern

```
                 ┌─────────────────────────────┐
   CREDENTIALS   │        Firebase Auth         │  ← both systems verify
   (email+pass)  │  (email/password accounts)   │    passwords here
                 └─────────────┬───────────────┘
                               │  same email
                 ┌─────────────▼───────────────┐
   ROLE/PROFILE  │  Firestore `users` (by email)│  ← both systems read
                 │  { role, name, active, ... } │    role/profile here
                 └─────────────────────────────┘
```

- **Firebase Auth** is the single source of truth for **credentials**.
- **Firestore `users`** is the single source of truth for **role and profile**.
- Every staff account exists in **both**, keyed by the same lowercased email.

### What each system now does

**Flutter PMS** (unchanged, already correct):
1. `signInWithEmailAndPassword()` against Firebase Auth
2. Loads the role from Firestore `users/{email}`

**Voice-AI backend** (`roles.authenticate()`):
1. Verifies the password against **Firebase Auth** via the Identity Toolkit REST
   API (`signInWithPassword`, using `FIREBASE_WEB_API_KEY`)
2. Falls back to the **PBKDF2 hash** in Firestore if Firebase Auth can't be
   reached or no web API key is set (offline/local dev)
3. Loads the role from Firestore `users/{email}`

The response includes `auth_method` (`firebase` or `pbkdf2`) so you can see which
path verified the login.

## How accounts are created (the bridge)

`seed_staff.py` and `roles.create_user()` now provision **both** sides at once:

- `roles.upsert_firebase_auth_user(email, password, name)` creates/updates the
  **Firebase Auth** account (via the Admin SDK).
- The Firestore `users/{email}` doc stores `role`, `name`, `active`,
  `firebase_uid`, and a PBKDF2 `password_hash` (fallback).

So the same email + password works in the Flutter PMS **and** the Voice-AI
backend immediately.

## Seed the staff accounts

```bash
python seed_staff.py            # create accounts (skips existing)
python seed_staff.py --reset    # reset passwords + (re)create Firebase Auth users
```

Provisions: 1 super-admin, 3 admins, 5 supervisors (all `@karivena.org`).
Passwords are written once to `staff_credentials.txt` (gitignored) — distribute
securely, then delete.

## Configuration

Add to `.env`:

```
FIREBASE_ENABLED=true
FIREBASE_KEY_PATH=firebase-key.json          # Admin SDK (creates Auth users)
FIREBASE_WEB_API_KEY=<your Firebase Web API key>   # REST password verification
```

- `firebase-key.json` — Admin service-account key (Firebase console → Project
  settings → Service accounts → Generate new private key).
- `FIREBASE_WEB_API_KEY` — Firebase console → Project settings → General → Web
  API Key. This is the same key the Flutter web app uses.

## Answering the original questions

- **"Which approach?"** — Option 1 (bridge), done cleanly: Firebase Auth for
  credentials, Firestore for roles. No need for separate `example.com` users.
- **"Add a password field to Firestore?"** — A PBKDF2 hash is kept as a fallback,
  but the real credential lives in Firebase Auth.
- **"Modify Flutter to support both?"** — Not needed. Flutter keeps using
  Firebase Auth; the Voice-AI backend was changed to verify against Firebase Auth
  too, so they converge on the same accounts.

## Security notes

- Do not commit `.env`, `firebase-key.json`, or `staff_credentials.txt`.
- Rotate any credentials that were ever committed.
- Consider disabling the PBKDF2 fallback in production once Firebase Auth is
  guaranteed reachable (set a policy in `roles.authenticate`).
