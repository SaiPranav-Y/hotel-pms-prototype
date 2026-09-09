"""
Start the Hotel Voice Booking Demo.
Usage: py run.py

Prerequisites:
1. Ollama installed and running (https://ollama.com/download)
2. Model pulled: ollama pull llama3.2
3. Python packages installed: py -m pip install -r requirements.txt
"""

import sys
import subprocess
import httpx


def check_ollama():
    """Verify Ollama is running and has the required model."""
    print("\n[Checking] Ollama connection...")
    try:
        r = httpx.get("http://localhost:11434/api/version", timeout=5)
        r.raise_for_status()
        print(f"  Ollama running (version: {r.json().get('version', 'unknown')})")
    except (httpx.ConnectError, httpx.TimeoutException):
        print("\n  ERROR: Cannot connect to Ollama!")
        print("  ")
        print("  To fix:")
        print("  1. Download Ollama from: https://ollama.com/download")
        print("  2. Install it (just run the installer)")
        print("  3. Open a terminal and run: ollama serve")
        print("  4. In another terminal run: ollama pull llama3.2")
        print("  5. Then run this script again: py run.py")
        print()
        sys.exit(1)

    # Check if model is available
    print("[Checking] AI model (llama3.2)...")
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=10)
        models = [m["name"] for m in r.json().get("models", [])]
        has_model = any("llama3.2" in m for m in models)
        if has_model:
            print("  Model ready!")
        else:
            print(f"  Available models: {models}")
            print("  llama3.2 not found. Pulling now (2GB download, one-time)...")
            print("  Run in another terminal: ollama pull llama3.2")
            print("  Then restart this script.")
            sys.exit(1)
    except Exception as e:
        print(f"  Warning: Could not verify model: {e}")


def main():
    print("=" * 60)
    print("  The Grand Horizon Hotel — Voice Booking Demo")
    print("  100% Free | No API Keys | Runs Locally")
    print("=" * 60)

    check_ollama()

    print()
    print("[Starting] Server...")
    print()
    print("  Voice Call:  http://localhost:8000")
    print("  Dashboard:   http://localhost:8000/dashboard")
    print("  API Docs:    http://localhost:8000/docs")
    print()
    print("  How to use:")
    print("  1. Open http://localhost:8000 in Chrome/Edge")
    print("  2. Click the green phone button")
    print("  3. Allow microphone access when prompted")
    print("  4. Say: 'I'd like to book a room for this weekend'")
    print("  5. Watch the dashboard update with your booking!")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 60)
    print()

    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
