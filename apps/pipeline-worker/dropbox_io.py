# /apps/pipeline-worker/dropbox_io.py

import io
import json
import os

import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    p = "/" + path.lstrip("/")
    # collapse duplicate slashes
    while "//" in p:
        p = p.replace("//", "/")
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p

# Initialize Dropbox client from environment variables
try:
    dbx = dropbox.Dropbox(
        oauth2_refresh_token=os.getenv("DROPBOX_REFRESH_TOKEN"),
        app_key=os.getenv("DROPBOX_APP_KEY"),
        app_secret=os.getenv("DROPBOX_APP_SECRET"),
    )
    print("Dropbox client initialized successfully.")
except Exception as e:
    print(f"Error initializing Dropbox client: {e}")
    dbx = None

def write_json(path: str, obj: dict):
    """Uploads a dictionary as a JSON file to Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        dbx.files_upload(
            json.dumps(obj, indent=2).encode("utf-8"),
            _normalize_path(path),
            mode=WriteMode.overwrite
        )
        print(f"Successfully wrote JSON to {path}")
    except ApiError as e:
        print(f"Error writing JSON to {path}: {e}")
        raise

def read_json(path: str) -> dict:
    """Downloads and parses a JSON file from Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        _, res = dbx.files_download(_normalize_path(path))
        return json.loads(res.content)
    except ApiError as e:
        print(f"Error reading JSON from {path}: {e}")
        raise

def upload_pil_image(path: str, img: Image.Image, format: str = "JPEG"):
    """Uploads a Pillow Image object to Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    buffer = io.BytesIO()
    img.save(buffer, format=format, quality=92)
    buffer.seek(0)
    try:
        dbx.files_upload(buffer.read(), _normalize_path(path), mode=WriteMode.overwrite)
        print(f"Successfully uploaded image to {path}")
    except ApiError as e:
        print(f"Error uploading image to {path}: {e}")
        raise

def download_pil_image(path: str) -> Image.Image:
    """Downloads an image from Dropbox and returns it as a Pillow Image object."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        _, res = dbx.files_download(_normalize_path(path))
        return Image.open(io.BytesIO(res.content)).convert("RGB")
    except ApiError as e:
        print(f"Error downloading image from {path}: {e}")
        raise

def ensure_folder(path: str):
    """Ensures a folder exists at the given path in Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        # Check if folder exists by trying to get its metadata
        norm = _normalize_path(path)
        dbx.files_get_metadata(norm)
    except ApiError as e:
        if isinstance(e.error, dropbox.files.GetMetadataError) and e.error.is_path() and e.error.get_path().is_not_found():
            # Folder does not exist, so create it
            try:
                dbx.files_create_folder_v2(norm)
                print(f"Created folder: {norm}")
            except ApiError as create_e:
                print(f"Error creating folder {norm}: {create_e}")
                raise
        else:
            # Some other API error occurred
            print(f"Error checking folder {norm}: {e}")
            raise

def list_folder(path: str) -> list:
    """Lists the contents of a folder in Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        result = dbx.files_list_folder(_normalize_path(path))
        return [entry.name for entry in result.entries]
    except ApiError as e:
        print(f"Error listing folder {path}: {e}")
        return []

def delete_path(path: str):
    """Deletes a file or folder in Dropbox."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        norm = _normalize_path(path)
        dbx.files_delete_v2(norm)
        print(f"Deleted path: {norm}")
    except ApiError as e:
        print(f"Error deleting {path}: {e}")
        raise

def upload_bytes(path: str, data: bytes):
    """Upload raw bytes to Dropbox at the given path."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        dbx.files_upload(data, _normalize_path(path), mode=WriteMode.overwrite)
        print(f"Successfully uploaded bytes to {path}")
    except ApiError as e:
        print(f"Error uploading bytes to {path}: {e}")
        raise

def download_bytes(path: str) -> bytes:
    """Download raw bytes from Dropbox at the given path."""
    if not dbx:
        raise ConnectionError("Dropbox client not initialized.")
    try:
        _, res = dbx.files_download(_normalize_path(path))
        return res.content
    except ApiError as e:
        print(f"Error downloading bytes from {path}: {e}")
        raise
