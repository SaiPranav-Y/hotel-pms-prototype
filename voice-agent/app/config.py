"""Configuration for the Telugu voice agent (Phase 1, text-mode)."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

_ROOT = Path(__file__).resolve().parent.parent  # voice-agent/

# --- LLM (Ollama, local) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# llama3.2 is already pulled locally and CPU-efficient. Swap to gemma3:4b etc.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60"))

# --- Database (SQLite, self-contained) ---
DB_PATH = os.getenv("VOICE_AGENT_DB", str(_ROOT / "voice_agent.db"))

# --- Hotel identity ---
HOTEL_NAME = os.getenv("HOTEL_NAME", "Karivena Satram")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# --- Data sources (reuse Karivena room/rate data from the sibling backend) ---
# Points at hotel-voice-booking-demo/app if present, else the repo voice-ai copy.
_CANDIDATES = [
    _ROOT.parent.parent / "hotel-voice-booking-demo" / "app",
    _ROOT.parent / "voice-ai" / "app",
]
ROOM_DATA_PATH = os.getenv("ROOM_DATA_PATH", "")
RATE_CONFIG_PATH = os.getenv("RATE_CONFIG_PATH", "")
if not ROOM_DATA_PATH:
    for c in _CANDIDATES:
        p = c / "room_data.json"
        if p.exists():
            ROOM_DATA_PATH = str(p)
            break
if not RATE_CONFIG_PATH:
    for c in _CANDIDATES:
        p = c / "rate_config.json"
        if p.exists():
            RATE_CONFIG_PATH = str(p)
            break

# --- Feature flags ---
ALLOW_CLOUD_TTS = os.getenv("ALLOW_CLOUD_TTS", "false").lower() == "true"
STORE_TRANSCRIPTS = os.getenv("STORE_TRANSCRIPTS", "false").lower() == "true"
