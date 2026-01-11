import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

from ..tools.twelvelabs_hashtag import get_hashtags_for_video_file







router = APIRouter(prefix="/media", tags=["media"])

@router.post("/upload-video-hashtags")
async def upload_video_hashtags(file: UploadFile = File(...)):
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="Please upload a video file.")

    suffix = os.path.splitext(file.filename)[-1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())

    try:
        result = get_hashtags_for_video_file(tmp_path)
        return result
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

@router.post("/upload-photo-tags")
async def upload_photo_tags(file: UploadFile = File(...)):
    # For demo: only accept images (jpg/png etc.)
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    suffix = os.path.splitext(file.filename)[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
        tmp.write(await file.read())

    try:
        # Placeholder for now (Gemini comes next step)
        # Later: tags = get_tags_for_image_file(tmp_path)
        return {
            "photo_path": tmp_path,   # just to prove we received + saved it
            "tags": []
        }
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
