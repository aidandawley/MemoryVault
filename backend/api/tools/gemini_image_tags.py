import json
import logging
import mimetypes
import os
from typing import List

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3.5-flash-lite"


# ---------------------------
# Lazy Gemini client loader
# ---------------------------

_client = None


def _get_client() -> genai.Client:
    """
    Lazily initialize Gemini so uvicorn reload does not crash
    if env vars are not loaded at import time.
    """
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    _client = genai.Client(api_key=api_key)
    return _client


def _mime_type_for(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime if mime and mime.startswith("image/") else "image/jpeg"


# ---------------------------
# Public API
# ---------------------------

def get_tags_for_image_file(image_path: str) -> List[str]:
    """
    Given a local image file path, returns a list of simple visual tags.
    Raises on API errors or an empty model response so callers can log the cause.
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

    client = _get_client()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type=_mime_type_for(image_path)),
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=200,
        ),
    )

    if not response.text:
        finish = None
        if response.candidates:
            finish = response.candidates[0].finish_reason
        raise RuntimeError(
            f"Gemini returned no text for {image_path} "
            f"(finish_reason={finish}, prompt_feedback={response.prompt_feedback})"
        )

    # Gemini sometimes wraps JSON in markdown
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        tags = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini response was not valid JSON, using line fallback: %r", text)
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
