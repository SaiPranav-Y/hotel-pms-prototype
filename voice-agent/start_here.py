# -*- coding: utf-8 -*-
"""
Karivena Satram — Telugu Booking Agent · One-click launcher.

A friendly, do-everything starter for non-technical users:

  1. checks Python,
  2. installs the Python packages (from requirements.txt),
  3. seeds the local booking database,
  4. checks Ollama (optional — the agent runs without it too),
  5. shows a simple menu to start Text / Voice / WhatsApp, or run the tests.

Run it with:   py start_here.py
(or just double-click start_here.bat on Windows)
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
PY = sys.executable  # the same interpreter that launched us


def _say(msg=""):
    print(msg)


def _hr():
    print("=" * 60)


def check_python():
    _say(f"[1/4] Python {sys.version.split()[0]}  (OK)")
    if sys.version_info < (3, 10):
        _say("  WARNING: Python 3.10+ is recommended. Some features may not work.")


def install_requirements():
    _say("[2/4] Installing required packages (first time may take a minute)...")
    req = ROOT / "requirements.txt"
    if not req.exists():
        _say("  requirements.txt not found — skipping.")
        return
    rc = subprocess.run(
        [PY, "-m", "pip", "install", "-r", str(req), "--quiet"]
    ).returncode
    _say("  Packages ready." if rc == 0 else
         "  Some packages may not have installed — you can still try the menu.")


def seed_db():
    _say("[3/4] Preparing the booking database...")
    try:
        subprocess.run([PY, "-m", "app.db.seed"], check=False)
    except Exception as e:
        _say(f"  Seed skipped: {e}")


def check_ollama():
    _say("[4/4] Checking the local AI (Ollama) — optional...")
    try:
        import httpx
        httpx.get("http://localhost:11434/api/version", timeout=3).raise_for_status()
        _say("  Ollama is running.")
    except Exception:
        _say("  Ollama not detected. That's OK — the agent still works without it")
        _say("  (choose the '--no-llm' style; the menu handles this for you).")
        _say("  To enable smarter intent detection later: https://ollama.com/download")
        _say("  then run:  ollama pull llama3.2")


def _run(cmd):
    _say()
    _hr()
    _say("Starting… (press Ctrl+C to stop and return here)")
    _hr()
    try:
        subprocess.run([PY] + cmd)
    except KeyboardInterrupt:
        pass


def menu():
    while True:
        _say()
        _hr()
        _say("  Karivena Satram — Telugu Booking Agent")
        _say("  Data source: " + os.getenv("DATA_SOURCE", "sqlite")
             + "   (set DATA_SOURCE=live to use the PMS data)")
        _hr()
        _say("  1) Text chat        (type in Telugu)")
        _say("  2) Voice call       (speak in Telugu — needs a mic + internet)")
        _say("  3) WhatsApp server  (webhook for WhatsApp text)")
        _say("  4) Run the tests")
        _say("  5) Quit")
        _hr()
        choice = input("  Choose 1-5: ").strip()

        if choice == "1":
            # Deterministic mode by default so it works even without Ollama.
            _run(["run_text.py", "--no-llm"])
        elif choice == "2":
            os.environ.setdefault("ALLOW_CLOUD_TTS", "true")
            _run(["run_voice.py", "--no-llm"])
        elif choice == "3":
            _run(["run_whatsapp.py"])
        elif choice == "4":
            _run(["-m", "pytest", "-q"])
        elif choice in ("5", "q", "quit", "exit"):
            _say("  Goodbye!")
            return
        else:
            _say("  Please type a number from 1 to 5.")


def main():
    # UTF-8 output so Telugu renders.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    _hr()
    _say("  Welcome! Setting things up (safe to run again anytime)…")
    _hr()
    check_python()
    install_requirements()
    seed_db()
    check_ollama()
    menu()


if __name__ == "__main__":
    main()
