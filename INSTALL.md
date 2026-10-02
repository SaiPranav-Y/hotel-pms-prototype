# Getting Started — Karivena Satram PMS

This guide walks you through setting up the project from scratch. No experience required — just follow each step in order.

---

## What You Are Setting Up

The project has three parts that work together:

| Part | What it is |
|---|---|
| **The Dashboard** | The main screen staff use to manage bookings (runs in your browser) |
| **The Backend** | The engine that handles AI, payments, and data (runs silently in the background) |
| **The Phone Gateway** | Lets guests book via a phone call (optional, needs a Twilio account) |

You can run just the Dashboard + Backend for day-to-day use. The Phone Gateway is only needed if you want live phone-call booking.

---

## Part 1 — Install the Required Software

Do these once. Skip any you already have.

### 1. Flutter (for the Dashboard)

1. Go to https://docs.flutter.dev/get-started/install/windows
2. Download the Flutter SDK and follow the installation steps
3. Open a new terminal and run:
   ```
   flutter doctor
   ```
   Fix any issues it points out (usually just accepting Android licenses or installing VS Build Tools)

### 2. Python (for the Backend)

1. Go to https://www.python.org/downloads/
2. Download Python **3.9 or newer**
3. During installation, **tick the box that says "Add Python to PATH"** — this is important

### 3. Node.js (for the Phone Gateway — skip if not using phone calls)

1. Go to https://nodejs.org/
2. Download the **LTS** version and install it

### 4. Ollama (the AI brain — runs locally on your computer)

1. Go to https://ollama.com/download
2. Download and install for Windows
3. After installing, open a terminal and run:
   ```
   ollama pull llama3.2
   ```
   This downloads the AI model (about 2GB, one-time only). It will take a few minutes.

---

## Part 2 — Get the Firebase Key

Firebase is the cloud database this project uses. You need a key file to connect to it.

1. Ask the project owner to send you the `firebase-key.json` file
2. Place that file inside the `voice-ai/` folder:
   ```
   hotel-pms-prototype/
   └── voice-ai/
       └── firebase-key.json   ← put it here
   ```

> If you don't have this file yet, the backend will still run — it just won't save data to the real database.

---

## Part 3 — Set Up the Backend

1. Open a terminal and go into the `voice-ai` folder:
   ```
   cd "voice-ai"
   ```

2. Run the automatic setup script:
   ```
   python setup.py
   ```
   This installs all the packages the backend needs and creates a settings file for you.

3. Open the settings file it created (called `.env`) in any text editor, and fill in these lines:
   ```
   FIREBASE_ENABLED=true
   FIREBASE_KEY_PATH=firebase-key.json
   FIREBASE_WEB_API_KEY=<paste the Web API Key here>
   ```
   The Web API Key comes from the Firebase console → Project Settings → General → Web API Key. Ask the project owner if you don't have it.

4. Create the staff accounts (only needs to be done once):
   ```
   python seed_staff.py
   ```
   This creates all the staff logins. After it finishes, a file called `staff_credentials.txt` will appear in the same folder — it contains all the usernames and passwords. Keep it safe and don't share it publicly.

---

## Part 4 — Set Up the Dashboard

1. Open a terminal and go to the project root (the main folder that contains `pubspec.yaml`):
   ```
   cd "hotel-pms-prototype"
   ```

2. Run:
   ```
   flutter pub get
   ```
   This downloads all the packages the dashboard needs.

---

## Running the Project

Every time you want to use the system, you need to start two things: the Backend and the Dashboard. Open two separate terminal windows.

### Terminal 1 — Start the Backend

```
cd "voice-ai"
python run.py
```

You should see something like:
```
Starting Karivena Satram on 0.0.0.0:8000
Dashboard: http://localhost:8000
```

Leave this terminal open and running.

### Terminal 2 — Start the Dashboard

```
cd "hotel-pms-prototype"
flutter run -d chrome
```

