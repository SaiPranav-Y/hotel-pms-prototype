# -*- coding: utf-8 -*-
"""
Language-agnostic phrases shown before the caller has picked a language.

The picker is bilingual on purpose (English + Telugu) so either kind of caller
understands it. It's used by the ASK_LANGUAGE state in the dialogue.
"""

# Bilingual greeting + language choice, shown first.
LANGUAGE_PROMPT = (
    "Namaste! / నమస్కారం!\n"
    "For English, press 1 or type English.\n"
    "తెలుగు కోసం, 2 నొక్కండి లేదా 'తెలుగు' అని టైప్ చేయండి."
)

# If the choice wasn't understood, re-ask (still bilingual).
LANGUAGE_RETRY = (
    "Please reply 1 for English or 2 for Telugu.\n"
    "దయచేసి English కోసం 1, తెలుగు కోసం 2 అని చెప్పండి."
)


def detect_language_choice(text: str) -> str | None:
    """
    Map a caller's reply to 'en' or 'te'. Returns None if unclear.
    Accepts: 1 / 2, english / telugu (any case), and Telugu words ఇంగ్లీష్/తెలుగు.
    """
    t = (text or "").strip().lower()
    if not t:
        return None
    # Numeric choice.
    if "1" in t and "2" not in t:
        return "en"
    if "2" in t and "1" not in t:
        return "te"
    # Word choice.
    if "eng" in t or "english" in t or "ఇంగ్లీష్" in t or "ఇంగ్లిష్" in t:
        return "en"
    if "telugu" in t or "telgu" in t or "తెలుగు" in t:
        return "te"
    return None
