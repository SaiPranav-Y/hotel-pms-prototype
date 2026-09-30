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

# --- Language ---
# "ask" = let the caller choose English or Telugu at the start (default),
# "te"  = Telugu only, "en" = English only.
LANG = os.getenv("LANG_MODE", "ask")

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

# --- Speech-to-text (Phase 2, faster-whisper, local/offline) ---
# Telugu ASR. On CPU use "small" or "base"; "medium"/"large-v3" are far slower.
STT_MODEL = os.getenv("STT_MODEL", "small")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")          # "cpu" | "cuda"
STT_COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")  # int8 is CPU-friendly
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "te")       # Telugu
STT_BEAM_SIZE = int(os.getenv("STT_BEAM_SIZE", "1"))  # 1 = greedy = fastest

# --- Text-to-speech (Phase 3) ---
# Default engine seam. "edge" is the working Telugu path but needs network +
# ALLOW_CLOUD_TTS=true. "piper"/"mms" are offline seams (need extra deps).
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge")
TTS_VOICE_TE = os.getenv("TTS_VOICE_TE", "te-IN-ShrutiNeural")
TTS_CACHE_DIR = os.getenv("TTS_CACHE_DIR", str(_ROOT / ".tts_cache"))
# Prosody for a more natural voice. edge-tts accepts +/-N% rate and +/-NHz pitch.
# Slightly slower + a touch lower pitch reads warmer and clearer for Telugu.
TTS_RATE = os.getenv("TTS_RATE", "-6%")
TTS_PITCH = os.getenv("TTS_PITCH", "-2Hz")
TTS_VOICE_TE_ALT = os.getenv("TTS_VOICE_TE_ALT", "te-IN-MohanNeural")  # male alt

# --- Local mic/speaker loop (Phase 4) ---
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))  # whisper wants 16k
AUDIO_SILENCE_RMS = float(os.getenv("AUDIO_SILENCE_RMS", "0.01"))  # below = silence
AUDIO_SILENCE_SECS = float(os.getenv("AUDIO_SILENCE_SECS", "1.2"))  # end-of-turn hush
AUDIO_MAX_TURN_SECS = float(os.getenv("AUDIO_MAX_TURN_SECS", "15"))  # hard cap per turn

# --- Live data integration (with hotel-voice-booking-demo) ---
# "sqlite" = self-contained offline DB (default). "live" = book against the
# Karivena knowledge_base data layer (Firestore-synced) from the sibling
# hotel-voice-booking-demo project, so bookings appear in the PMS too.
DATA_SOURCE = os.getenv("DATA_SOURCE", "sqlite").lower()

# Path to the sibling demo project (holds knowledge_base.py, vernacular.py, …).
# Auto-discovers the sibling checkout; override with KARIVENA_DEMO_PATH.
_DEMO_CANDIDATES = [
    _ROOT.parent.parent / "hotel-voice-booking-demo",
    _ROOT.parent / "hotel-voice-booking-demo",
]
KARIVENA_DEMO_PATH = os.getenv("KARIVENA_DEMO_PATH", "")
if not KARIVENA_DEMO_PATH:
    for c in _DEMO_CANDIDATES:
        if (c / "app" / "knowledge_base.py").exists():
            KARIVENA_DEMO_PATH = str(c)
            break

# Default gotram to use when a caller can't supply one (live mode requires a
# gotram in the approved list). Empty = always ask the caller.
DEFAULT_GOTRAM = os.getenv("DEFAULT_GOTRAM", "")

# --- WhatsApp text channel (Telugu, same dialogue as voice) ---
# Server bind for the webhook (run_whatsapp.py).
WHATSAPP_HOST = os.getenv("WHATSAPP_HOST", "0.0.0.0")
WHATSAPP_PORT = int(os.getenv("WHATSAPP_PORT", "8100"))
# Idle conversation timeout (seconds) before a WhatsApp session is dropped.
WA_SESSION_TTL_SECS = int(os.getenv("WA_SESSION_TTL_SECS", "1800"))
# Outbound send provider. With none set, replies are logged (MOCK) — good for
# local testing. Meta Cloud API: set token + phone id. Generic bot: set URL.
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_WEBHOOK_URL = os.getenv("WHATSAPP_WEBHOOK_URL", "")
# Token Meta uses to verify the webhook (GET /webhook hub.verify_token).
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "karivena-verify")
