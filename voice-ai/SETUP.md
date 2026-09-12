# Karivena Satram — Setup Guide

The platform has two parts:
- **Voice-AI backend** (Python / FastAPI) — this folder
- **Flutter PMS app** — the `lib/` folder in the repo

Both share the same Firebase project and staff accounts (see `AUTH.md`).

---

## 1. Backend — one command

```bash
python setup.py
```

This installs dependencies, creates `.env`, and checks Ollama. Then:

```bash
python run.py
```

Open:
- Voice / call UI — http://localhost:8000
- Dashboard — http://localhost:8000/dashboard
- API docs — http://localhost:8000/docs

### Manual steps (if you skip setup.py)

```bash
pip install -r requirements.txt
cp .env.example .env        # then edit .env
ollama pull llama3.2        # one-time (needs Ollama installed)
python run.py
```

Everything runs in local/mock mode with no `.env`. Add credentials only for the
integrations you want live (Firebase, Razorpay, WhatsApp) — see `.env.example`.

---

## 2. Firebase (persistence + shared login)

1. Firebase console → Project settings → Service accounts → **Generate new
   private key** → save as `firebase-key.json` in this folder.
2. In `.env` set:
   ```
   FIREBASE_ENABLED=true
   FIREBASE_KEY_PATH=firebase-key.json
   FIREBASE_WEB_API_KEY=<Web API Key from Firebase console>
   ```
3. In the Firebase console, enable **Authentication → Email/Password**.

---

## 3. Staff accounts (works in BOTH apps)

```bash
python seed_staff.py            # create accounts
python seed_staff.py --reset    # reset passwords
```

Creates 1 super-admin, 3 admins, 5 supervisors — provisioned in **both**
Firebase Auth (login) and Firestore (roles). Passwords are written once to
`staff_credentials.txt` (gitignored). Distribute securely, then delete.

The same email + password logs into the Flutter PMS and the Voice-AI dashboard.
See `AUTH.md` for how the bridge works.

---

## 4. Flutter PMS app

```bash
cd ..                    # repo root (where pubspec.yaml lives)
flutter pub get
flutter run -d chrome
```

Point the app at your backend + Firebase project via `--dart-define` (optional —
defaults to the demo project):

```bash
flutter run -d chrome \
  --dart-define=API_BASE_URL=http://localhost:8000 \
  --dart-define=FIREBASE_API_KEY=... \
  --dart-define=FIREBASE_PROJECT_ID=...
```

Log in with a seeded account (e.g. `admin1@karivena.org` + its password from
`staff_credentials.txt`).

---

## 5. Tests

```bash
python test_all.py        # core (27)
python test_phase5.py     # gotram / payments / whatsapp
python test_phase6.py     # roles / rates / invoice / 80G / checkout
python test_phase7.py     # payment automation / dates / consent
python test_phase8.py     # real Karivena data
python test_phase9.py     # staff auth / email / whatsapp flow / receipts
```

---

## Troubleshooting

- **`Router.__init__() got an unexpected keyword argument 'on_startup'`** — a
  Starlette/FastAPI version mismatch. `pip install -r requirements.txt` installs
  the pinned `starlette==0.38.6` that fixes it.
- **Flutter login fails** — ensure `seed_staff.py` was run with Firebase enabled,
  and Email/Password sign-in is turned on in the Firebase console.
- **Ollama errors** — run `ollama serve` in a separate terminal and
  `ollama pull llama3.2`.
