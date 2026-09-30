# -*- coding: utf-8 -*-
"""
Phase-1 TEXT-MODE demo for the Telugu voice booking agent.

Type Telugu (or code-mixed) input; the agent replies in Telugu. This is the
"fast iteration" mode from the steering file (§10) — no audio, no telephony.

Run:
    python run_text.py                 # asks English or Telugu, then chats
    python run_text.py --no-llm        # deterministic only (no Ollama needed)
    python run_text.py --en            # force English
    python run_text.py --te            # force Telugu
    python run_text.py --lang ask|en|te

Prereqs: `python -m app.db.seed` runs automatically on first launch.
"""

import sys
import io
import logging

# Ensure UTF-8 I/O on Windows terminals. Prefer reconfigure() (Py3.7+), which
# keeps redirected/piped stdin working; only fall back to wrapping the raw
# buffer when reconfigure isn't available.
def _force_utf8(stream):
    try:
        stream.reconfigure(encoding="utf-8")
        return stream
    except Exception:
        try:
            return io.TextIOWrapper(stream.buffer, encoding="utf-8")
        except Exception:
            return stream

sys.stdout = _force_utf8(sys.stdout)
sys.stdin = _force_utf8(sys.stdin)

from app import config
from app.db.seed import seed, all_locations
from app.dialogue.state_machine import DialogueSession

logging.basicConfig(level=logging.WARNING)


def _lang_from_argv() -> str:
    argv = sys.argv
    if "--en" in argv:
        return "en"
    if "--te" in argv:
        return "te"
    if "--lang" in argv:
        i = argv.index("--lang")
        if i + 1 < len(argv) and argv[i + 1] in ("ask", "en", "te"):
            return argv[i + 1]
    return config.LANG  # default (ask)


def main():
    use_llm = "--no-llm" not in sys.argv
    caller_id = "+919876543210"  # simulated caller number for the demo
    lang = _lang_from_argv()

    print("=" * 60)
    print(f"  {config.HOTEL_NAME} — Booking Agent (Text Mode)")
    print("  Type 'exit' / 'q' to quit.")
    print("=" * 60)

    # Seed DB (idempotent) + list locations for slot matching.
    seed(config.DB_PATH)
    locations = all_locations()
    print("Locations:", ", ".join(locations))

    llm = None
    if use_llm:
        try:
            from app.llm.ollama_client import OllamaProvider
            llm = OllamaProvider()
            print(f"Warming up Ollama ({llm.model})…")
            llm.warm_up()
        except Exception as e:
            print(f"[warn] Ollama unavailable ({e}); running deterministic-only.")
            llm = None

    session = DialogueSession(llm=llm, caller_id=caller_id, locations=locations,
                              lang=lang)

    # Agent speaks first (the bilingual language picker if lang == "ask").
    print(f"\nAgent: {session.greeting()}")

    while not session.finished:
        try:
            user = input("You:   ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in ("exit", "q", "quit"):
            break
        if not user:
            continue
        reply = session.handle(user)
        print(f"Agent: {reply}")

    if session.finished:
        print("\n[conversation ended]")
    if llm and hasattr(llm, "close"):
        llm.close()


if __name__ == "__main__":
    main()
