# Getting Started — Karivena Satram Telugu Booking Agent

A simple, friendly guide. No coding needed. If you can install an app and type a
command once, you can run this.

---

## What is this?

A booking assistant for **Karivena Satram** that talks to guests **in Telugu**.
It helps them check rooms, book, and cancel. You can use it three ways:

1. **Text chat** — type in Telugu on your screen. (Easiest to try.)
2. **Voice** — speak into your microphone; it speaks back in Telugu.
3. **WhatsApp** — guests message on WhatsApp and the agent replies in Telugu.

All three ask the same friendly questions — a greeting, then location, dates,
number of guests, room type, name, and (for real bookings) gotram and email.

---

## Step 1 — Install Python (one time)

1. Go to **https://www.python.org/downloads/**
2. Download and run the installer.
3. **Important:** on the first screen, tick **"Add Python to PATH"**, then
   click Install.

## Step 2 — (Optional) Install Ollama for smarter understanding

The agent works fine without this. If you want smarter intent detection:

1. Go to **https://ollama.com/download**, install it.
2. Open a terminal and run: `ollama pull llama3.2`

You can skip this entirely — the app runs in a simple, reliable mode without it.

---

## Step 3 — Start the app (the easy way)

- **Windows:** double-click **`start_here.bat`** in the `voice-agent` folder.
- **Any system:** open a terminal in the `voice-agent` folder and run:
  ```
  py start_here.py
  ```

The first time, it installs what it needs and prepares the booking data. Then
you'll see a simple menu:

```
1) Text chat
2) Voice call
3) WhatsApp server
4) Run the tests
5) Quit
```

Type a number and press Enter. That's it.

---

## How to use each option

### 1) Text chat
Type in Telugu. A full booking looks like this (type one line, press Enter,
read the reply, type the next):

```
బుక్ చేయాలి        (I want to book)
శ్రీశైలం            (which place)
రేపు               (when — tomorrow)
రెండు రోజులు        (how many nights — two)
ఇద్దరు             (how many guests — two)
ఏసీ               (AC or Non-AC)
రవి కుమార్          (your name)
అవును             (yes, confirm)
```

The agent replies in Telugu and gives you a booking number. Type `exit` to stop.

### 2) Voice call
Speak the same answers into your microphone; the agent speaks back in Telugu.
Voice output needs an internet connection (it uses a free Microsoft Telugu
voice). If you don't have a microphone, it quietly switches to typing.

### 3) WhatsApp server
This starts a small web service that answers WhatsApp messages. By default it's
in **safe test mode** (it logs replies instead of sending real WhatsApp
messages), so you can try it without any WhatsApp account. To connect a real
WhatsApp number, see "Going live on WhatsApp" below.

---

## Two data modes: practice vs real

The agent can save bookings in two places. You choose by setting `DATA_SOURCE`.

| Mode | What it does | When to use |
| --- | --- | --- |
| **`sqlite`** (default) | Saves to a local practice database on this computer. Offline, safe to experiment. | Learning, demos, testing |
| **`live`** | Saves into the real **Karivena PMS** data (the same place the front desk sees). Asks for gotram + email, and the gotram must be approved. | Real bookings |

To use real mode, set it before starting:

```
# Windows PowerShell
$env:DATA_SOURCE = "live"
py start_here.py
```

Live mode needs the companion `hotel-voice-booking-demo` project available next
to this one (the app finds it automatically). For bookings to also appear in the
staff app, that project needs Firebase turned on — see `SETUP.md` for the details.

---

## Going live on WhatsApp (optional, for real messages)

By default WhatsApp is in test mode (replies are logged, nothing is sent). To
send real WhatsApp messages you need one of these, set in a `.env` file:

- **Meta WhatsApp Cloud API:** set `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_ID`.
- **Your existing WhatsApp bot:** set `WHATSAPP_WEBHOOK_URL`.

Then point your WhatsApp provider's webhook at this app's `/webhook` address.
For local testing you can expose it with a free tool like **ngrok**
(`ngrok http 8100`). Full steps and all settings are in `.env.example` and
`SETUP.md`.

---

## Common problems (and quick fixes)

| Problem | Fix |
| --- | --- |
| Telugu shows as boxes or `????` | Close the window and start again with `start_here.bat` (it sets the right text mode). |
| `python` opens the Microsoft Store | Use `py` instead of `python` (e.g. `py start_here.py`). |
| Voice has no sound | You need internet, and the app must be in voice mode; it uses a free online Telugu voice. |
| "Ollama not detected" | That's fine — the app still works. Install Ollama later only if you want smarter understanding. |
| Live mode says it fell back to practice mode | The companion PMS project wasn't found. Keep `hotel-voice-booking-demo` next to this folder, or see `SETUP.md`. |
| Gotram not accepted (live mode) | Only approved community gotrams can book — this is intentional. |

---

## Want more detail?

- **`SETUP.md`** — full setup, live mode, Firebase, all settings.
- **`docs/INTEGRATION.md`** — how this connects to the Karivena PMS.
- **`README.md`** — the technical overview.

Om Namah Shivaya 🕉️
