# backend/api/tools/tag_normalizer.py
from __future__ import annotations

import re
from typing import Dict

# 1) hand-written alias map (expand over time)
ALIASES: Dict[str, str] = {
    "dancing": "dance",
    "dancer": "dance",
    "dances": "dance",
    "hiphop": "hip hop",
    "soccer game": "soccer",
    "football game": "football",
    "basketball game": "basketball",

    # common “plural-but-should-stay” words
    "sunglasses": "sunglasses",
    "glasses": "glasses",
    "lights": "lights",

    # demo-friendly mappings
    "formal dress": "dress",
    "formaldress": "dress",
}

# --- Wedding / Ceremony ---
ALIASES.update({
    # core wedding
    "wedding day": "wedding",
    "wedding vibes": "wedding",
    "wedding party": "wedding",
    "wedding guests": "wedding",
    "wedding celebration": "wedding",
    "marriage": "wedding",
    "married": "wedding",
    "just married": "wedding",
    "newlyweds": "wedding",
    "newly weds": "wedding",

    # bride / groom
    "the bride": "bride",
    "bridal": "bride",
    "bride to be": "bride",
    "bride-to-be": "bride",
    "the groom": "groom",
    "groomsman": "groomsmen",
    "best man": "groomsmen",
    "maid of honor": "bridesmaids",
    "bridesmaid": "bridesmaids",

    # ceremony
    "wedding ceremony": "ceremony",
    "the ceremony": "ceremony",
    "wedding vows": "vows",
    "exchanging vows": "vows",
    "ring exchange": "rings",
    "wedding rings": "rings",
    "ring": "rings",
    "first kiss": "kiss",
    "wedding kiss": "kiss",
    "altar": "ceremony",
    "aisle": "ceremony",
    "walking down the aisle": "ceremony",
    "processional": "ceremony",
    "recessional": "ceremony",

    # reception
    "wedding reception": "reception",
    "the reception": "reception",
    "reception party": "reception",
    "banquet": "reception",
    "wedding banquet": "reception",

    # speeches / toasts
    "toast": "toasts",
    "wedding toast": "toasts",
    "cheers": "toasts",
    "speech": "speeches",
    "wedding speech": "speeches",
    "mic speech": "speeches",

    # cake
    "wedding cake": "cake",
    "cake cutting": "cake",
    "cutting the cake": "cake",
    "dessert table": "dessert",

    # bouquet / flowers
    "bridal bouquet": "bouquet",
    "bouquet toss": "bouquet",
    "flower bouquet": "bouquet",
    "floral": "flowers",

    # outfits
    "wedding dress": "dress",
    "bridal dress": "dress",
    "gown": "dress",
    "formal wear": "formalwear",
    "tux": "tuxedo",

    # photos
    "wedding photos": "photos",
    "wedding photography": "photos",
    "photo session": "photos",
    "group photo": "photos",
    "family photo": "photos",
})

# --- Dancing / Music / DJ ---
ALIASES.update({
    "dance floor": "dance",
    "party dancing": "dance",
    "energetic dance": "dance",
    "energetic dancing": "dance",
    "dance party": "dance",
    "father daughter dance": "first dance",
    "mother son dance": "first dance",

    "wedding dj": "dj",
    "live music": "music",
    "live band": "band",
    "singer": "music",
    "song": "music",
    "songs": "music",
    "playlist": "music",
})

# --- Party / Superbad-style vibes ---
ALIASES.update({
    # general party
    "party vibes": "party",
    "party vibe": "party",
    "party time": "party",
    "house party": "party",
    "houseparty": "party",
    "college party": "party",
    "collegeparty": "party",
    "teen party": "party",
    "big party": "party",
    "wild party": "party",
    "crazy party": "party",
    "after party": "afterparty",

    # location-ish party tags
    "kitchen party": "party",
    "living room party": "party",
    "bedroom party": "party",
    "hotel room party": "party",
    "hotelroomparty": "party",
    "backyard party": "party",
    "pool party": "pool party",
    "poolparty": "pool party",

    # crowd / people
    "best friends": "friends",
    "friend group": "friends",
    "friendgroup": "friends",
    "group of friends": "friends",
    "crowd reaction": "crowd",
    "crowdreaction": "crowd",
    "kids": "children",

    # energy / chaos
    "hype": "energetic",
    "hyped": "energetic",
    "hype moment": "energetic",
    "chaotic": "chaos",
    "rowdy": "chaos",
    "loud": "chaos",
    "comedy": "funny",
    "laughing": "funny",

    # drinking / superbad-ish
    "drink": "drinks",
    "drinking": "drinks",
    "beer": "drinks",
    "beers": "drinks",
    "shot": "drinks",
    "shots": "drinks",
    "alcohol": "drinks",
    "red cup": "drinks",
    "red cups": "drinks",
    "solo cup": "drinks",
    "celebratory drink": "drinks",
    "celebratorydrink": "drinks",

    # stunts / moments
    "dramatic fall": "fall",
    "dramaticfall": "fall",
    "dancing fail": "fall",
    "party fail": "fall",

    # lighting / vibe
    "dim lighting": "lighting",
    "dimlighting": "lighting",
    "party lights": "lighting",
    "light show": "lighting",
    "neon": "lighting",
    "strobe": "lighting",
})

# --- Extra common “cleanup” variants ---
ALIASES.update({
    "night club": "nightclub",
    "dance club": "nightclub",

    # keep these stable (avoid singularizer messing them up)
    "sunglasses": "sunglasses",
    "glasses": "glasses",
    "lights": "lights",
    "dress": "dress",
})

# Insert spaces for CamelCase / PascalCase: "HotelRoomParty" -> "Hotel Room Party"
_camel_re = re.compile(r"([a-z0-9])([A-Z])")

_punct_re = re.compile(r"[^a-z0-9\s]")  # keep letters/numbers/spaces
_space_re = re.compile(r"\s+")

# Words we never want to singularize (prevents "sunglasse", "glasse", etc.)
NO_SINGULARIZE = {"sunglasses", "glasses", "dress", "lights"}


def normalize_text(s: str) -> str:
    s = (s or "").strip()

    # Split CamelCase BEFORE lowercasing
    s = _camel_re.sub(r"\1 \2", s)

    s = s.lower()
    s = s.replace("_", " ").replace("-", " ")
    s = _punct_re.sub(" ", s)
    s = _space_re.sub(" ", s).strip()
    return s


def _safe_singularize_word(w: str) -> str:
    """
    Conservative singularization for 1 token.
    Avoids nasty cases like sunglasses->sunglasse.
    """
    if not w or len(w) <= 3:
        return w
    if w in NO_SINGULARIZE:
        return w

    # parties -> party
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"

    # boxes -> box, watches -> watch, dresses -> dress
    if w.endswith("es") and len(w) > 4:
        if w.endswith(("sses", "shes", "ches", "xes", "zes")):
            return w[:-2]

    # generic trailing 's' (but avoid ss/us/is)
    if w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]

    return w


def normalize_and_alias(tag: str) -> str:
    t = normalize_text(tag)

    # exact alias hit first
    if t in ALIASES:
        return ALIASES[t]

    # only singularize if it's ONE word
    if " " not in t:
        t2 = _safe_singularize_word(t)
        if t2 in ALIASES:
            return ALIASES[t2]
        return t2

    return t