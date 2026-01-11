import filetype

def get_media_type(file_bytes: bytes):
    kind = filetype.guess(file_bytes)

    if kind is None:
        return "unknown"

    if kind.mime.startswith("image/"):
        return "image"
    elif kind.mime.startswith("video/"):
        return "video"
    else:
        return "other"
