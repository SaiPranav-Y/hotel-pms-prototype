"""
Build script — creates a standalone .exe launcher for the demo.
Run: py build_exe.py

This creates: dist/KaveriDemo.exe
Double-click it to start the server + open browser automatically.
"""

import subprocess
import sys


def main():
    print("Building KaveriDemo.exe...")
    print()

    # Install PyInstaller if not present
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "--quiet"])

    # Build the exe
    # --onefile: single .exe
    # --name: output name
    # --add-data: include the app folder
    # --hidden-import: ensure all needed modules are bundled
    # --console: keep console window for logs
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "KaveriDemo",
        "--console",
        "--add-data", "app;app",
        "--add-data", "recordings;recordings",
        "--add-data", ".env;.",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "app.main",
        "--hidden-import", "app.config",
        "--hidden-import", "app.ai_engine",
        "--hidden-import", "app.call_handler",
        "--hidden-import", "app.hotel_data",
        "--hidden-import", "app.local_tts",
        "--hidden-import", "app.local_stt",
        "--hidden-import", "app.recorder",
        "--hidden-import", "app.pages",
        "--hidden-import", "app.pages.call_page",
        "--hidden-import", "app.pages.dashboard_page",
        "--hidden-import", "edge_tts",
        "--hidden-import", "httpx",
        "--hidden-import", "ollama",
        "launcher.py",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print()
        print("=" * 50)
        print("  BUILD SUCCESSFUL!")
        print()
        print("  Output: dist/KaveriDemo.exe")
        print()
        print("  To use:")
        print("  1. Copy dist/KaveriDemo.exe anywhere")
        print("  2. Double-click it")
        print("  3. Browser opens automatically")
        print("=" * 50)
    else:
        print()
        print("Build failed. Check errors above.")


if __name__ == "__main__":
    main()
