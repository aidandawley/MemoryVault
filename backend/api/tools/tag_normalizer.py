# backend/api/tools/tag_normalizer.py
import re
from typing import Dict

# 1) hand-written alias map (you’ll expand this over time)
ALIASES: Dict[str, str] = {
    "dancing": "dance",
    "dancer": "dance",
    "dances": "dance",
    "hiphop": "hip hop",
    "soccer game": "soccer",
    "football game": "football",
    "basketball game": "basketball",
}

_punct_re = re.compile(r"[^a-z0-9\s]")     # keep letters/numbers/spaces
_space_re = re.compile(r"\s+")

def normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("_", " ").replace("-", " ")
    s = _punct_re.sub(" ", s)
    s = _space_re.sub(" ", s).strip()
    return s

def normalize_and_alias(tag: str) -> str:
    t = normalize_text(tag)

    # exact alias hit first
    if t in ALIASES:
        return ALIASES[t]

    # very light singularization fallback (safe-ish)
    # (keeps this step deterministic and cheap)
    if t.endswith("ing") and len(t) > 5:
        # dancing -> danc (too aggressive), so DON'T do this blindly.
        # leave as-is unless explicit alias exists.
        return t

    if t.endswith("s") and len(t) > 3:
        singular = t[:-1]
        if singular in ALIASES:
            return ALIASES[singular]
        # only accept singular if it’s not weird
        return singular

    return t