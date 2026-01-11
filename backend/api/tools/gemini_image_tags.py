import os
import json
from typing import List

from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai


# ---------------------------
# Lazy Gemini model loader
# ---------------------------

_model = None


def _get_model():
    """
    Lazily initialize Gemini so uvicorn reload does not crash
    if env vars are not loaded at import time.
    """
    global _model

    if _model is not None:
        return _model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel("gemini-2.0-flash-lite")
    return _model


# ---------------------------
# Public API
# ---------------------------

def get_tags_for_image_file(image_path: str) -> List[str]:
    """
    Given a local image file path, returns a list of simple visual tags.
    """

    # Read image bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    prompt = """
You are an image tagging system.

Return 5 to 8 visual tags describing the image.

Rules:
- Use only lowercase words
- Use simple nouns or short noun phrases (1–2 words max)
- No full sentences
- No punctuation
- No hashtags
- No emojis

Return the result as a JSON array of strings only.
"""

    model = _get_model()

    response = model.generate_content(
        [
            prompt,
            {
                "mime_type": "image/jpeg",
                "data": image_bytes,
            },
        ],
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 200,
        },
    )

    if not response.text:
        return []

    # Gemini sometimes wraps JSON in markdown
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        tags = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: line-based parsing
        tags = [
            t.strip().lower()
            for t in text.splitlines()
            if t.strip()
        ]

    # Final cleanup
    clean_tags = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        t = tag.lower().strip()
        if t and t not in clean_tags:
            clean_tags.append(t)

    return clean_tags