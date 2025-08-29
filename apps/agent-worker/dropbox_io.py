# /apps/agent-worker/dropbox_io.py

import io
import os
from PIL import Image
import dropbox
from dropbox.exceptions import ApiError
from dotenv import load_dotenv

load_dotenv()

dbx = None
try:
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
        app_key=os.getenv("DROPBOX_APP_KEY"),
        app_secret=os.getenv("DROPBOX_APP_SECRET"),
    )
except Exception as e:
    print(f"[agent-worker] Dropbox init error: {e}")


def download_pil_image(path: str) -> Image.Image:
    if not dbx:
        raise ConnectionError("Dropbox client not initialized in agent worker.")
    try:
        _, res = dbx.files_download(path)
        return Image.open(io.BytesIO(res.content)).convert("RGB")
    except ApiError as e:
        print(f"[agent-worker] Error downloading image from {path}: {e}")
        raise
