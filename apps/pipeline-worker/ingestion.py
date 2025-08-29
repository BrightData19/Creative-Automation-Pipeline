from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PIL import Image

import storage


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".gif"}
AUDIO_EXTS = {".mp3", ".wav", ".aac", ".flac"}
DOC_EXTS = {".pdf", ".docx", ".pptx", ".ppt", ".key", ".xlsx"}
GRAPHIC_EXTS = {".svg", ".psd", ".ai"}


@dataclass
class Asset:
    name: str
    path: str
    kind: str  # image, video, audio, doc, graphic, other


def _classify(name: str) -> str:
    ext = os.path.splitext(name.lower())[1]
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in DOC_EXTS:
        return "doc"
    if ext in GRAPHIC_EXTS:
        return "graphic"
    return "other"


def index_inbox(inbox_folder: str) -> List[Asset]:
    """List assets in the inbox folder and classify them."""
    names = storage.list_folder(inbox_folder) or []
    assets: List[Asset] = []
    for n in names:
        assets.append(Asset(name=n, path=f"{inbox_folder}/{n}", kind=_classify(n)))
    return assets


def copy_all_assets_to_outputs(campaign: str, inbox_folder: str, assets: List[Asset]) -> List[Asset]:
    """Copy all inbox assets to outputs/<campaign>/ingested for traceability."""
    out_dir = f"{storage.get_root()}/outputs/{campaign}/ingested"
    storage.ensure_folder(out_dir)
    copied: List[Asset] = []
    for a in assets:
        dest = f"{out_dir}/{a.name}"
        try:
            data = storage.download_bytes(a.path)
            storage.upload_bytes(dest, data)
            copied.append(Asset(name=a.name, path=f"dropbox:{dest}", kind=a.kind))
        except Exception:
            # best-effort copy
            continue
    return copied


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def pick_product_image_asset(product_name: str, assets: List[Asset]) -> Optional[Asset]:
    """Pick the best matching image asset for a product by filename slug match, fall back to any image."""
    prod_slug = _slug(product_name)
    image_assets = [a for a in assets if a.kind == "image"]
    # Direct slug contains
    for a in image_assets:
        if prod_slug and prod_slug in _slug(a.name):
            return a
    # Fallback to first image
    return image_assets[0] if image_assets else None


def load_image_from_asset(asset: Asset) -> Image.Image:
    data = storage.download_bytes(asset.path)
    from io import BytesIO

    return Image.open(BytesIO(data)).convert("RGB")

