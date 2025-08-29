from __future__ import annotations

from typing import Dict, List
from PIL import Image
from io import BytesIO
import storage
from datetime import datetime, timezone


def save_localized_messages(campaign: str, product: str, market: str, messages: Dict[str, str]):
    base = f"{storage.get_root()}/outputs/{campaign}/messages"
    storage.ensure_folder(base)
    path = f"{base}/{product.replace(' ', '_')}_{market.replace(' ', '_')}.json"
    storage.write_json(path, messages)


def generate_carousel_from_image(campaign: str, product: str, img: Image.Image, count: int = 3):
    """Create a simple carousel as multiple crops of the base image (left/center/right)."""
    w, h = img.size
    offsets = [0.0, 0.25, 0.5]
    base_dir = f"{storage.get_root()}/outputs/{campaign}/carousels/{product.replace(' ', '_')}"
    storage.ensure_folder(base_dir)
    for i in range(min(count, len(offsets))):
        left = int(offsets[i] * w)
        right = left + int(0.75 * w)
        if right > w:
            right = w
            left = w - int(0.75 * w)
        crop = img.crop((left, 0, right, h)).resize((1080, 1080), Image.Resampling.LANCZOS)
        storage.upload_pil_image(f"{base_dir}/slide_{i+1}.jpg", crop)


def generate_animated_gif_from_image(campaign: str, product: str, market: str, img: Image.Image):
    """Create a lightweight animated GIF using a simple zoom effect."""
    frames: List[Image.Image] = []
    w, h = img.size
    steps = 8
    for i in range(steps):
        scale = 1.0 + 0.02 * i
        new_w, new_h = int(w * scale), int(h * scale)
        frame = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # center-crop back to original size
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        frame = frame.crop((left, top, left + w, top + h))
        frames.append(frame)

    out = BytesIO()
    frames[0].save(
        out,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
        disposal=2,
    )
    out.seek(0)
    base_dir = f"{storage.get_root()}/outputs/{campaign}/videos/{product.replace(' ', '_')}"
    storage.ensure_folder(base_dir)
    storage.upload_bytes(f"{base_dir}/{market.replace(' ', '_')}.gif", out.read())


def update_catalog(campaign: str, catalog: Dict):
    base_dir = f"{storage.get_root()}/outputs/{campaign}"
    storage.ensure_folder(base_dir)
    if "created_at" not in catalog:
        catalog["created_at"] = datetime.now(timezone.utc).isoformat()
    storage.write_json(f"{base_dir}/catalog.json", catalog)