This will open the dashboard in your browser after a moment. Log in with one of the accounts from `staff_credentials.txt`.

---

## Running the Phone Gateway (Optional)

Only do this if you want guests to be able to book via phone call. This also requires a Twilio account and ngrok.

1. Open a third terminal and go to the gateway folder:
   ```
   cd "voice-gateway"
   ```

2. Install its packages (first time only):
   ```
   npm install
   ```

3. Copy the settings file:
   ```
   copy .env.example .env
   ```

4. Open the new `.env` file and fill in your Twilio details (Account SID, Auth Token, and your Twilio phone number). These come from your Twilio account dashboard at https://console.twilio.com

5. Start it:
   ```
   npm start
   ```

6. In a fourth terminal, run ngrok to make it reachable from the internet:
   ```
   ngrok http 3000
   ```
   Copy the `https://` URL ngrok gives you, paste it into `.env` as `PUBLIC_URL`, then restart with `npm start` again.

7. In your Twilio console, set your phone number's incoming call webhook to:
   ```
   https://<your-ngrok-url>/voice/incoming
   ```

---

## What to Open Each Day

| What | Where |
|---|---|
| Staff Dashboard | http://localhost:8000/dashboard |
| Voice / Call UI | http://localhost:8000 |
| API Reference | http://localhost:8000/docs |

The Flutter dashboard also opens in your browser via `flutter run -d chrome` — both the Flutter app and the web dashboard show booking data from the same database.

---

## Troubleshooting

### "flutter: command not found"
Flutter was not added to your system's PATH. Redo the Flutter installation and make sure to follow the step that adds it to PATH, then close and reopen your terminal.

### "python: command not found"
Python was not added to PATH. Uninstall and reinstall Python, making sure to tick "Add Python to PATH" during setup.

### Dashboard opens but shows no data
The backend is probably not running. Go to Terminal 1 and check if `python run.py` is still active. If it stopped, run it again.

### Login fails on the dashboard
Make sure `seed_staff.py` was run at least once (Part 3, Step 4). Also confirm that Firebase Email/Password sign-in is enabled in the Firebase console (Authentication → Sign-in methods → Email/Password → Enable).

### "Ollama connection error" in the backend
Ollama is not running. Open a new terminal and run:
```
ollama serve
```
Leave it open, then restart the backend.

### `seed_staff.py` shows `firebase_auth=NO (Firebase not active)`
This means either the `firebase-admin` package is not installed, `firebase-key.json` is missing, or `FIREBASE_ENABLED` is not set to `true`. Fix all three:
```
pip install firebase-admin
```
Then confirm `firebase-key.json` is inside `voice-ai/` and your `.env` has `FIREBASE_ENABLED=true`. Then re-run `python seed_staff.py --reset`.

### Backend crashes with a Starlette/FastAPI error
Run this to fix it:
```
pip install -r requirements.txt
```
Then restart with `python run.py`.

### Bookings are not saving to the database
Check that `firebase-key.json` is inside the `voice-ai/` folder, and that `FIREBASE_ENABLED=true` is set in the `.env` file.

### Phone calls are not connecting (gateway)
Check that ngrok is running and the `PUBLIC_URL` in `voice-gateway/.env` matches the current ngrok URL exactly. ngrok free-tier URLs change every time you restart it, so update the `.env` and your Twilio webhook URL whenever that happens.

### Port 8000 is already in use
Another program is using that port. Either stop it, or change the port in `voice-ai/.env`:
```
PORT=8001
```
Then restart the backend. Remember to open `http://localhost:8001` instead.

---

## Shutting Down

To stop everything cleanly, go to each terminal window and press `Ctrl + C`.

---

## Need Help?

- Check the full developer notes in `README.md`
- For voice/AI platform details, see `voice-ai/DOCUMENTATION.md`
- For security and advanced configuration, see `HARDENING.md`
