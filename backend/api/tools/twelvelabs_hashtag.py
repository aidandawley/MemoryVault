import os
from typing import Any, Dict, List, Optional

from twelvelabs import TwelveLabs
from twelvelabs.indexes import IndexesCreateRequestModelsItem

# ---- Config ----
# Set these in your environment:
#   TWELVELABS_API_KEY=...
#   TWELVELABS_INDEX_ID=...   (recommended)
# Optionally:
#   TWELVELABS_INDEX_NAME=memoryvault-demo

_API_KEY = os.getenv("TWELVELABS_API_KEY")
if not _API_KEY:
    raise RuntimeError("Missing TWELVELABS_API_KEY in environment")

_client = TwelveLabs(api_key=_API_KEY)

_cached_index_id: Optional[str] = os.getenv("TWELVELABS_INDEX_ID")


def _get_or_create_index_id() -> str:
    """
    For hackathon/demo:
    - Best: set TWELVELABS_INDEX_ID once and reuse it.
    - Fallback: auto-create a Pegasus index if INDEX_ID isn't provided.
    """
    global _cached_index_id

    if _cached_index_id:
        return _cached_index_id

    index_name = os.getenv("TWELVELABS_INDEX_NAME", "memoryvault-demo")

    # Create an index with Pegasus enabled (visual only).
    # If you later want speech/voice to influence tags, change model_options to ["visual","audio"].
    index = _client.indexes.create(
        index_name=index_name,
        models=[
            IndexesCreateRequestModelsItem(
                model_name="pegasus1.2",
                model_options=["visual"],
            )
        ],
    )

    if not index or not index.id:
        raise RuntimeError("Failed to create Twelve Labs index")

    _cached_index_id = index.id
    return _cached_index_id


def upload_video_and_wait(video_file_path: str, sleep_interval: int = 5) -> str:
    """
    Uploads a local video file into the index and blocks until indexing is ready.
    Returns the Twelve Labs video_id (what you need for gist/analysis).
    """
    index_id = _get_or_create_index_id()

    task = _client.tasks.create(index_id=index_id, video_file=video_file_path)

    # Wait for indexing to finish
    task.wait_for_done(
        sleep_interval=sleep_interval,
        callback=lambda t: print(f"[twelvelabs] status={t.status}"),
    )

    if task.status != "ready":
        raise RuntimeError(f"Indexing failed with status {task.status}")

    if not task.video_id:
        raise RuntimeError("No video_id returned from Twelve Labs task")

    return task.video_id


def get_hashtags_for_video_file(video_file_path: str) -> Dict[str, Any]:
    """
    The function you will call from your route/service.
    Upload -> wait -> gist -> return hashtags
    """
    video_id = upload_video_and_wait(video_file_path)

    # Gist types can include: "title", "topic", "hashtag"
    gist = _client.gist(video_id=video_id, types=["hashtag"])

    hashtags: List[str] = gist.hashtags or []
    return {
        "video_id": video_id,
        "hashtags": hashtags,
    }
