@echo off
echo ============================================================
echo   Hotel Voice Booking Demo - One-Click Setup
echo   100%% Free - No API keys needed!
echo ============================================================
echo.

:: Check Python
echo [1/4] Checking Python...
py --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Install from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       OK!

:: Install Python packages
echo [2/4] Installing Python packages...
py -m pip install -r requirements.txt --quiet 2>nul
echo       OK!

:: Check Ollama
echo [3/4] Checking Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   Ollama is NOT installed yet.
    echo   This is the FREE AI engine that powers the voice assistant.
    echo.
    echo   Download from: https://ollama.com/download
    echo   Install it, then run these commands:
    echo     ollama serve        (start the AI server)
    echo     ollama pull llama3.2  (download the AI model, ~2GB)
    echo.
    echo   After that, run this script again.
    echo ============================================================
    pause
    exit /b 1
)

:: Check if Ollama is serving
curl -s http://localhost:11434/api/version >nul 2>&1
if errorlevel 1 (
    echo       Starting Ollama...
    start /b ollama serve >nul 2>&1
    timeout /t 5 >nul
)

:: Check model
echo [4/4] Checking AI model...
ollama list 2>nul | findstr /i "llama3.2" >nul 2>&1
if errorlevel 1 (
    echo       Downloading llama3.2 model (~2GB, one-time)...
    ollama pull llama3.2
    if errorlevel 1 (
        echo ERROR: Failed to download model.
        pause
        exit /b 1
    )
)
echo       OK!

echo.
echo ============================================================
echo   All set! Starting the demo...
echo.
echo   Open in Chrome/Edge: http://localhost:8000
echo   Dashboard:           http://localhost:8000/dashboard
echo.
echo   Press Ctrl+C to stop.
echo ============================================================
echo.

py run.py
