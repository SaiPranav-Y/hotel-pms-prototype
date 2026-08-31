"""
Kaveri Demo — Start Script
Checks Ollama, starts server, auto-opens the correct browser.
Usage: py start.py   OR   double-click KaveriDemo.exe
"""

import subprocess
import sys
import time
import os
import webbrowser
import threading
import socket

PORT = 8000
URL = f"http://localhost:{PORT}"


def print_banner():
    print()
    print("=" * 60)
    print("  The Grand Horizon Hotel — Kaveri Voice Booking Demo")
    print("  100% Free | No API Keys | Runs Locally")
    print("=" * 60)
    print()


def find_ollama() -> str | None:
    """Find ollama executable."""
    local_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
    if os.path.exists(local_path):
        return local_path
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return "ollama"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def is_ollama_running() -> bool:
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama(ollama_cmd: str) -> bool:
    print("      Starting Ollama server...")
    try:
        kwargs = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        subprocess.Popen([ollama_cmd, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
        for _ in range(20):
            time.sleep(1)
            if is_ollama_running():
                return True
    except Exception as e:
        print(f"      Error: {e}")
    return False


def has_model() -> bool:
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=10)
        models = [m["name"] for m in r.json().get("models", [])]
        return any("llama3.2" in m for m in models)
    except Exception:
        return False


def is_port_free(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def find_chrome_or_edge() -> str | None:
    """Find Chrome or Edge executable path on Windows."""
    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def open_browser_smart():
    """
    Open the correct browser (Chrome/Edge) with flags that ensure mic works on localhost.
    Falls back to default browser if Chrome/Edge not found.
    """
    time.sleep(3)

    browser_path = find_chrome_or_edge()

    if browser_path:
        try:
            # Launch Chrome/Edge with flags:
            # --use-fake-ui-for-media-stream: auto-allow mic (no popup)
            # --autoplay-policy=no-user-gesture-required: allow audio playback
            subprocess.Popen([
                browser_path,
                f"--app={URL}",
                "--use-fake-ui-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"\n  [OK] Opened: {URL}")
            print(f"       Dashboard: {URL}/dashboard")
            return
        except Exception:
            pass

    # Fallback: use default browser
    webbrowser.open(URL)
    print(f"\n  [OK] Browser opened: {URL}")
    print(f"       Dashboard: {URL}/dashboard")


def main():
    print_banner()

    # 1. Check Ollama installed
    print("[1/5] Checking Ollama...")
    ollama_cmd = find_ollama()
    if not ollama_cmd:
        print()
        print("  ERROR: Ollama not installed!")
        print("  Download free: https://ollama.com/download")
        print("  Install it, then run this again.")
        print()
        input("  Press Enter to exit...")
        return
    print("      Found.")

    # 2. Start Ollama if needed
    print("[2/5] Checking Ollama server...")
    if not is_ollama_running():
        if not start_ollama(ollama_cmd):
            print("  ERROR: Could not start Ollama. Run 'ollama serve' manually.")
            input("  Press Enter to exit...")
            return
    print("      Running.")

    # 3. Check model
    print("[3/5] Checking AI model...")
    if not has_model():
        print("      Downloading llama3.2 (2GB, one-time)...")
        subprocess.run([ollama_cmd, "pull", "llama3.2"])
        if not has_model():
            print("  ERROR: Model download failed.")
            input("  Press Enter to exit...")
            return
    print("      Ready.")

    # 4. Check port
    print("[4/5] Checking port 8000...")
    if not is_port_free(PORT):
        print(f"      WARNING: Port {PORT} is already in use!")
        print(f"      Another instance may be running. Open {URL} directly.")
        print(f"      Or kill the process using port {PORT} and try again.")
        print()
        webbrowser.open(URL)
        input("  Press Enter to exit...")
        return
    print("      Available.")

    # 5. Start server + open browser
    print("[5/5] Starting server...")
    print()
    print(f"  Call Kaveri:  {URL}")
    print(f"  Dashboard:   {URL}/dashboard")
    print()
    print("  Browser will open automatically (Chrome or Edge).")
    print()
    print("  TIPS:")
    print("  - Use Chrome or Edge (Firefox doesn't support voice)")
    print("  - Allow microphone when prompted")
    print("  - Wait for 'Listening...' before speaking")
    print("  - Press Ctrl+C to stop the server")
    print()

    # Open browser in background (auto-detects Chrome/Edge)
    threading.Thread(target=open_browser_smart, daemon=True).start()

    # Start uvicorn
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped. Goodbye!")
