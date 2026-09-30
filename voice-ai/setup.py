"""
One-command setup for the Karivena Satram Voice-AI backend.

    python setup.py

Does the following:
  1. Checks Python version
  2. Installs Python dependencies (requirements.txt)
  3. Creates .env from .env.example if missing
  4. Checks Ollama + the required model
  5. Prints next steps

Cross-platform (Windows / macOS / Linux). Safe to re-run.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)


def step(n, msg):
    print(f"\n[{n}] {msg}")


def run(cmd):
    return subprocess.run(cmd, shell=isinstance(cmd, str)).returncode


def main():
    print("=" * 60)
    print("  Karivena Satram — Voice AI Setup")
    print("=" * 60)

    # 1. Python version
    step(1, "Checking Python version...")
    if sys.version_info < (3, 9):
        print(f"  ERROR: Python 3.9+ required (found {sys.version.split()[0]})")
        sys.exit(1)
    print(f"  OK — Python {sys.version.split()[0]}")

    # 2. Dependencies
    step(2, "Installing Python dependencies (requirements.txt)...")
    rc = run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"])
    if rc != 0:
        print("  WARNING: pip install returned non-zero. Check the output above.")
    else:
        print("  OK — dependencies installed")

    # 3. .env
    step(3, "Setting up .env ...")
    if os.path.exists(".env"):
        print("  .env already exists — leaving it as is")
    elif os.path.exists(".env.example"):
        shutil.copyfile(".env.example", ".env")
        print("  Created .env from .env.example — edit it to add credentials")
    else:
        print("  No .env.example found — skipping")

    # 4. Ollama
    step(4, "Checking Ollama (local AI)...")
    ollama = shutil.which("ollama")
    if not ollama:
        print("  Ollama NOT found. Install from https://ollama.com/download")
        print("  Then run:  ollama pull llama3.2")
    else:
        print(f"  OK — Ollama found at {ollama}")
        try:
            out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
            if "llama3.2" in (out.stdout or ""):
                print("  OK — llama3.2 model present")
            else:
                print("  Model llama3.2 not found. Run:  ollama pull llama3.2")
        except Exception:
            print("  Could not list Ollama models (is 'ollama serve' running?)")

    # 5. Next steps
    step(5, "Setup complete. Next steps:")
    print("""
  Run the backend:      python run.py
    -> Voice/call UI:   http://localhost:8000
    -> Dashboard:       http://localhost:8000/dashboard
    -> API docs:        http://localhost:8000/docs

  Seed staff accounts (needs Firebase configured in .env):
                        python seed_staff.py

  Run the tests:        python test_all.py

  Auth + Flutter setup: see AUTH.md and SETUP.md
""")


if __name__ == "__main__":
    main()
