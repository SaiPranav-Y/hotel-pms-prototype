"""
Custom Pronunciation Engine — ensures TTS says temple/domain names correctly.
Uses SSML-like substitution rules applied before text goes to Edge-TTS.
Maps difficult words to phonetically-spelled equivalents that TTS handles well.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Pronunciation rules: original → phonetic spelling for TTS
# Format: (pattern, replacement) — applied in order

PRONUNCIATION_RULES = [
    # Temple locations — spelled phonetically for Indian English TTS
    (r'\bSrisailam\b', 'Shree-Shy-Lum'),
    (r'\bNaimisaranyam\b', 'Nai-Misha-Ranyum'),
    (r'\bVruddasramam\b', 'Vruddha-Ashramam'),
    (r'\bBrundavanam\b', 'Brunda-Vanam'),
    (r'\bArunachalam\b', 'Aruna-Chalam'),
    (r'\bRameswaram\b', 'Ramesh-Waram'),
    (r'\bMahanandi\b', 'Maha-Nandi'),
    (r'\bTirupathi\b', 'Thiru-Pathi'),
    (r'\bShiridi\b', 'Shir-Dee'),
    (r'\bKasi\b', 'Kaa-Shi'),

    # Building names from Excel
    (r'\bPandey Haveli\b', 'Pandey Ha-Veli'),
    (r'\bKarivena\b', 'Kari-Vena'),
    (r'\bNityannadana\b', 'Nitya-Anna-Dana'),
    (r'\bSatram\b', 'Sut-Ram'),
    (r'\bBharath[ei]eya\b', 'Bhara-Theeya'),
    (r'\bBrahmana\b', 'Brah-Mana'),

    # Room/domain terms
    (r'\bINR\b', 'rupees'),
    (r'\bRs\.?\b', 'rupees'),
    (r'\b₹\b', 'rupees'),
    (r'\bA/?C\b', 'A C'),
    (r'\bNon[- ]?A/?C\b', 'Non A C'),
    (r'\bBK-([A-Z0-9]+)\b', r'Booking I D \1'),

    # Numbers with context
    (r'(\d+)\s*rupees', r'\1 rupees'),
    (r'(\d+)/night', r'\1 rupees per night'),
]

# Words that should NOT be substituted (protect list)
PROTECTED_WORDS = {"sir", "ma'am", "namaste", "thank", "please", "room", "booking"}


def apply_pronunciation(text: str) -> str:
    """
    Apply pronunciation rules to text before sending to TTS.
    Makes difficult names pronounceable by Edge-TTS.
    """
    result = text

    for pattern, replacement in PRONUNCIATION_RULES:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result


def add_pronunciation_rule(pattern: str, replacement: str) -> bool:
    """Add a custom pronunciation rule at runtime."""
    try:
        re.compile(pattern)  # Validate regex
        PRONUNCIATION_RULES.append((pattern, replacement))
        logger.info(f"Added pronunciation rule: {pattern} → {replacement}")
        return True
    except re.error:
        return False


def get_pronunciation_rules() -> list[dict]:
    """Get all active pronunciation rules."""
    return [{"pattern": p, "replacement": r} for p, r in PRONUNCIATION_RULES]


def get_rules_count() -> int:
    return len(PRONUNCIATION_RULES)
