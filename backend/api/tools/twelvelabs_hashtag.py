import os
import time
from typing import Any, Dict, List, Optional

from twelvelabs import TwelveLabs
from twelvelabs.indexes import IndexesCreateRequestModelsItem

_API_KEY = os.getenv("TWELVELABS_API_KEY")
if not _API_KEY:
    raise RuntimeError("Missing TWELVELABS_API_KEY in environment")

_client = TwelveLabs(api_key=_API_KEY)
_cached_index_id: Optional[str] = os.getenv("TWELVELABS_INDEX_ID")


def _get_or_create_index_id() -> str:
    global _cached_index_id
    if _cached_index_id:
        return _cached_index_id

    index_name = os.getenv("TWELVELABS_INDEX_NAME", "memoryvault-demo")

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
    index_id = _get_or_create_index_id()

    # Upload bytes (not a string path)
    with open(video_file_path, "rb") as f:
        task = _client.tasks.create(index_id=index_id, video_file=f)

    if not getattr(task, "id", None):
        raise RuntimeError("No task id returned from Twelve Labs")

    # Poll until ready/failed
    while True:
        t = _client.tasks.retrieve(task.id)
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

    gist = _client.gist(video_id=video_id, types=["hashtag"])
    hashtags: List[str] = getattr(gist, "hashtags", None) or []

    return {"video_id": video_id, "hashtags": hashtags}