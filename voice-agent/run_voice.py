# -*- coding: utf-8 -*-
"""
Phase-4 LOCAL VOICE demo for the Telugu voice booking agent.

Talk to the agent through your mic and speaker. Pipeline per turn:

    [mic] record_until_silence → STT (faster-whisper, te) → DialogueSession
          → Telugu template reply → TTS (edge-tts, gated) → [speaker] play

Everything is local + free except edge-tts (needs network; enable with
ALLOW_CLOUD_TTS=true). If STT or TTS isn't usable, the loop degrades gracefully:
  * no STT  → falls back to typed input,
  * no TTS  → prints the Telugu reply instead of speaking it.

Run:
    set ALLOW_CLOUD_TTS=true    &  py run_voice.py
    py run_voice.py --no-llm    # deterministic intent, no Ollama
    py run_voice.py --text      # force text input (skip mic)

The core dialogue is identical to run_text.py — only the I/O changes.
"""

import io
import sys
import logging
import time

try:
    sys.stdout = sys.stdout
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

from app import config
from app.db.seed import seed, all_locations
from app.dialogue import templates_te as T
from app.dialogue.state_machine import DialogueSession

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("run_voice")

SLOW_TURN_SECS = 2.5  # if a turn takes longer, we play a filler first next time


def _build_llm(use_llm: bool):
    if not use_llm:
        return None
    try:
        from app.llm.ollama_client import OllamaProvider
        llm = OllamaProvider()
        print(f"Warming up Ollama ({llm.model})…")
        llm.warm_up()
        return llm
    except Exception as e:
        print(f"[warn] Ollama unavailable ({e}); deterministic-only.")
        return None


def _build_stt(force_text: bool):
    if force_text:
        return None
    from app.audio import mic
    if not mic.audio_available():
        print("[warn] No microphone/input device; using typed input.")
        return None
    from app.audio.stt import get_stt
    stt = get_stt("faster-whisper")
    if not stt.available:
        print("[warn] STT backend unavailable; using typed input.")
        return None
    print(f"Loading STT model '{config.STT_MODEL}' (first run downloads it)…")
    stt.warm_up()
    return stt


def _build_tts():
    from app.audio.tts import get_tts
    tts = get_tts()
    if not tts.available:
        if config.TTS_ENGINE == "edge" and not config.ALLOW_CLOUD_TTS:
            print("[info] TTS off (set ALLOW_CLOUD_TTS=true for spoken Telugu). "
                  "Replies will be printed.")
        else:
            print("[info] No TTS backend; replies will be printed.")
        return None
    try:
        tts.warm_up()
    except Exception:
        pass
    return tts


def _speak(tts, mic_mod, text: str):
    """Speak via TTS if available, else print. Always prints for visibility."""
    print(f"Agent: {text}")
    if not tts:
        return
    try:
        path = tts.synthesize(text)
        if path and mic_mod:
            mic_mod.play(path)
    except Exception as e:
        log.warning(f"speak failed: {e}")


def _listen(stt, mic_mod) -> str | None:
    """Record + transcribe one turn; None means 'fall back to typing'."""
    if not stt or not mic_mod:
        return None
    try:
        print("[listening… speak now]")
        audio = mic_mod.record_until_silence()
        if audio.size == 0:
            return ""
        text = stt.transcribe(audio, config.AUDIO_SAMPLE_RATE)
        print(f"You (heard): {text}")
        return text
    except mic_mod.AudioUnavailable as e:
        print(f"[warn] mic error ({e}); switch to typing.")
        return None


def main():
    argv = sys.argv[1:]
    use_llm = "--no-llm" not in argv
    force_text = "--text" in argv

    print("=" * 60)
    print(f"  {config.HOTEL_NAME} — Telugu Voice Agent (Local Voice)")
    print("  Speak in Telugu. Say/type 'exit' to quit.")
    print("=" * 60)

    seed(config.DB_PATH)
    locations = all_locations()
    print("Locations:", ", ".join(locations))

    from app.audio import mic as mic_mod
    llm = _build_llm(use_llm)
    stt = _build_stt(force_text)
    tts = _build_tts()

    session = DialogueSession(llm=llm, caller_id="+919876543210", locations=locations)
    _speak(tts, mic_mod, session.greeting())

    while not session.finished:
        heard = _listen(stt, mic_mod)
        if heard is None:  # no STT/mic → type instead
            try:
                heard = input("You:   ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
        if heard.lower() in ("exit", "q", "quit"):
            break
        if not heard:
            continue

        t0 = time.time()
        reply = session.handle(heard)
        took = time.time() - t0
        if took > SLOW_TURN_SECS:
            log.info(f"slow turn: {took:.1f}s")
        _speak(tts, mic_mod, reply)

    if session.finished:
        print("\n[conversation ended]")
    if llm and hasattr(llm, "close"):
        llm.close()


if __name__ == "__main__":
    main()
