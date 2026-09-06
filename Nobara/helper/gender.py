"""
Gender detection via genderize.io, for pairing up "Male + Female" style
outputs (e.g. /couple).

Names on Telegram are very often typed in stylish/decorated Unicode fonts
(math alphanumeric symbols, full-width characters, etc.) that genderize.io
can't recognize as a real name at all, so it would always return an unknown
gender - or, in changed name edge-cases, an outright API error. Names are
normalized with `unidecode` (already a project dependency) down to plain
ASCII before ever being sent, and every failure path just returns
(None, 0.0) instead of raising - callers should always have a sensible
fallback for "gender unknown".
"""

import re
import httpx
from unidecode import unidecode

_TIMEOUT = 8


def _clean_first_name(name: str) -> str:
    """Best-effort: strip emoji/symbols/decorations, transliterate to ASCII,
    and return just the first alphabetic word (genderize.io only wants a
    first name)."""
    if not name:
        return ""
    ascii_name = unidecode(name)
    # Keep letters/spaces only - drops leftover punctuation, digits, etc.
    ascii_name = re.sub(r"[^A-Za-z\s]", " ", ascii_name).strip()
    if not ascii_name:
        return ""
    return ascii_name.split()[0]


async def detect_gender(name: str):
    """
    Returns (gender, probability) where gender is "male", "female", or None
    (unknown / API unavailable / name couldn't be normalized). Never raises.
    """
    first_name = _clean_first_name(name)
    if len(first_name) < 2:
        return None, 0.0

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                "https://api.genderize.io", params={"name": first_name}
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None, 0.0

    gender = data.get("gender")
    probability = data.get("probability") or 0.0
    if gender not in ("male", "female"):
        return None, 0.0
    return gender, probability
