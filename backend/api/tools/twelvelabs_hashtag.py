import os
import time
from typing import Any, Dict, List, Optional

from twelvelabs import TwelveLabs
from twelvelabs.indexes import IndexesCreateRequestModelsItem

_client: Optional[TwelveLabs] = None
_cached_index_id: Optional[str] = os.getenv("TWELVELABS_INDEX_ID")


def _get_client() -> TwelveLabs:
    """Create the client on first use, so the API can start without a Twelve Labs key
    (photo uploads, search and browsing keep working; only video tagging needs it)."""
    global _client
    if _client is None:
        api_key = os.getenv("TWELVELABS_API_KEY")
        if not api_key:
            raise RuntimeError("Missing TWELVELABS_API_KEY in environment")
        _client = TwelveLabs(api_key=api_key)
    return _client


def _get_or_create_index_id() -> str:
    global _cached_index_id
    if _cached_index_id:
        return _cached_index_id

    index_name = os.getenv("TWELVELABS_INDEX_NAME", "memoryvault-demo")

    index = _get_client().indexes.create(
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
    index_id = _get_or_create_index_id()

    # Upload bytes (not a string path)
    with open(video_file_path, "rb") as f:
        task = _get_client().tasks.create(index_id=index_id, video_file=f)

    if not getattr(task, "id", None):
        raise RuntimeError("No task id returned from Twelve Labs")

    # Poll until ready/failed
    while True:
        t = _get_client().tasks.retrieve(task.id)
        print(f"[twelvelabs] task={t.id} status={t.status}")

        if t.status == "ready":
            if not t.video_id:
                raise RuntimeError("Task ready but no video_id returned")
            return t.video_id

        if t.status == "failed":
            raise RuntimeError(
                f"Indexing failed: {getattr(t, 'error', None) or getattr(t, 'message', None) or 'unknown error'}"
            )

        time.sleep(sleep_interval)


def get_hashtags_for_video_file(video_file_path: str) -> Dict[str, Any]:
    video_id = upload_video_and_wait(video_file_path)

    gist = _get_client().gist(video_id=video_id, types=["hashtag"])
    hashtags: List[str] = getattr(gist, "hashtags", None) or []

    return {"video_id": video_id, "hashtags": hashtags}