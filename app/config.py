"""
Configuration — all local, no paid APIs needed.
Uses Ollama (local LLM) + Whisper (local STT) + Piper (local TTS).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Ollama (local LLM - free)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Whisper (local STT - free)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")  # tiny, base, small, medium

# Piper TTS (local - free)
PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-amy-medium")

# Audio config
SAMPLE_RATE = 16000
