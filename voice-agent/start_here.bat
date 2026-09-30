@echo off
REM ============================================================
REM   Karivena Satram - Telugu Booking Agent
REM   Double-click this file to set up and start the app.
REM ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

REM Prefer the Windows Python launcher 'py'; fall back to 'python'.
where py >nul 2>&1
if %errorlevel%==0 (
    py start_here.py
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        python start_here.py
    ) else (
        echo.
        echo Python was not found.
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        echo During install, tick "Add Python to PATH".
        echo.
    )
)

echo.
pause
