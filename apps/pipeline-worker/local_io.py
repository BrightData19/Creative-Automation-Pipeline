"""
Local filesystem storage adapter for the pipeline worker.

Provides a dropbox_io-compatible interface for offline/demo runs.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import List

from PIL import Image
import shutil

LOCAL_ROOT = os.getenv("LOCAL_ROOT", "local_storage")


def _abs(path: str) -> Path:
    # Normalize leading slashes and join under LOCAL_ROOT
    # Accepts paths like "/Apps/CreativeAutomation/outputs/..." or relative
    p = path.lstrip("/")
    return Path(LOCAL_ROOT) / p


def ensure_folder(path: str):
    (_abs(path)).mkdir(parents=True, exist_ok=True)


def write_json(path: str, obj: dict):
    fp = _abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def read_json(path: str) -> dict:
    fp = _abs(path)
    return json.loads(fp.read_text(encoding="utf-8"))


def upload_pil_image(path: str, img: Image.Image, format: str = "JPEG"):
    fp = _abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    # Pillow saves based on suffix if not provided, but we enforce format
    with io.BytesIO() as buf:
        save_kwargs = {"quality": 92} if format.upper() in {"JPEG", "JPG"} else {}
        img.save(buf, format=format, **save_kwargs)
        buf.seek(0)
        fp.write_bytes(buf.read())


def download_pil_image(path: str) -> Image.Image:
    fp = _abs(path)
    return Image.open(fp).convert("RGB")


def list_folder(path: str) -> List[str]:
    fp = _abs(path)
    if not fp.exists():
        return []
    return [p.name for p in fp.iterdir()]


def get_root() -> str:
    return LOCAL_ROOT


def upload_bytes(path: str, data: bytes):
    fp = _abs(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_bytes(data)


def download_bytes(path: str) -> bytes:
    fp = _abs(path)
    return fp.read_bytes()


def delete_path(path: str):
    fp = _abs(path)
    if fp.is_dir():
        shutil.rmtree(fp, ignore_errors=True)
    elif fp.exists():
        fp.unlink()
