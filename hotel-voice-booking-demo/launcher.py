"""
Hotel Voice Booking Demo — One-Click Launcher
Checks Ollama, starts the server, opens the browser automatically.
This file gets compiled to .exe via PyInstaller.
"""

import subprocess
import sys
import time
import os
import webbrowser
import threading
import httpx

# Paths
OLLAMA_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
PORT = 8000
URL = f"http://localhost:{PORT}"


def print_banner():
    print()
    print("=" * 60)
    print("  The Grand Horizon Hotel — Kaveri Voice Booking Demo")
    print("  100% Free | No API Keys | Runs Locally")
    print("=" * 60)
    print()


def check_ollama_installed() -> bool:
    """Check if Ollama is installed."""
    if os.path.exists(OLLAMA_PATH):
        return True
    # Try system PATH
    try:
        subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_ollama_running() -> bool:
    """Check if Ollama server is responding."""
    try:
        r = httpx.get("http://localhost:11434/api/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama():
    """Start Ollama serve in background."""
    print("[*] Starting Ollama server...")
    cmd = OLLAMA_PATH if os.path.exists(OLLAMA_PATH) else "ollama"
    subprocess.Popen(
        [cmd, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    # Wait for it to come up
    for _ in range(15):
        time.sleep(1)
        if check_ollama_running():
            print("[OK] Ollama server running.")
            return True
    print("[!] Ollama failed to start. Please run 'ollama serve' manually.")
    return False


def check_model() -> bool:
    """Check if llama3.2 model is available."""
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=10)
        models = [m["name"] for m in r.json().get("models", [])]
        return any("llama3.2" in m for m in models)
    except Exception:
        return False


def open_browser_delayed():
    """Open browser after a short delay to let server start."""
    time.sleep(3)
    webbrowser.open(URL)
    print(f"\n[OK] Browser opened: {URL}")
    print(f"     Dashboard: {URL}/dashboard")
    print()
    print("     Press Ctrl+C to stop the server.")
    print()


def main():
    print_banner()

    # 1. Check Ollama
    print("[1/4] Checking Ollama installation...")
    if not check_ollama_installed():
        print()
        print("  ERROR: Ollama is not installed!")
        print("  Download free from: https://ollama.com/download")
        print("  Install it, then run this again.")
        print()
        input("  Press Enter to exit...")
        sys.exit(1)
    print("      Ollama installed.")

    # 2. Start Ollama if not running
    print("[2/4] Checking Ollama server...")
    if not check_ollama_running():
        if not start_ollama():
            input("  Press Enter to exit...")
            sys.exit(1)
    else:
        print("      Ollama already running.")

    # 3. Check model
    print("[3/4] Checking AI model (llama3.2)...")
    if not check_model():
        print("      Model not found. Pulling llama3.2 (2GB, one-time)...")
        cmd = OLLAMA_PATH if os.path.exists(OLLAMA_PATH) else "ollama"
        result = subprocess.run([cmd, "pull", "llama3.2"], capture_output=False)
        if result.returncode != 0:
            print("  ERROR: Failed to pull model. Check internet connection.")
            input("  Press Enter to exit...")
            sys.exit(1)
    print("      Model ready.")

    # 4. Start server + open browser
    print("[4/4] Starting voice booking server...")
    print()
    print(f"  Voice Call:  {URL}")
    print(f"  Dashboard:   {URL}/dashboard")
    print()

    # Open browser in background thread
    threading.Thread(target=open_browser_delayed, daemon=True).start()

    # Start uvicorn (blocks here)
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")
        sys.exit(0)
